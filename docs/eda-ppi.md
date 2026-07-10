# EDA — PPI (D-SCRIPT)

**Generated:** 2026-07-09 | **Source:** `rawdata/ppi/` (see `SOURCE.md`)

## Positive fraction & row counts by dataset/species

| dataset     |   n_rows |   positive_fraction |   n_unique_proteins |   n_duplicate_rows |   n_missing_values |
|:------------|---------:|--------------------:|--------------------:|-------------------:|-------------------:|
| human_train |   421792 |              0.0909 |               15816 |                  0 |                  0 |
| human_test  |    52725 |              0.0909 |               15525 |                  0 |                  0 |
| mouse_test  |    55000 |              0.0909 |               37497 |                  0 |                  0 |
| fly_test    |    55000 |              0.0909 |               19213 |                  0 |                  0 |
| yeast_test  |    55000 |              0.0909 |                5664 |                  0 |                  0 |
| worm_test   |    55000 |              0.0909 |               25429 |                  0 |                  0 |
| ecoli_test  |    22000 |              0.0909 |                7138 |               3761 |                  0 |

## Sequence length distribution by species

| species   |   n_sequences |   length_min |   length_median |   length_mean |   length_max |
|:----------|--------------:|-------------:|----------------:|--------------:|-------------:|
| human     |         70529 |           50 |             406 |         415.5 |          800 |
| mouse     |         40606 |           50 |             370 |         392.4 |          800 |
| fly       |         19310 |           50 |             376 |         388   |          800 |
| yeast     |          5664 |           50 |             314 |         341.5 |          800 |
| worm      |         25930 |           50 |             335 |         351.8 |          800 |
| ecoli     |          8848 |           50 |             262 |         286.5 |          799 |

## Duplicate sequences (identical seq, different protein ID)

- human: 54898 duplicate sequence(s)

- mouse: 22689 duplicate sequence(s)

- fly: 7966 duplicate sequence(s)

- yeast: 73 duplicate sequence(s)

- worm: 7575 duplicate sequence(s)

- ecoli: 4436 duplicate sequence(s)


## Figures

![](figures/ppi_positive_fraction.png)

![](figures/ppi_seq_length_hist.png)


## Notes

- Label column normalized to int (source files mix `0`/`1` and `0.0`/`1.0` formatting across species).

- `n_unique_proteins` counts proteins referenced in that species' pair file(s), not the full species fasta (which may include unpaired proteins).

- **Positive fraction is exactly ~0.0909 (1/11) for every species and split** — indicates the D-SCRIPT benchmark uses a fixed 1:10 positive:negative sampling ratio by construction, not an incidental class imbalance.

- **Sequence lengths are hard-capped in [50, 800] aa** for every species — a deliberate preprocessing filter in the source data, not a natural distribution tail.

- **Large fraction of duplicate sequences** (same amino-acid sequence under different protein IDs) — e.g. human: 54,898/70,529 (78%), mouse: 22,689/40,606 (56%). Likely reflects transcript-isoform redundancy in the underlying STRING/Ensembl protein set rather than a data error; worth accounting for if training on this data (isoform duplicates could leak between train/test).

- `ecoli_test.tsv` has 3,761 duplicate **rows** (exact pair+label duplicates) out of 22,000 — unlike any other species file (all had 0). Worth flagging if using ecoli as a held-out test set.

## D1 curated train/val/test split (Phase 2 addendum, 2026-07-10)

The curated, modeling-ready D1 (post-dedup, post-bad-residue-filter human split — `data/curated/d1_ppi/`) is further divided three ways for Phase 2 training: `human_test` stays untouched as a single-use held-out test set, and a validation split is carved out of `human_train` for per-epoch monitoring, so the test metric is never touched during training.

| Split | Rows | Positive rate | Notes |
|:------|-----:|---------------:|:------|
| train | 377,924 | 0.0912 | 90% of the cleaned 419,916-row train set |
| val   |  41,992 | 0.0912 | 10%, stratified by label, fixed seed |
| test  |  52,424 | 0.0912 | unchanged from the original clean test set |

**Split verification:**
- Row-count sum exact: 377,924 + 41,992 = 419,916 (the pre-split clean train count).
- Label balance: train/val positive-rate difference = 0.0000.
- Overlap: zero pairwise row overlap between train/val, val/test, and train/test (row-hash check over `(protein_a, protein_b, label)`).
- `test.csv` confirmed byte-identical (sha256 match) to its pre-split version — never touched by the split logic.

**Length-distribution parity (checked 2026-07-10, given the length confound below):** train and val match closely on both central tendency and the length-confound shape — train len_sum mean 752.9 (std 263.1) vs. val 751.9 (std 263.2); positive rate by length decile is nearly identical between the two (e.g. shortest decile ~0.16-0.17 in both, longest decile ~0.10-0.11 in both). The 90/10 stratified-by-label split did not introduce a length skew, so val is an unbiased monitoring signal for training, not a biased one — relevant given PPI's positive fraction is known to vary meaningfully by pair length (see PLM-readiness note above).

See `dax-state/runs/phase2-1c-6-validation-split.md` for the full run record and `dax-state/decisions.md`'s 2026-07-10 entry for why the split exists (val monitors training; test is reserved for final reporting only).
