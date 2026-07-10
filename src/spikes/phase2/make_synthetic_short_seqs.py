"""Phase 2 / M3 smoke-test helper: build a tiny synthetic short-sequence (20-35aa)
train/val/test set for train_lora.py's CPU smoke test.

Study code (src/spikes/phase2/) -- one-shot smoke-data generator, not a real
curated dataset (does not represent D1 in any way).

Why this exists: M3's trainable-backbone forward+backward OOMs (exit 137) on this
node's tight, shared memory budget even at smoke scale when run against real D1
sequences (~300-800aa) -- a known, accepted limitation (see run-note
phase2-1c-6-validation-split.md and dax-state/journal.md 2026-07-10 "M3 CPU-smoke
finding"). Full-scale / full-length validation only works on the eventual GPU node.
This script produces short (20-35aa), purely synthetic amino-acid sequences instead,
so train_lora.py's *logic* (including the new per-epoch validation loop) can be
smoke-tested end-to-end on CPU without hitting that memory ceiling. The resulting
data has no biological meaning and is never used for anything but a pipeline
correctness check.

Usage:
    python make_synthetic_short_seqs.py --out-dir ../../../data/intermediate/d1_ppi_smoke_lora_short \
        --n-train 15 --n-val 10 --n-test 10 --seed 3
"""
import argparse
import random
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
STANDARD_AA = "ACDEFGHIKLMNPQRSTVWY"


def make_split(n_pairs, n_proteins, rng, id_prefix):
    """n_proteins short (20-35aa) synthetic sequences, sampled into n_pairs random
    pairs with a random 0/1 label (label has no real relationship to sequence
    content -- this is a pipeline-logic smoke test only, not a modeling exercise)."""
    ids = [f"{id_prefix}{i}" for i in range(n_proteins)]
    seqs = {pid: "".join(rng.choices(STANDARD_AA, k=rng.randint(20, 35))) for pid in ids}
    rows = []
    for _ in range(n_pairs):
        a, b = rng.choice(ids), rng.choice(ids)
        label = rng.randint(0, 1)
        rows.append({"protein_a": a, "protein_b": b, "label": label,
                      "seq_a": seqs[a], "seq_b": seqs[b]})
    df = pd.DataFrame(rows)
    df["len_a"] = df["seq_a"].str.len()
    df["len_b"] = df["seq_b"].str.len()
    df["len_sum"] = df["len_a"] + df["len_b"]
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(REPO_ROOT / "data" / "intermediate" / "d1_ppi_smoke_lora_short"))
    ap.add_argument("--n-train", type=int, default=15)
    ap.add_argument("--n-val", type=int, default=10)
    ap.add_argument("--n-test", type=int, default=10)
    ap.add_argument("--n-proteins", type=int, default=12)
    ap.add_argument("--seed", type=int, default=3)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train = make_split(args.n_train, args.n_proteins, rng, "synprot")
    val = make_split(args.n_val, args.n_proteins, rng, "synprot")
    test = make_split(args.n_test, args.n_proteins, rng, "synprot")

    train.to_csv(out_dir / "train.csv", index=False)
    val.to_csv(out_dir / "val.csv", index=False)
    test.to_csv(out_dir / "test.csv", index=False)

    print(f"Wrote {out_dir/'train.csv'} ({len(train)} rows, seq len 20-35aa, synthetic)")
    print(f"Wrote {out_dir/'val.csv'} ({len(val)} rows)")
    print(f"Wrote {out_dir/'test.csv'} ({len(test)} rows)")


if __name__ == "__main__":
    main()
