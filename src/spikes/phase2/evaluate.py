"""Phase 2 / M1-on-D1 evaluation harness.

Study code (src/spikes/phase2/). Required reporting per project policy
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

Usage:
    python evaluate.py --run-dir ../../../runs/phase2_m1_d1/smoke \
        --data-dir ../../../data/curated/d1_ppi_smoke
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import average_precision_score, roc_auc_score

from model import D_MODEL_300M, PairHead, batch_features

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


def safe_auroc_auprc(labels, probs):
    if len(np.unique(labels)) < 2:
        return None, None, "only one class present"
    return round(roc_auc_score(labels, probs), 4), round(average_precision_score(labels, probs), 4), None


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=str(REPO_ROOT / "runs" / "phase2_m1_d1" / "smoke"))
    ap.add_argument("--data-dir", default=str(REPO_ROOT / "data" / "curated" / "d1_ppi_smoke"))
    ap.add_argument("--n-bins", type=int, default=10)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    data_dir = Path(args.data_dir)

    test_df = pd.read_csv(data_dir / "test.csv")

    head = PairHead(d_model=D_MODEL_300M)
    head.load_state_dict(torch.load(run_dir / "head.pt", map_location="cpu"))
    head.eval()

    cache = torch.load(run_dir / "embedding_cache.pt", map_location="cpu")
    embedding_matrix = cache["embedding_matrix"]
    test_idx = torch.load(run_dir / "test_indices.pt", map_location="cpu")

    with torch.no_grad():
        combined_test = batch_features(test_idx["idx_a"], test_idx["idx_b"], embedding_matrix)
        logits = head(combined_test)
        probs = torch.sigmoid(logits).numpy()
    labels = test_idx["labels"].numpy()

    assert len(probs) == len(test_df), "test_indices.pt row count doesn't match curated test.csv"

    auroc, auprc, note = safe_auroc_auprc(labels, probs)
    pos_rate = float(labels.mean())

    print("=== Aggregate M1-on-D1 (smoke scale) vs. length-only baseline ===")
    comparison = pd.DataFrame([
        {"model": "M1 (ESM-C 300M frozen, mean-pool)", "n_test": len(test_df),
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
