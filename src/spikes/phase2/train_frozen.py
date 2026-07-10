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


def train_mean(head, dataset, embedding_matrix, epochs, lr, batch_size, device):
    """M1: pooling has no params -- optimizer covers the head only."""
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
            combined = batch_features(idx_a, idx_b, embedding_matrix)
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


def train_attn(head, pooling, dataset, hidden_list, epochs, lr, batch_size, device):
    """M2: pooling is trainable -- optimizer covers pooling + head, and pooled
    vectors are recomputed fresh every batch (model.batch_pooled_attn)."""
    head = head.to(device)
    pooling = pooling.to(device)
    opt = torch.optim.Adam(list(head.parameters()) + list(pooling.parameters()), lr=lr)
    loss_fn = nn.BCEWithLogitsLoss()

    n = len(dataset)
    loss_history = []
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
        print(f"epoch {epoch+1}/{epochs}  mean_loss={mean_loss:.4f}")
    return loss_history


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
    test_df = pd.read_csv(data_dir / "test.csv")
    print(f"Loaded train={len(train_df)} rows, test={len(test_df)} rows from {data_dir}")

    unique_seqs = gather_unique_sequences(train_df, test_df)
    print(f"{len(unique_seqs)} unique protein sequences to embed (train+test combined)")

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
        test_ds = PairIndexDataset(test_df["protein_a"], test_df["protein_b"], test_df["label"], id_to_idx)

        print("Training head (pooling has no trainable params)...")
        loss_history = train_mean(head, train_ds, embedding_matrix, args.epochs, args.lr,
                                   args.batch_size, args.device)
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
        test_ds = PairIndexDataset(test_df["protein_a"], test_df["protein_b"], test_df["label"], id_to_idx)

        print("Training pooling + head...")
        loss_history = train_attn(head, pooling, train_ds, hidden_list, args.epochs, args.lr,
                                   args.batch_size, args.device)
        t_train = time.time()

        torch.save(head.state_dict(), out_dir / "head.pt")
        torch.save(pooling.state_dict(), out_dir / "pooling.pt")
        torch.save({"hidden_list": hidden_list, "id_to_idx": id_to_idx}, out_dir / "hidden_state_cache.pt")
        torch.save({"idx_a": test_ds.idx_a, "idx_b": test_ds.idx_b, "labels": test_ds.labels},
                   out_dir / "test_indices.pt")

    meta = {
        "pooling": args.pooling,
        "n_train": len(train_df),
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
