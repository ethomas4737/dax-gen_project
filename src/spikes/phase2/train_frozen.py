"""Phase 2 training script for frozen-backbone models: M1 (--pooling mean) and
M2 (--pooling attn). Generalizes train_m1.py (kept in place, per Article 6 --
superseded study code is preserved, not deleted) with a --pooling flag.

Both variants freeze the ESM-C 300M backbone, so both get the "embed each unique
protein once" efficiency trick -- but WHAT gets cached differs:
  - mean (M1): pooling is non-parametric, so we cache the final *pooled* [D]
    vector per unique protein (model.build_embedding_cache / cache_to_matrix) and
    train only the head.
  - attn (M2): pooling itself is trainable (AttnPooling), so a cached pooled
    vector would go stale as soon as pooling's weights update. Instead we cache
    each unique protein's per-residue hidden states (model.build_hidden_state_cache
    / hidden_cache_to_list) -- still a one-time cost, since the backbone is frozen
    -- and apply pooling fresh every batch (model.batch_pooled_attn), training
    both the pooling and the head.

Per-epoch validation (added 2026-07-10, step 6 reopened per dax-state/decisions.md):
after each training epoch, run a no-grad forward pass over data/curated/d1_ppi/val.csv
(step 1c's dedicated split -- never data/curated/d1_ppi/test.csv, which stays reserved
for final held-out reporting) and print val_loss + val_auroc. Both pooling variants
reuse their existing cache mechanism for the val pass (embedding_matrix for mean,
hidden_list + batch_pooled_attn for attn) since the backbone is frozen either way --
only the val *pairs* are new, not new protein embeddings to compute (val's unique
proteins are already included in the one-time cache built over train+val+test).

Usage (smoke test):
    python train_frozen.py --pooling mean --data-dir ../../../data/curated/d1_ppi_smoke \
        --out-dir ../../../runs/phase2_m1_d1/smoke --epochs 5 --device cpu
    python train_frozen.py --pooling attn --data-dir ../../../data/curated/d1_ppi_smoke \
        --out-dir ../../../runs/phase2_m2_d1/smoke --epochs 5 --device cpu
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
    batch_features,
    batch_pooled_attn,
    build_embedding_cache,
    build_hidden_state_cache,
    cache_to_matrix,
    combine_pair,
    get_pooling,
    hidden_cache_to_list,
    load_esmc_300m,
    PairHead,
    PairIndexDataset,
    safe_auroc_auprc,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def gather_unique_sequences(*dfs):
    seqs = {}
    for df in dfs:
        for _, row in df[["protein_a", "seq_a"]].drop_duplicates().iterrows():
            seqs[row["protein_a"]] = row["seq_a"]
        for _, row in df[["protein_b", "seq_b"]].drop_duplicates().iterrows():
            seqs[row["protein_b"]] = row["seq_b"]
    return seqs


@torch.no_grad()
def evaluate_mean(head, dataset, embedding_matrix, device, batch_size=256):
    """Val pass for M1 (mean-pool): reuses the same cached embedding_matrix +
    batch_features lookup as training, just no_grad + head.eval() + no optimizer step."""
    head.eval()
    n = len(dataset)
    total_loss, all_probs, all_labels = 0.0, [], []
    loss_fn = nn.BCEWithLogitsLoss(reduction="sum")
    for start in range(0, n, batch_size):
        idx_a = dataset.idx_a[start:start + batch_size].to(device)
        idx_b = dataset.idx_b[start:start + batch_size].to(device)
        labels = dataset.labels[start:start + batch_size].to(device)
        combined = batch_features(idx_a, idx_b, embedding_matrix)
        logits = head(combined)
        total_loss += loss_fn(logits, labels).item()
        all_probs.append(torch.sigmoid(logits).cpu())
        all_labels.append(labels.cpu())
    head.train()
    probs = torch.cat(all_probs).numpy()
    labels = torch.cat(all_labels).numpy()
    auroc, _, _ = safe_auroc_auprc(labels, probs)
    return total_loss / n, auroc


@torch.no_grad()
def evaluate_attn(head, pooling, dataset, hidden_list, device, batch_size=256):
    """Val pass for M2 (attn-pool): reuses the same per-residue hidden_list cache +
    batch_pooled_attn as training, just no_grad + eval() + no optimizer step."""
    head.eval()
    pooling.eval()
    n = len(dataset)
    total_loss, all_probs, all_labels = 0.0, [], []
    loss_fn = nn.BCEWithLogitsLoss(reduction="sum")
    for start in range(0, n, batch_size):
        idx_a = dataset.idx_a[start:start + batch_size]
        idx_b = dataset.idx_b[start:start + batch_size]
        labels = dataset.labels[start:start + batch_size].to(device)
        pooled_a, pooled_b = batch_pooled_attn(idx_a, idx_b, hidden_list, pooling, device)
        combined = combine_pair(pooled_a, pooled_b)
        logits = head(combined)
        total_loss += loss_fn(logits, labels).item()
        all_probs.append(torch.sigmoid(logits).cpu())
        all_labels.append(labels.cpu())
    head.train()
    pooling.train()
    probs = torch.cat(all_probs).numpy()
    labels = torch.cat(all_labels).numpy()
    auroc, _, _ = safe_auroc_auprc(labels, probs)
    return total_loss / n, auroc


def train_mean(head, dataset, embedding_matrix, epochs, lr, batch_size, device,
                val_dataset=None):
    """M1: pooling has no params -- optimizer covers the head only. If val_dataset
    is given, runs a no-grad validation pass (evaluate_mean, reusing the same
    embedding_matrix cache) after every epoch and prints val_loss/val_auroc."""
    head = head.to(device)
    embedding_matrix = embedding_matrix.to(device)
    opt = torch.optim.Adam(head.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()

    n = len(dataset)
    loss_history, val_loss_history, val_auroc_history = [], [], []
    for epoch in range(epochs):
        perm = torch.randperm(n)
        epoch_losses = []
        for start in range(0, n, batch_size):
            batch_idx = perm[start:start + batch_size]
            idx_a, idx_b, labels = dataset.idx_a[batch_idx], dataset.idx_b[batch_idx], dataset.labels[batch_idx]
            idx_a, idx_b, labels = idx_a.to(device), idx_b.to(device), labels.to(device)
            combined = batch_features(idx_a, idx_b, embedding_matrix)
            logits = head(combined)
            loss = loss_fn(logits, labels)
            opt.zero_grad()
            loss.backward()
            opt.step()
            epoch_losses.append(loss.item())
        mean_loss = sum(epoch_losses) / len(epoch_losses)
        loss_history.append(mean_loss)
        if val_dataset is not None:
            val_loss, val_auroc = evaluate_mean(head, val_dataset, embedding_matrix, device)
            val_loss_history.append(val_loss)
            val_auroc_history.append(val_auroc)
            print(f"epoch {epoch+1}/{epochs}  train_loss={mean_loss:.4f}  val_loss={val_loss:.4f}  "
                  f"val_auroc={val_auroc}")
        else:
            print(f"epoch {epoch+1}/{epochs}  mean_loss={mean_loss:.4f}")
    return loss_history, val_loss_history, val_auroc_history


def train_attn(head, pooling, dataset, hidden_list, epochs, lr, batch_size, device,
                val_dataset=None):
    """M2: pooling is trainable -- optimizer covers pooling + head, and pooled
    vectors are recomputed fresh every batch (model.batch_pooled_attn). If
    val_dataset is given, runs a no-grad validation pass (evaluate_attn, reusing
    the same hidden_list cache) after every epoch and prints val_loss/val_auroc."""
    head = head.to(device)
    pooling = pooling.to(device)
    opt = torch.optim.Adam(list(head.parameters()) + list(pooling.parameters()), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()

    n = len(dataset)
    loss_history, val_loss_history, val_auroc_history = [], [], []
    for epoch in range(epochs):
        perm = torch.randperm(n)
        epoch_losses = []
        for start in range(0, n, batch_size):
            batch_idx = perm[start:start + batch_size]
            idx_a, idx_b, labels = dataset.idx_a[batch_idx], dataset.idx_b[batch_idx], dataset.labels[batch_idx]
            labels = labels.to(device)
            pooled_a, pooled_b = batch_pooled_attn(idx_a, idx_b, hidden_list, pooling, device)
            combined = combine_pair(pooled_a, pooled_b)
            logits = head(combined)
            loss = loss_fn(logits, labels)
            opt.zero_grad()
            loss.backward()
            opt.step()
            epoch_losses.append(loss.item())
        mean_loss = sum(epoch_losses) / len(epoch_losses)
        loss_history.append(mean_loss)
        if val_dataset is not None:
            val_loss, val_auroc = evaluate_attn(head, pooling, val_dataset, hidden_list, device)
            val_loss_history.append(val_loss)
            val_auroc_history.append(val_auroc)
            print(f"epoch {epoch+1}/{epochs}  train_loss={mean_loss:.4f}  val_loss={val_loss:.4f}  "
                  f"val_auroc={val_auroc}")
        else:
            print(f"epoch {epoch+1}/{epochs}  mean_loss={mean_loss:.4f}")
    return loss_history, val_loss_history, val_auroc_history


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pooling", choices=["mean", "attn"], required=True)
    ap.add_argument("--data-dir", default=str(REPO_ROOT / "data" / "curated" / "d1_ppi_smoke"))
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "runs" / "phase2_m1_d1" / "smoke"))
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--embed-batch-size", type=int, default=8)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--hidden-dim", type=int, default=256)
    ap.add_argument("--dropout", type=float, default=0.1)
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

    unique_seqs = gather_unique_sequences(train_df, val_df, test_df)
    print(f"{len(unique_seqs)} unique protein sequences to embed (train+val+test combined)")

    print(f"Loading ESM-C 300M backbone (frozen for {'M1' if args.pooling == 'mean' else 'M2'})...")
    backbone, tokenizer = load_esmc_300m(device=args.device)
    pooling = get_pooling(args.pooling, D_MODEL_300M)
    n_backbone_params = sum(p.numel() for p in backbone.parameters())
    print(f"Backbone loaded: {n_backbone_params:,} params, frozen (requires_grad=False, no_grad forward)")
    for p in backbone.parameters():
        p.requires_grad_(False)

    t_load = time.time()
    head = PairHead(d_model=D_MODEL_300M, hidden_dim=args.hidden_dim, dropout=args.dropout)
    n_head_params = sum(p.numel() for p in head.parameters())
    n_pooling_params = sum(p.numel() for p in pooling.parameters())
    print(f"Head: {n_head_params:,} trainable params; pooling ({args.pooling}): {n_pooling_params:,} trainable params")

    if args.pooling == "mean":
        print("Building pooled-embedding cache (M1: pooling is non-parametric)...")
        cache = build_embedding_cache(backbone, tokenizer, pooling, unique_seqs,
                                       device=args.device, batch_size=args.embed_batch_size)
        embedding_matrix, id_to_idx = cache_to_matrix(cache)
        t_embed = time.time()
        print(f"Embedding cache built: {len(cache)} vectors, dim={D_MODEL_300M}, took {t_embed - t_load:.1f}s")

        train_ds = PairIndexDataset(train_df["protein_a"], train_df["protein_b"], train_df["label"], id_to_idx)
        val_ds = PairIndexDataset(val_df["protein_a"], val_df["protein_b"], val_df["label"], id_to_idx)
        test_ds = PairIndexDataset(test_df["protein_a"], test_df["protein_b"], test_df["label"], id_to_idx)

        print("Training head (pooling has no trainable params)...")
        loss_history, val_loss_history, val_auroc_history = train_mean(
            head, train_ds, embedding_matrix, args.epochs, args.lr, args.batch_size, args.device,
            val_dataset=val_ds)
        t_train = time.time()

        torch.save(head.state_dict(), out_dir / "head.pt")
        torch.save({"embedding_matrix": embedding_matrix, "id_to_idx": id_to_idx}, out_dir / "embedding_cache.pt")
        torch.save({"idx_a": test_ds.idx_a, "idx_b": test_ds.idx_b, "labels": test_ds.labels},
                   out_dir / "test_indices.pt")
    else:
        print("Building per-residue hidden-state cache (M2: pooling is trainable)...")
        cache = build_hidden_state_cache(backbone, tokenizer, unique_seqs,
                                          device=args.device, batch_size=args.embed_batch_size)
        hidden_list, id_to_idx = hidden_cache_to_list(cache)
        t_embed = time.time()
        print(f"Hidden-state cache built: {len(cache)} proteins, dim={D_MODEL_300M}, took {t_embed - t_load:.1f}s")

        train_ds = PairIndexDataset(train_df["protein_a"], train_df["protein_b"], train_df["label"], id_to_idx)
        val_ds = PairIndexDataset(val_df["protein_a"], val_df["protein_b"], val_df["label"], id_to_idx)
        test_ds = PairIndexDataset(test_df["protein_a"], test_df["protein_b"], test_df["label"], id_to_idx)

        print("Training pooling + head...")
        loss_history, val_loss_history, val_auroc_history = train_attn(
            head, pooling, train_ds, hidden_list, args.epochs, args.lr, args.batch_size, args.device,
            val_dataset=val_ds)
        t_train = time.time()

        torch.save(head.state_dict(), out_dir / "head.pt")
        torch.save(pooling.state_dict(), out_dir / "pooling.pt")
        torch.save({"hidden_list": hidden_list, "id_to_idx": id_to_idx}, out_dir / "hidden_state_cache.pt")
        torch.save({"idx_a": test_ds.idx_a, "idx_b": test_ds.idx_b, "labels": test_ds.labels},
                   out_dir / "test_indices.pt")

    meta = {
        "pooling": args.pooling,
        "n_train": len(train_df),
        "n_val": len(val_df),
        "n_test": len(test_df),
        "n_unique_sequences": len(unique_seqs),
        "d_model": D_MODEL_300M,
        "n_backbone_params": n_backbone_params,
        "n_head_params": n_head_params,
        "n_pooling_params": n_pooling_params,
        "epochs": args.epochs,
        "lr": args.lr,
        "batch_size": args.batch_size,
        "loss_history": loss_history,
        "loss_decreased": loss_history[-1] < loss_history[0] if len(loss_history) > 1 else None,
        "val_loss_history": val_loss_history,
        "val_auroc_history": val_auroc_history,
        "wall_time_s": {
            "data_load": round(t_load - t0, 2),
            "embedding_cache": round(t_embed - t_load, 2),
            "training": round(t_train - t_embed, 2),
            "total": round(t_train - t0, 2),
        },
    }
    with open(out_dir / "train_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(json.dumps(meta, indent=2))
    print(f"Wrote checkpoint(s) + cache + meta to {out_dir}")


if __name__ == "__main__":
    main()
