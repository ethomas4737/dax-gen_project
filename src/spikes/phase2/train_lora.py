"""Phase 2 training script for M3: LoRA-wrapped trainable backbone (peft).

Unlike train_frozen.py (M1/M2), M3's backbone is trainable, so there is no
embed-once-cache trick available -- a trained protein's embedding changes every
optimizer step, so every training step must run a fresh backbone forward pass
over that batch's actual seq_a/seq_b tokens (twice per pair: once for seq_a, once
for seq_b). This makes M3 materially more expensive per step than M1/M2 (a real
~300M-param forward pass through the LoRA-adapted layers, every batch, every
epoch, vs. M1/M2's one-time embedding pass) -- see dax-state/plan-phase2.md for
the separate GPU resource estimate this implies before step 8a's real run.

M3 = LoRA-wrapped backbone + mean-pooling + head (--pooling defaults to "mean",
matching M1, so M3 isolates exactly one change from M1: backbone trainability.
Attention-pooling is available via --pooling attn if wanted, but the two "new"
mechanisms -- trainable backbone and trainable pooling -- are kept separable by
default rather than combined, for a cleaner one-axis-at-a-time comparison against
M1/M2. Flagged in dax-state/plan-phase2.md; not explicitly specified by the human.)

Per-epoch validation (added 2026-07-10, step 6 reopened per dax-state/decisions.md):
after each training epoch, run a no-grad forward pass over data/curated/d1_ppi/val.csv
(step 1c's dedicated split -- never data/curated/d1_ppi/test.csv, reserved for final
held-out reporting) and print val_loss + val_auroc. Unlike train_frozen.py, M3 has no
embed-once cache (trainable backbone) -- the val pass is structurally identical to the
train pass (same tokenize + forward path) but with clf.eval() and no backward/optimizer
step.

Usage (smoke test):
    python train_lora.py --data-dir ../../../data/curated/d1_ppi_smoke \
        --out-dir ../../../runs/phase2_m3_d1/smoke --epochs 5 --device cpu
"""
import argparse
import json
import time
from pathlib import Path

import pandas as pd
import torch
import torch.nn as nn

from model import (
    D_MODEL_300M,
    apply_lora,
    get_pooling,
    load_esmc_300m,
    PairClassifier,
    PairHead,
    safe_auroc_auprc,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


class PairSeqDataset(torch.utils.data.Dataset):
    """Pair dataset over raw sequences, not cache indices -- M3 needs the actual
    seq_a/seq_b strings every step since the backbone is trainable."""

    def __init__(self, seq_a, seq_b, labels):
        self.seq_a = list(seq_a)
        self.seq_b = list(seq_b)
        self.labels = list(labels)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        return self.seq_a[i], self.seq_b[i], self.labels[i]


def tokenize_batch(seqs, tokenizer, pad_id, device):
    token_lists = [tokenizer.encode(s) for s in seqs]
    max_len = max(len(t) for t in token_lists)
    padded = torch.full((len(seqs), max_len), pad_id, dtype=torch.long)
    for i, t in enumerate(token_lists):
        padded[i, :len(t)] = torch.tensor(t, dtype=torch.long)
    return padded.to(device)


@torch.no_grad()
def evaluate_lora(clf, dataset, tokenizer, device, batch_size=32):
    """Val pass for M3: no cache (trainable backbone) -- structurally the same
    per-batch tokenize + forward as train(), but eval() + no_grad + no optimizer step."""
    clf.eval()
    pad_id = tokenizer.pad_token_id
    n = len(dataset)
    loss_fn = nn.BCEWithLogitsLoss(reduction="sum")
    total_loss, all_probs, all_labels = 0.0, [], []
    for start in range(0, n, batch_size):
        seq_a = dataset.seq_a[start:start + batch_size]
        seq_b = dataset.seq_b[start:start + batch_size]
        labels = torch.tensor(dataset.labels[start:start + batch_size], dtype=torch.float32, device=device)
        ids_a = tokenize_batch(seq_a, tokenizer, pad_id, device)
        ids_b = tokenize_batch(seq_b, tokenizer, pad_id, device)
        logits = clf(ids_a, ids_b)
        total_loss += loss_fn(logits, labels).item()
        all_probs.append(torch.sigmoid(logits).cpu())
        all_labels.append(labels.cpu())
    clf.train()
    probs = torch.cat(all_probs).numpy()
    labels = torch.cat(all_labels).numpy()
    auroc, _, _ = safe_auroc_auprc(labels, probs)
    return total_loss / n, auroc


def train(clf, dataset, tokenizer, epochs, lr, batch_size, device, val_dataset=None):
    clf = clf.to(device)
    trainable_params = [p for p in clf.parameters() if p.requires_grad]
    opt = torch.optim.Adam(trainable_params, lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()
    pad_id = tokenizer.pad_token_id

    n = len(dataset)
    loss_history, val_loss_history, val_auroc_history = [], [], []
    for epoch in range(epochs):
        perm = torch.randperm(n).tolist()
        epoch_losses = []
        for start in range(0, n, batch_size):
            batch_idx = perm[start:start + batch_size]
            seq_a = [dataset.seq_a[i] for i in batch_idx]
            seq_b = [dataset.seq_b[i] for i in batch_idx]
            labels = torch.tensor([dataset.labels[i] for i in batch_idx], dtype=torch.float32, device=device)
            ids_a = tokenize_batch(seq_a, tokenizer, pad_id, device)
            ids_b = tokenize_batch(seq_b, tokenizer, pad_id, device)

            logits = clf(ids_a, ids_b)
            loss = loss_fn(logits, labels)
            opt.zero_grad()
            loss.backward()
            opt.step()
            epoch_losses.append(loss.item())
        mean_loss = sum(epoch_losses) / len(epoch_losses)
        loss_history.append(mean_loss)
        if val_dataset is not None:
            val_loss, val_auroc = evaluate_lora(clf, val_dataset, tokenizer, device)
            val_loss_history.append(val_loss)
            val_auroc_history.append(val_auroc)
            print(f"epoch {epoch+1}/{epochs}  train_loss={mean_loss:.4f}  val_loss={val_loss:.4f}  "
                  f"val_auroc={val_auroc}")
        else:
            print(f"epoch {epoch+1}/{epochs}  mean_loss={mean_loss:.4f}")
    return loss_history, val_loss_history, val_auroc_history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(REPO_ROOT / "data" / "curated" / "d1_ppi_smoke"))
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "runs" / "phase2_m3_d1" / "smoke"))
    ap.add_argument("--pooling", choices=["mean", "attn"], default="mean")
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--hidden-dim", type=int, default=256)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--lora-r", type=int, default=8)
    ap.add_argument("--lora-alpha", type=int, default=16)
    ap.add_argument("--lora-dropout", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    train_df = pd.read_csv(data_dir / "train.csv")
    val_df = pd.read_csv(data_dir / "val.csv")
    test_df = pd.read_csv(data_dir / "test.csv")
    print(f"Loaded train={len(train_df)} rows, val={len(val_df)} rows, test={len(test_df)} rows from {data_dir}")

    print("Loading ESM-C 300M backbone + wrapping with LoRA (M3)...")
    backbone, tokenizer = load_esmc_300m(device=args.device)
    lora_backbone = apply_lora(backbone, r=args.lora_r, lora_alpha=args.lora_alpha,
                                lora_dropout=args.lora_dropout)
    pooling = get_pooling(args.pooling, D_MODEL_300M)
    head = PairHead(d_model=D_MODEL_300M, hidden_dim=args.hidden_dim, dropout=args.dropout)
    clf = PairClassifier(lora_backbone, tokenizer, pooling, head, backbone_trainable=True)

    n_trainable = sum(p.numel() for p in clf.parameters() if p.requires_grad)
    n_total = sum(p.numel() for p in clf.parameters())
    print(f"Trainable params: {n_trainable:,} / {n_total:,} total (LoRA r={args.lora_r} + pooling + head)")
    t_load = time.time()

    train_ds = PairSeqDataset(train_df["seq_a"], train_df["seq_b"], train_df["label"])
    val_ds = PairSeqDataset(val_df["seq_a"], val_df["seq_b"], val_df["label"])

    print("Training M3 (LoRA backbone + pooling + head)...")
    loss_history, val_loss_history, val_auroc_history = train(
        clf, train_ds, tokenizer, args.epochs, args.lr, args.batch_size, args.device,
        val_dataset=val_ds)
    t_train = time.time()

    torch.save(clf.state_dict(), out_dir / "model.pt")

    meta = {
        "pooling": args.pooling,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "lora_dropout": args.lora_dropout,
        "n_train": len(train_df),
        "n_val": len(val_df),
        "n_test": len(test_df),
        "n_trainable_params": n_trainable,
        "n_total_params": n_total,
        "epochs": args.epochs,
        "lr": args.lr,
        "batch_size": args.batch_size,
        "loss_history": loss_history,
        "loss_decreased": loss_history[-1] < loss_history[0] if len(loss_history) > 1 else None,
        "val_loss_history": val_loss_history,
        "val_auroc_history": val_auroc_history,
        "wall_time_s": {
            "setup": round(t_load - t0, 2),
            "training": round(t_train - t_load, 2),
            "total": round(t_train - t0, 2),
        },
    }
    with open(out_dir / "train_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(json.dumps(meta, indent=2))
    print(f"Wrote checkpoint + meta to {out_dir}")


if __name__ == "__main__":
    main()
