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

Usage:
    python data_prep.py                  # full curation (writes data/curated/d1_ppi/{train,test}.csv)
    python data_prep.py --smoke-n-train 100 --smoke-n-test 50 --seed 0
                                          # also writes a tiny CPU-smoke subset to
                                          # data/curated/d1_ppi_smoke/{train,test}.csv
"""
import argparse
from pathlib import Path

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

    assert len(train) == EXPECTED_TRAIN_ROWS_CLEAN, f"final train count {len(train)} != {EXPECTED_TRAIN_ROWS_CLEAN}"
    assert len(test) == EXPECTED_TEST_ROWS_CLEAN, f"final test count {len(test)} != {EXPECTED_TEST_ROWS_CLEAN}"

    train.to_csv(out_dir / "train.csv", index=False)
    test.to_csv(out_dir / "test.csv", index=False)

    print(f"Wrote {out_dir/'train.csv'} ({len(train)} rows; removed {n_bad_train} bad-residue rows from raw {EXPECTED_TRAIN_ROWS_RAW})")
    print(f"Wrote {out_dir/'test.csv'} ({len(test)} rows; removed {n_dupe} train-dupe + {n_bad_test} bad-residue rows "
          f"({n_overlap} overlap) from raw {EXPECTED_TEST_ROWS_RAW})")
    return train, test, n_dupe


def make_smoke_subset(train, test, n_train, n_test, seed, out_dir=None):
    """Deterministic random subsample for a CPU smoke test. Stratified-ish: just a
    plain random sample (label imbalance at this scale is expected and fine --
    the smoke test only checks the pipeline runs, not that metrics are meaningful).
    """
    out_dir = out_dir or (CURATED / "d1_ppi_smoke")
    out_dir.mkdir(parents=True, exist_ok=True)

    smoke_train = train.sample(n=n_train, random_state=seed).reset_index(drop=True)
    smoke_test = test.sample(n=n_test, random_state=seed).reset_index(drop=True)

    smoke_train.to_csv(out_dir / "train.csv", index=False)
    smoke_test.to_csv(out_dir / "test.csv", index=False)

    print(f"Wrote {out_dir/'train.csv'} ({len(smoke_train)} rows, {smoke_train['label'].sum()} positive)")
    print(f"Wrote {out_dir/'test.csv'} ({len(smoke_test)} rows, {smoke_test['label'].sum()} positive)")
    return smoke_train, smoke_test


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke-n-train", type=int, default=100)
    ap.add_argument("--smoke-n-test", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-smoke", action="store_true")
    args = ap.parse_args()

    train, test, n_removed = curate()

    if not args.skip_smoke:
        make_smoke_subset(train, test, args.smoke_n_train, args.smoke_n_test, args.seed)


if __name__ == "__main__":
    main()
