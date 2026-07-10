"""Phase 2 / M1-on-D1 training: frozen ESM-C 300M backbone (mean-pooled) + MLP head.

Study code (src/spikes/phase2/) -- CPU smoke-test scale only. This script is deliberately
NOT wired to launch the real ~421K-row training run -- see the run-note
(dax-state/runs/phase2-m1-d1-pipeline.md) for the GPU resource estimate for that.

Because M1's backbone is frozen (no gradient, no dropout in the backbone), embedding
a given protein sequence gives the exact same pooled vector every time it's used --
across every pair it appears in and across every training epoch. So instead of
re-running the backbone forward pass per pair per epoch, we embed each *unique*
sequence once (model.build_embedding_cache), cache the pooled vectors, and train
only the MLP head against those fixed features. This is mathematically identical
to running the full Siamese PairClassifier forward pass every step for M1
specifically (mean-pooling has no learned parameters and no stochasticity), and is
dramatically cheaper -- this is the central fact behind the GPU resource estimate.

Scale note: we deliberately do NOT materialize a (n_pairs, 4*d_model) combined-feature
matrix for the whole train/test set up front -- at D1's real scale (~420K train pairs)
that would be ~6.4GB (420K * 3840 * 4 bytes). Instead we keep only the small
(n_unique_proteins, d_model) embedding matrix (~60MB for D1's ~15.7K unique proteins)
and look up + combine embeddings per batch on the fly (model.PairIndexDataset /
model.batch_features). This is the code path that should scale to the real run.

Usage (smoke test):
    python train_m1.py --data-dir ../../../data/curated/d1_ppi_smoke \
        --out-dir ../../../runs/phase2_m1_d1/smoke --epochs 5 --device cpu
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
    MeanPooling,
    PairHead,
    batch_features,
    build_embedding_cache,
    cache_to_matrix,
    load_esmc_300m,
    PairIndexDataset,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def gather_unique_sequences(train_df, test_df):
    seqs = {}
    for df in (train_df, test_df):
        for _, row in df[["protein_a", "seq_a"]].drop_duplicates().iterrows():
            seqs[row["protein_a"]] = row["seq_a"]
        for _, row in df[["protein_b", "seq_b"]].drop_duplicates().iterrows():
            seqs[row["protein_b"]] = row["seq_b"]
    return seqs


def train(head, dataset, embedding_matrix, epochs, lr, batch_size, device):
    head = head.to(device)
    embedding_matrix = embedding_matrix.to(device)
    opt = torch.optim.Adam(head.parameters(), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()

    n = len(dataset)
    loss_history = []
    for epoch in range(epochs):
        perm = torch.randperm(n)
        epoch_losses = []
        for start in range(0, n, batch_size):
            batch_idx = perm[start:start + batch_size]
            idx_a, idx_b, labels = dataset.idx_a[batch_idx], dataset.idx_b[batch_idx], dataset.labels[batch_idx]
            idx_a, idx_b, labels = idx_a.to(device), idx_b.to(device), labels.to(device)
            combined = batch_features(idx_a, idx_b, embedding_matrix)  # [b, 4*d_model], on the fly
            logits = head(combined)
            loss = loss_fn(logits, labels)
            opt.zero_grad()
            loss.backward()
            opt.step()
            epoch_losses.append(loss.item())
        mean_loss = sum(epoch_losses) / len(epoch_losses)
        loss_history.append(mean_loss)
        print(f"epoch {epoch+1}/{epochs}  mean_loss={mean_loss:.4f}")
    return loss_history


def main():
    ap = argparse.ArgumentParser()
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
    test_df = pd.read_csv(data_dir / "test.csv")
    print(f"Loaded train={len(train_df)} rows, test={len(test_df)} rows from {data_dir}")

    unique_seqs = gather_unique_sequences(train_df, test_df)
    print(f"{len(unique_seqs)} unique protein sequences to embed (train+test combined)")

    print("Loading ESM-C 300M backbone (frozen for M1)...")
    backbone, tokenizer = load_esmc_300m(device=args.device)
    pooling = MeanPooling()
    n_backbone_params = sum(p.numel() for p in backbone.parameters())
    print(f"Backbone loaded: {n_backbone_params:,} params, frozen (requires_grad=False, no_grad forward)")
    for p in backbone.parameters():
        p.requires_grad_(False)

    t_load = time.time()
    print("Building embedding cache (one forward pass per unique sequence)...")
    cache = build_embedding_cache(backbone, tokenizer, pooling, unique_seqs,
                                   device=args.device, batch_size=args.embed_batch_size)
    t_embed = time.time()
    print(f"Embedding cache built: {len(cache)} vectors, dim={D_MODEL_300M}, "
          f"took {t_embed - t_load:.1f}s")

    embedding_matrix, id_to_idx = cache_to_matrix(cache)
    train_ds = PairIndexDataset(train_df["protein_a"], train_df["protein_b"], train_df["label"], id_to_idx)
    test_ds = PairIndexDataset(test_df["protein_a"], test_df["protein_b"], test_df["label"], id_to_idx)

    head = PairHead(d_model=D_MODEL_300M, hidden_dim=args.hidden_dim, dropout=args.dropout)
    n_head_params = sum(p.numel() for p in head.parameters())
    print(f"Head: {n_head_params:,} trainable params")

    print("Training head...")
    loss_history = train(head, train_ds, embedding_matrix, args.epochs, args.lr,
                          args.batch_size, args.device)
    t_train = time.time()

    torch.save(head.state_dict(), out_dir / "head.pt")
    torch.save({"embedding_matrix": embedding_matrix, "id_to_idx": id_to_idx}, out_dir / "embedding_cache.pt")
    torch.save({"idx_a": test_ds.idx_a, "idx_b": test_ds.idx_b, "labels": test_ds.labels},
               out_dir / "test_indices.pt")

    meta = {
        "n_train": len(train_df),
        "n_test": len(test_df),
        "n_unique_sequences": len(unique_seqs),
        "d_model": D_MODEL_300M,
        "n_backbone_params": n_backbone_params,
        "n_head_params": n_head_params,
        "epochs": args.epochs,
        "lr": args.lr,
        "batch_size": args.batch_size,
        "loss_history": loss_history,
        "loss_decreased": loss_history[-1] < loss_history[0] if len(loss_history) > 1 else None,
        "wall_time_s": {
            "data_load": round(t_load - t0, 2),
            "embedding_cache": round(t_embed - t_load, 2),
            "head_training": round(t_train - t_embed, 2),
            "total": round(t_train - t0, 2),
        },
    }
    with open(out_dir / "train_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    print(json.dumps(meta, indent=2))
    print(f"Wrote checkpoint + cache + meta to {out_dir}")


if __name__ == "__main__":
    main()
