"""Phase 2 evaluation harness -- shared across M1 (--variant mean), M2 (--variant
attn), and M3 (--variant lora). Required reporting per project policy
(docs/phase1_eda_summary.md Section 3.1, docs/length_baseline_results.md):
  1. Aggregate AUROC/AUPRC, reported alongside the D1 length-only baseline
     (AUROC 0.652, AUPRC 0.183, floor 0.091 -- computed on the raw, undeduped
     52,725-row human_test split. Our curated test set removes 89 train-dupe rows
     + 212 bad-residue rows (301 total, 0.57%), landing at 52,424 rows -- too small
     a shift to expect these baseline numbers to move meaningfully, but flagged
     here rather than silently treated as identical).
  2. Performance stratified by sequence-length decile (bin by len_a + len_b,
     qcut into 10 bins -- same approach as docs/length_baseline_results.md /
     src/spikes/length_baseline.py and the Phase 1 EDA positive-fraction-by-length
     check). This is required, not optional -- a model that only beats the
     length-only floor in aggregate but shows no lift within each length stratum
     is not learning past the confound.

Loading + producing test-set probabilities differs materially by variant (mean/attn
reuse train_frozen.py's cache; lora has none and reruns the real model) -- those
paths are kept separate below; the metrics/reporting logic is the one genuinely
shared piece.

Usage:
    python evaluate.py --run-dir ../../../runs/phase2_m1_d1/smoke \
        --data-dir ../../../data/curated/d1_ppi_smoke --variant mean
    python evaluate.py --run-dir ../../../runs/phase2_m3_d1/smoke \
        --data-dir ../../../data/curated/d1_ppi_smoke --variant lora
"""
import argparse
import json
from pathlib import Path

import pandas as pd
import torch

from model import (
    D_MODEL_300M,
    apply_lora,
    batch_features,
    combine_pair,
    get_pooling,
    load_esmc_300m,
    pad_hidden_states,
    PairClassifier,
    PairHead,
    safe_auroc_auprc,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

# D1 length-only baseline, from docs/length_baseline_results.md, computed on the raw
# 52,725-row human_test split (our curated test.csv is 52,424 rows after both required
# filters -- 0.57% smaller, not expected to move these numbers meaningfully).
D1_LENGTH_BASELINE = {
    "AUROC": 0.6522,
    "AUPRC": 0.1826,
    "positive_rate_floor": 0.0909,
    "n_test_raw": 52725,
}


def stratified_by_length(test_df, probs, labels, n_bins=10):
    df = test_df.copy()
    df["prob"] = probs
    df["label"] = labels
    try:
        df["len_bin"] = pd.qcut(df["len_sum"], n_bins, labels=False, duplicates="drop")
    except ValueError as e:
        return [{"bin": "all", "note": f"qcut failed: {e}"}]

    rows = []
    for b, g in df.groupby("len_bin"):
        auroc, auprc, note = safe_auroc_auprc(g["label"].values, g["prob"].values)
        rows.append({
            "bin": int(b),
            "n": len(g),
            "n_pos": int(g["label"].sum()),
            "len_sum_min": int(g["len_sum"].min()),
            "len_sum_max": int(g["len_sum"].max()),
            "AUROC": auroc,
            "AUPRC": auprc,
            "note": note,
        })
    return rows


def predict_frozen(run_dir, data_dir, variant, device="cpu"):
    """M1 (variant='mean') / M2 (variant='attn'): reload the head (+ pooling, for
    attn) and the cache train_frozen.py saved, no backbone needed at eval time."""
    test_df = pd.read_csv(data_dir / "test.csv")
    test_idx = torch.load(run_dir / "test_indices.pt", map_location="cpu")
    labels = test_idx["labels"].numpy()

    head = PairHead(d_model=D_MODEL_300M)
    head.load_state_dict(torch.load(run_dir / "head.pt", map_location="cpu"))
    head.eval()

    if variant == "mean":
        cache = torch.load(run_dir / "embedding_cache.pt", map_location="cpu")
        embedding_matrix = cache["embedding_matrix"]
        with torch.no_grad():
            combined = batch_features(test_idx["idx_a"], test_idx["idx_b"], embedding_matrix)
            probs = torch.sigmoid(head(combined)).numpy()
    else:  # attn
        pooling = get_pooling("attn", D_MODEL_300M)
        pooling.load_state_dict(torch.load(run_dir / "pooling.pt", map_location="cpu"))
        pooling.eval()
        hidden_cache = torch.load(run_dir / "hidden_state_cache.pt", map_location="cpu")
        hidden_list = hidden_cache["hidden_list"]
        idx_a, idx_b = test_idx["idx_a"], test_idx["idx_b"]

        chunk = 512
        probs_chunks = []
        with torch.no_grad():
            for start in range(0, len(idx_a), chunk):
                a, b = idx_a[start:start + chunk], idx_b[start:start + chunk]
                unique_idx = torch.unique(torch.cat([a, b]))
                local_pos = {int(gi): li for li, gi in enumerate(unique_idx.tolist())}
                tensors = [hidden_list[int(gi)] for gi in unique_idx]
                padded, mask = pad_hidden_states(tensors)
                pooled_unique = pooling(padded, mask)
                a_local = torch.tensor([local_pos[int(gi)] for gi in a.tolist()], dtype=torch.long)
                b_local = torch.tensor([local_pos[int(gi)] for gi in b.tolist()], dtype=torch.long)
                combined = combine_pair(pooled_unique[a_local], pooled_unique[b_local])
                probs_chunks.append(torch.sigmoid(head(combined)))
        probs = torch.cat(probs_chunks).numpy()

    assert len(probs) == len(test_df), "test_indices.pt row count doesn't match curated test.csv"
    return test_df, probs, labels


def predict_lora(run_dir, data_dir, device="cpu", batch_size=32):
    """M3: no cache -- reload the full PairClassifier (LoRA backbone + pooling +
    head) from run_dir/train_meta.json's recorded config and run a real forward
    pass over the test set's raw sequences."""
    test_df = pd.read_csv(data_dir / "test.csv")
    with open(run_dir / "train_meta.json") as f:
        meta = json.load(f)

    backbone, tokenizer = load_esmc_300m(device=device)
    lora_backbone = apply_lora(backbone, r=meta["lora_r"], lora_alpha=meta["lora_alpha"],
                                lora_dropout=meta.get("lora_dropout", 0.0))
    pooling = get_pooling(meta["pooling"], D_MODEL_300M)
    head = PairHead(d_model=D_MODEL_300M)
    clf = PairClassifier(lora_backbone, tokenizer, pooling, head, backbone_trainable=True)
    # mmap=True avoids briefly holding two full copies of the ~335M-param model in RAM
    # (the freshly-built clf + the freshly-loaded state dict) -- the same class of
    # memory spike that motivated load_esmc_300m()'s mmap workaround, here on the
    # checkpoint this pipeline itself saves.
    state_dict = torch.load(run_dir / "model.pt", map_location="cpu", mmap=True, weights_only=True)
    clf.load_state_dict(state_dict, assign=True)
    clf = clf.to(device)
    clf.eval()

    pad_id = tokenizer.pad_token_id
    probs_chunks = []
    with torch.no_grad():
        for start in range(0, len(test_df), batch_size):
            chunk_df = test_df.iloc[start:start + batch_size]
            ids_a = _tokenize_batch(chunk_df["seq_a"].tolist(), tokenizer, pad_id, device)
            ids_b = _tokenize_batch(chunk_df["seq_b"].tolist(), tokenizer, pad_id, device)
            logits = clf(ids_a, ids_b)
            probs_chunks.append(torch.sigmoid(logits).cpu())
    probs = torch.cat(probs_chunks).numpy()
    labels = test_df["label"].values
    return test_df, probs, labels


def _tokenize_batch(seqs, tokenizer, pad_id, device):
    token_lists = [tokenizer.encode(s) for s in seqs]
    max_len = max(len(t) for t in token_lists)
    padded = torch.full((len(seqs), max_len), pad_id, dtype=torch.long)
    for i, t in enumerate(token_lists):
        padded[i, :len(t)] = torch.tensor(t, dtype=torch.long)
    return padded.to(device)


MODEL_LABELS = {
    "mean": "M1 (ESM-C 300M frozen, mean-pool)",
    "attn": "M2 (ESM-C 300M frozen, attention-pool)",
    "lora": "M3 (ESM-C 300M LoRA-wrapped backbone)",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=str(REPO_ROOT / "runs" / "phase2_m1_d1" / "smoke"))
    ap.add_argument("--data-dir", default=str(REPO_ROOT / "data" / "curated" / "d1_ppi_smoke"))
    ap.add_argument("--variant", choices=["mean", "attn", "lora"], default="mean")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--n-bins", type=int, default=10)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    data_dir = Path(args.data_dir)

    if args.variant in ("mean", "attn"):
        test_df, probs, labels = predict_frozen(run_dir, data_dir, args.variant, device=args.device)
    else:
        test_df, probs, labels = predict_lora(run_dir, data_dir, device=args.device)

    auroc, auprc, note = safe_auroc_auprc(labels, probs)
    pos_rate = float(labels.mean())

    print(f"=== Aggregate {MODEL_LABELS[args.variant]} vs. length-only baseline ===")
    comparison = pd.DataFrame([
        {"model": MODEL_LABELS[args.variant], "n_test": len(test_df),
         "positive_rate": round(pos_rate, 4), "AUROC": auroc, "AUPRC": auprc, "note": note},
        {"model": "length-only baseline (docs/length_baseline_results.md)", "n_test": D1_LENGTH_BASELINE["n_test_raw"],
         "positive_rate": D1_LENGTH_BASELINE["positive_rate_floor"],
         "AUROC": D1_LENGTH_BASELINE["AUROC"], "AUPRC": D1_LENGTH_BASELINE["AUPRC"], "note": None},
    ])
    print(comparison.to_string(index=False))

    print(f"\n=== Stratified by length decile (bin on len_a + len_b, n_bins={args.n_bins}) ===")
    strat = stratified_by_length(test_df, probs, labels, args.n_bins)
    strat_df = pd.DataFrame(strat)
    print(strat_df.to_string(index=False))

    SMOKE_SCALE_THRESHOLD = 1000
    if len(test_df) < SMOKE_SCALE_THRESHOLD:
        caveat = ("Smoke-test scale (n_test={}) -- metrics are not meaningful, this only "
                  "verifies the eval harness runs end-to-end and produces the required "
                  "aggregate + stratified numbers.").format(len(test_df))
    else:
        caveat = None

    out = {
        "variant": args.variant,
        "model_label": MODEL_LABELS[args.variant],
        "aggregate": {
            "n_test": len(test_df),
            "positive_rate": round(pos_rate, 4),
            "AUROC": auroc,
            "AUPRC": auprc,
            "note": note,
        },
        "length_baseline_comparison": D1_LENGTH_BASELINE,
        "stratified_by_length_decile": strat,
        "caveat": caveat,
    }
    with open(run_dir / "eval_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nWrote {run_dir / 'eval_results.json'}")


if __name__ == "__main__":
    main()
