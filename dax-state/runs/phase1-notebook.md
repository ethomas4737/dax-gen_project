# Phase 1 EDA walkthrough notebook

## Current state
**Last updated:** 2026-07-09
**Status:** done
**Load-bearing:** `docs/phase1_eda_walkthrough.ipynb` is a human-facing verification/follow-along artifact consolidating steps 1–4's work; not a new analysis (no new findings beyond `dax-state/runs/phase1-{1,2,3,4}.md`).
**What's new since last update:** Initial creation.

## Setup

| | |
|---|---|
| Conda env | `/hpc/home/emt70/micromamba/envs/eda` (added `nbformat`, `nbconvert`, `ipykernel`, `jupyter_client` via pip) |
| Kernel | Registered as `eda` via `python -m ipykernel install --user --name eda --display-name eda` |
| Input file(s) | `rawdata/{ppi,avida,mlaep}/*` (same inputs as steps 1–3) |

## Command (literal)

```bash
/hpc/home/emt70/micromamba/envs/eda/bin/python -m ipykernel install --user --name eda --display-name eda
/hpc/home/emt70/micromamba/envs/eda/bin/jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.kernel_name=eda --ExecutePreprocessor.timeout=180 \
  docs/phase1_eda_walkthrough.ipynb
```

## Counts

16 code cells, 12 markdown cells, all executed with 0 errors (verified via `nbformat` scan for `output_type == "error"`).

## Verification

- All headline numbers re-derived live in the notebook (not copy-pasted from the earlier scripts) and cross-checked against `docs/runs/phase1-{1,2,3,4}.md`: PPI 0 COVID hits / 1 non-functional IGHV pseudogene hit (exact match); AVIDa 0 SARS-CoV-2 Ag_labels in either file (exact match).
- No error outputs in any cell.

## Findings

No new findings — this notebook consolidates and re-verifies steps 1–4's results for human review, structured as: intro → PPI (load, positive fraction, seq-length, exclusion re-verification) → AVIDa (overview, by-antigen, seq-length, exclusion re-verification) → MLAEP (binary-label positive fractions, remaining 6 files) → summary table.

## Provenance

- Same data/commit provenance as `dax-state/runs/phase1-{1,2,3}.md`.
- Notebook re-runs the mygene.info and AVIDa exclusion checks live (not cached) — reproduces the step 1/2 QA independently.
