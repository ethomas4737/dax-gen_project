"""Phase 2 / D1 data prep: load D-SCRIPT human PPI pairs + sequences, apply the
two required cleaning filters, and write a curated, modeling-ready copy to
data/curated/d1_ppi/.

Study code (src/spikes/phase2/) -- not yet promoted.

Required cleaning step 1 (per project spec): human_test.tsv contains 89 rows that
are exact sequence-pair duplicates of rows already in human_train.tsv -- real
train/test leakage. We drop them and assert the count matches exactly (see
dedup_test_against_train docstring for the exact matching methodology). If the
count differs, we stop rather than silently proceeding.

Required cleaning step 2 (per coordinator instruction, added after the initial
build): drop every pair (in both human_train and human_test) that involves a
protein whose sequence contains a non-standard amino acid character (outside
ACDEFGHIKLMNPQRSTVWY -- in this data that's U or X specifically, no other
non-standard codes present). Filtered at the protein level: build the set of
"bad" protein IDs from the fasta (221/70,529 proteins: 145 with U, 76 with X, no
overlap), then drop any pair row where protein_a or protein_b is in that set.
Verified independently (see run-note): 1,876/421,792 train rows (0.445%),
212/52,725 test rows (0.402%) involve a bad protein; overall positive rate shift
is negligible (9.09% -> 9.12%), consistent with the coordinator's figures.

Both filters are computed independently against the raw loaded data (not
sequentially re-derived from each other's output), so the order they're applied
in doesn't change the final kept row set -- a row is dropped if it matches
EITHER predicate. Verified zero overlap between the two filters on human_test
(the 89 dedup rows and the 212 bad-residue rows are disjoint), so final test
row count = 52,725 - 89 - 212 = 52,424. Final train row count = 421,792 - 1,876
= 419,916 (train only gets the residue filter -- dedup only removes from test).

Val split (added 2026-07-10, step 1c, per dax-state/decisions.md's 2026-07-10 entry): the
curated train set is further split 90/10, stratified by label, fixed seed, into a new
train.csv + val.csv. This exists so train_frozen.py/train_lora.py have a dedicated split
for per-epoch validation monitoring -- test.csv is NOT touched by this and stays reserved
purely for final held-out reporting (the whole point of carving out val.csv is to stop
reusing test.csv for any monitoring decision). See split_train_val() below for the exact
methodology and VAL_FRAC/VAL_SEED for the chosen ratio/seed.

Usage:
    python data_prep.py                  # full curation (writes data/curated/d1_ppi/{train,val,test}.csv)
    python data_prep.py --smoke-n-train 100 --smoke-n-test 50 --smoke-n-val 10 --seed 0
                                          # also writes a tiny CPU-smoke subset to
                                          # data/curated/d1_ppi_smoke/{train,val,test}.csv
"""
import argparse
import gc
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
RAWDATA = REPO_ROOT / "rawdata" / "ppi"
CURATED = REPO_ROOT / "data" / "curated"

STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")

EXPECTED_TRAIN_ROWS_RAW = 421792
EXPECTED_TEST_ROWS_RAW = 52725
EXPECTED_DUPES_REMOVED = 89
EXPECTED_BAD_RESIDUE_PROTEINS = 221
EXPECTED_BAD_RESIDUE_TRAIN_ROWS = 1876
EXPECTED_BAD_RESIDUE_TEST_ROWS = 212
EXPECTED_TRAIN_ROWS_CLEAN = EXPECTED_TRAIN_ROWS_RAW - EXPECTED_BAD_RESIDUE_TRAIN_ROWS  # 419916
EXPECTED_TEST_ROWS_CLEAN = EXPECTED_TEST_ROWS_RAW - EXPECTED_DUPES_REMOVED - EXPECTED_BAD_RESIDUE_TEST_ROWS  # 52424

# Step 1c (2026-07-10 decision): dedicated val split carved out of the cleaned train set,
# stratified by label, fixed seed. human_test.csv is never touched by this.
VAL_FRAC = 0.10
VAL_SEED = 42


def read_pairs(path):
    df = pd.read_csv(path, sep="\t", header=None, names=["protein_a", "protein_b", "label"])
    # normalize label to int -- some species files store label as float-string
    df["label"] = df["label"].astype(float).astype(int)
    return df


def read_fasta(path):
    seqs = {}
    cur_id, cur_seq = None, []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if cur_id is not None:
                    seqs[cur_id] = "".join(cur_seq)
                cur_id, cur_seq = line[1:], []
            else:
                cur_seq.append(line)
        if cur_id is not None:
            seqs[cur_id] = "".join(cur_seq)
    return seqs


def dedup_test_against_train(train_df, test_df):
    """Anti-join test against train on the **sequence-pair** (not protein-ID) triple,
    matching the exact methodology used in docs/phase1_eda_walkthrough.ipynb (Section 5,
    "Level 3: whole-pair sequence overlap") that produced the "89" figure documented in
    docs/phase1_eda_summary.md Section 2.1.

    Both train_df and test_df must already have seq_a/seq_b columns attached.

    Key details that matter for reproducing exactly 89 (verified empirically -- a naive
    anti-join on (protein_a, protein_b, label) IDs gives 0, because PPI has heavy
    isoform-level sequence duplication under different protein IDs (see
    docs/eda-ppi.md); ordered-ID or label-conditioned variants also do not reproduce 89):
      - Match on the *sequence content* of the pair, not the protein ID -- the same
        physical pair can appear under different ID pairs due to isoform duplicates.
      - Match *unordered* -- (seq_a, seq_b) and (seq_b, seq_a) count as the same pair
        (`frozenset`), except self-pairs (seq_a == seq_b) which use a plain tuple key.
      - Label is NOT part of the match key (the notebook's pair-sequence overlap check
        does not condition on label).

    Returns (is_dupe_mask, n_removed) -- a boolean mask over test_df, not a filtered
    copy, so the caller can combine it with other independently-computed drop
    predicates (e.g. the bad-residue filter) via OR before actually dropping rows.
    Raises if n_removed != 89.
    """
    def pair_key(a, b):
        return frozenset([a, b]) if a != b else (a, b)

    train_pair_seqs = set(pair_key(a, b) for a, b in zip(train_df["seq_a"], train_df["seq_b"]))
    is_dupe = [pair_key(a, b) in train_pair_seqs for a, b in zip(test_df["seq_a"], test_df["seq_b"])]
    is_dupe = pd.Series(is_dupe, index=test_df.index)

    n_removed = int(is_dupe.sum())

    if n_removed != EXPECTED_DUPES_REMOVED:
        raise RuntimeError(
            f"Dedup mismatch: expected exactly {EXPECTED_DUPES_REMOVED} train/test "
            f"duplicate rows removed from human_test.tsv, got {n_removed}. "
            f"Stopping rather than silently proceeding -- see docs/phase1_eda_summary.md Section 2.1."
        )
    return is_dupe, n_removed


def find_bad_residue_proteins(seqs):
    """Protein IDs whose sequence contains a character outside the standard
    20-letter amino acid alphabet (ACDEFGHIKLMNPQRSTVWY). In this data that's
    U or X specifically -- verified no other non-standard codes are present."""
    bad_ids = set(pid for pid, s in seqs.items() if set(s) - STANDARD_AA)
    if len(bad_ids) != EXPECTED_BAD_RESIDUE_PROTEINS:
        raise RuntimeError(
            f"Bad-residue protein count changed: expected {EXPECTED_BAD_RESIDUE_PROTEINS}, "
            f"got {len(bad_ids)}. Stopping rather than silently proceeding."
        )
    return bad_ids


def bad_residue_row_mask(df, bad_ids):
    return df["protein_a"].isin(bad_ids) | df["protein_b"].isin(bad_ids)


def attach_sequences_and_lengths(df, seqs):
    df = df.copy()
    df["seq_a"] = df["protein_a"].map(seqs)
    df["seq_b"] = df["protein_b"].map(seqs)
    missing = df["seq_a"].isna() | df["seq_b"].isna()
    if missing.any():
        raise RuntimeError(f"{int(missing.sum())} pairs reference protein IDs missing from human.fasta")
    df["len_a"] = df["seq_a"].str.len()
    df["len_b"] = df["seq_b"].str.len()
    df["len_sum"] = df["len_a"] + df["len_b"]
    return df


def split_train_val(train, val_frac=VAL_FRAC, seed=VAL_SEED):
    """Carve a dedicated validation split out of an already-curated train set:
    90/10, stratified by label, fixed seed (step 1c). Returns (new_train, val),
    both re-indexed. Sampling is done independently within each label group
    (pandas .sample(frac=...)) so the positive rate is preserved (up to rounding)
    in both the shrunk train set and the new val set.
    """
    val_parts, train_parts = [], []
    for _, group in train.groupby("label", sort=True):
        val_group = group.sample(frac=val_frac, random_state=seed)
        train_group = group.drop(val_group.index)
        val_parts.append(val_group)
        train_parts.append(train_group)

    # Shuffle the concatenated pieces (groupby leaves label-sorted blocks otherwise).
    val = pd.concat(val_parts).sample(frac=1, random_state=seed).reset_index(drop=True)
    new_train = pd.concat(train_parts).sample(frac=1, random_state=seed).reset_index(drop=True)

    assert len(new_train) + len(val) == len(train), (
        f"split_train_val row-count mismatch: {len(new_train)} + {len(val)} != {len(train)}"
    )
    return new_train, val


def _row_hashes(df):
    """Row-identity hash for overlap checks over (protein_a, protein_b, label), as a
    numpy uint64 array -- deliberately NOT a Python set of (str, str, int) tuples /
    frozensets, which is far more RAM-hungry at D1 scale (~420K+ rows) on this node's
    tight shared memory budget (see run-note Finding: a tuple/frozenset-based version
    of this check OOM-killed the whole curate() pipeline). hash_pandas_object hashes
    are not guaranteed collision-free, but at this row count the false-positive-overlap
    probability is negligible and this is a diagnostic invariant check, not the dedup
    logic itself (that already happened, exactly, in dedup_test_against_train)."""
    return pd.util.hash_pandas_object(df[["protein_a", "protein_b", "label"]], index=False).to_numpy()


def verify_split(train, val, test, label="full"):
    """Print + assert the required step 1c invariants: counts sum correctly, label
    balance is preserved within a small tolerance between train/val, and there is
    zero row overlap between train/val/test (all three pairwise checks). Uses
    numpy-array row hashes (see _row_hashes) rather than Python sets of tuples to
    keep this cheap on a memory-constrained node."""
    n_train, n_val, n_test = len(train), len(val), len(test)
    pos_rate_train = float(train["label"].mean())
    pos_rate_val = float(val["label"].mean())
    pos_rate_test = float(test["label"].mean())
    balance_diff = abs(pos_rate_train - pos_rate_val)

    h_train, h_val, h_test = _row_hashes(train), _row_hashes(val), _row_hashes(test)
    n_overlap_train_val = int(np.intersect1d(h_train, h_val, assume_unique=False).size)
    n_overlap_val_test = int(np.intersect1d(h_val, h_test, assume_unique=False).size)
    n_overlap_train_test = int(np.intersect1d(h_train, h_test, assume_unique=False).size)
    del h_train, h_val, h_test

    print(f"--- verify_split ({label}) ---")
    print(f"  rows: train={n_train}, val={n_val}, test={n_test}")
    print(f"  positive rate: train={pos_rate_train:.4f}, val={pos_rate_val:.4f}, "
          f"test={pos_rate_test:.4f} (train/val diff={balance_diff:.4f})")
    print(f"  overlap: train/val={n_overlap_train_val}, val/test={n_overlap_val_test}, "
          f"train/test={n_overlap_train_test}")

    BALANCE_TOLERANCE = 0.01
    assert balance_diff < BALANCE_TOLERANCE, (
        f"train/val positive-rate diff {balance_diff:.4f} exceeds tolerance {BALANCE_TOLERANCE}"
    )
    assert n_overlap_train_val == 0, f"{n_overlap_train_val} overlapping rows between train/val"
    assert n_overlap_val_test == 0, f"{n_overlap_val_test} overlapping rows between val/test"
    assert n_overlap_train_test == 0, f"{n_overlap_train_test} overlapping rows between train/test"

    return {
        "n_train": n_train, "n_val": n_val, "n_test": n_test,
        "pos_rate_train": pos_rate_train, "pos_rate_val": pos_rate_val, "pos_rate_test": pos_rate_test,
        "balance_diff": balance_diff,
        "overlap_train_val": n_overlap_train_val,
        "overlap_val_test": n_overlap_val_test,
        "overlap_train_test": n_overlap_train_test,
    }


def curate(out_dir=None):
    """Full D1 curation: load, apply both required row filters, attach sequences/lengths,
    write to data/curated/d1_ppi/. Both filters (train/test sequence-pair dedup, and
    bad-residue-protein exclusion) are computed against the raw loaded data and combined
    via OR before dropping -- see module docstring for why order doesn't matter here."""
    out_dir = out_dir or (CURATED / "d1_ppi")
    out_dir.mkdir(parents=True, exist_ok=True)

    seqs = read_fasta(RAWDATA / "seqs" / "human.fasta")
    train_raw = read_pairs(RAWDATA / "pairs" / "human_train.tsv")
    test_raw = read_pairs(RAWDATA / "pairs" / "human_test.tsv")

    assert len(train_raw) == EXPECTED_TRAIN_ROWS_RAW, f"train row count changed: {len(train_raw)} != {EXPECTED_TRAIN_ROWS_RAW}"
    assert len(test_raw) == EXPECTED_TEST_ROWS_RAW, f"raw test row count changed: {len(test_raw)} != {EXPECTED_TEST_ROWS_RAW}"

    bad_ids = find_bad_residue_proteins(seqs)
    is_bad_train = bad_residue_row_mask(train_raw, bad_ids)
    is_bad_test = bad_residue_row_mask(test_raw, bad_ids)
    n_bad_train, n_bad_test = int(is_bad_train.sum()), int(is_bad_test.sum())
    if n_bad_train != EXPECTED_BAD_RESIDUE_TRAIN_ROWS or n_bad_test != EXPECTED_BAD_RESIDUE_TEST_ROWS:
        raise RuntimeError(
            f"Bad-residue row count mismatch: expected train={EXPECTED_BAD_RESIDUE_TRAIN_ROWS}, "
            f"test={EXPECTED_BAD_RESIDUE_TEST_ROWS}; got train={n_bad_train}, test={n_bad_test}. "
            f"Stopping rather than silently proceeding."
        )

    # Sequences must be attached before dedup -- the required dedup step matches on
    # sequence-pair content, not protein ID (see dedup_test_against_train docstring).
    train_raw = attach_sequences_and_lengths(train_raw, seqs)
    test_raw = attach_sequences_and_lengths(test_raw, seqs)

    is_dupe_test, n_dupe = dedup_test_against_train(train_raw, test_raw)
    n_overlap = int((is_dupe_test & is_bad_test).sum())

    train = train_raw.loc[~is_bad_train].reset_index(drop=True)
    test = test_raw.loc[~(is_dupe_test | is_bad_test)].reset_index(drop=True)

    # Free the pre-filter frames + masks -- this node runs under a tight, shared
    # ~2GB job-wide memory cgroup (see run-note), and holding train_raw/test_raw
    # alive alongside their filtered copies through the val-split step below is
    # unnecessary peak memory this pipeline doesn't need to carry.
    del train_raw, test_raw, is_bad_train, is_bad_test, is_dupe_test
    gc.collect()

    assert len(train) == EXPECTED_TRAIN_ROWS_CLEAN, f"final train count {len(train)} != {EXPECTED_TRAIN_ROWS_CLEAN}"
    assert len(test) == EXPECTED_TEST_ROWS_CLEAN, f"final test count {len(test)} != {EXPECTED_TEST_ROWS_CLEAN}"

    # Step 1c: carve the val split out of the cleaned train set (test.csv is untouched).
    train, val = split_train_val(train)
    verify_split(train, val, test, label="full")

    train.to_csv(out_dir / "train.csv", index=False)
    val.to_csv(out_dir / "val.csv", index=False)
    test.to_csv(out_dir / "test.csv", index=False)

    print(f"Wrote {out_dir/'train.csv'} ({len(train)} rows; removed {n_bad_train} bad-residue rows from raw "
          f"{EXPECTED_TRAIN_ROWS_RAW}, then carved out {len(val)} val rows)")
    print(f"Wrote {out_dir/'val.csv'} ({len(val)} rows; {VAL_FRAC:.0%} stratified-by-label split of the cleaned "
          f"train set, seed={VAL_SEED})")
    print(f"Wrote {out_dir/'test.csv'} ({len(test)} rows; removed {n_dupe} train-dupe + {n_bad_test} bad-residue rows "
          f"({n_overlap} overlap) from raw {EXPECTED_TEST_ROWS_RAW}; untouched by the val split)")
    return train, val, test, n_dupe


def make_smoke_subset(train, val, test, n_train, n_test, n_val, seed, out_dir=None):
    """Deterministic random subsample for a CPU smoke test. Stratified-ish: just a
    plain random sample (label imbalance at this scale is expected and fine --
    the smoke test only checks the pipeline runs, not that metrics are meaningful).
    Sampled independently from each of the already-disjoint full train/val/test sets,
    so the smoke subsets stay disjoint too.
    """
    out_dir = out_dir or (CURATED / "d1_ppi_smoke")
    out_dir.mkdir(parents=True, exist_ok=True)

    smoke_train = train.sample(n=n_train, random_state=seed).reset_index(drop=True)
    smoke_val = val.sample(n=min(n_val, len(val)), random_state=seed).reset_index(drop=True)
    smoke_test = test.sample(n=n_test, random_state=seed).reset_index(drop=True)

    smoke_train.to_csv(out_dir / "train.csv", index=False)
    smoke_val.to_csv(out_dir / "val.csv", index=False)
    smoke_test.to_csv(out_dir / "test.csv", index=False)

    print(f"Wrote {out_dir/'train.csv'} ({len(smoke_train)} rows, {smoke_train['label'].sum()} positive)")
    print(f"Wrote {out_dir/'val.csv'} ({len(smoke_val)} rows, {smoke_val['label'].sum()} positive)")
    print(f"Wrote {out_dir/'test.csv'} ({len(smoke_test)} rows, {smoke_test['label'].sum()} positive)")
    return smoke_train, smoke_val, smoke_test


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke-n-train", type=int, default=100)
    ap.add_argument("--smoke-n-test", type=int, default=50)
    ap.add_argument("--smoke-n-val", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-smoke", action="store_true")
    args = ap.parse_args()

    train, val, test, n_removed = curate()

    if not args.skip_smoke:
        make_smoke_subset(train, val, test, args.smoke_n_train, args.smoke_n_test, args.smoke_n_val, args.seed)


if __name__ == "__main__":
    main()
