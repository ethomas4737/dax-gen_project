# Phase 1 EDA walkthrough notebook

## Current state
**Last updated:** 2026-07-09
**Status:** done
**Load-bearing:** `docs/phase1_eda_walkthrough.ipynb` is a human-facing verification/follow-along artifact. Section 4 (PLM-readiness) contains genuinely new findings not in the original Phase 1 EDA scripts/reports — see below.
**What's new since last update:** Added a "PLM-readiness checks" section (context-window fit, vocabulary/non-standard residues, positive-fraction-vs-length-bin) in response to the human noting a PLM is planned downstream.

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

22 code cells, 17 markdown cells, all executed with 0 errors (verified via `nbformat` scan for `output_type == "error"`).

## Verification

- All headline numbers re-derived live in the notebook (not copy-pasted from the earlier scripts) and cross-checked against `docs/runs/phase1-{1,2,3,4}.md`: PPI 0 COVID hits / 1 non-functional IGHV pseudogene hit (exact match); AVIDa 0 SARS-CoV-2 Ag_labels in either file (exact match).
- No error outputs in any cell.

## Findings

Structured as: intro → PPI → AVIDa → MLAEP → PLM-readiness → **train/test identity-leakage (new)** → summary table.

Findings from section 4 (PLM-readiness), prompted by the human's plan to use a PLM downstream:
- **Context window:** nothing exceeds ~1022 residues anywhere (max 800 for PPI, 201 MLAEP, 179 AVIDa) — no truncation handling needed for any dataset.
- **Vocabulary:** AVIDa and MLAEP are fully standard-alphabet (20 aa). **PPI is not** — `U` (selenocysteine) and `X` (unresolved residue) appear in human (221/70,529 seqs), mouse (217/40,606), fly (8/19,310), worm (1/25,930); yeast/ecoli clean.
- **Length-confounded labels — real finding for PPI:** positive fraction is NOT flat across sequence-length deciles (unlike the flat ~9.09% across species). Shortest-pair decile = 0.165 (~1.8x baseline), longest = 0.103, middle deciles ~0.07-0.08. This is a genuine shortcut-learning risk for a length-sensitive PLM-based classifier.
- AVIDa-hIL6's analogous by-length-bin pattern is noisy/non-monotonic — judged more likely confounded with antigen identity (positive fraction already varies 1.1-13.7% by antigen) than a clean length effect; flagged with lower confidence than the PPI finding.

**Section 5 — train/test identity leakage (PPI), the highest-priority finding in this whole EDA phase:**
- **100% of `human_test`'s 15,525 unique proteins — by protein ID AND by exact sequence — already appear in `human_train`.** Zero test proteins are genuinely unseen.
- 89/52,725 test pairs (0.17%) are exact duplicates of a train pair (same two sequences, same label).
- Root cause: the split holds out pairings, not proteins — combined with the high isoform-duplication rate already found in §1.3.
- Implication: "test performance" on this benchmark demonstrates generalization to new pairings of known proteins, not to genuinely novel proteins — a materially weaker claim than usually assumed of a train/test split. A protein-level held-out split would need to be constructed separately if the downstream goal requires that claim.
- Only checked for human (only species with both train+test files); mouse/fly/yeast/worm/ecoli are test-only cross-species-transfer files, a different question.

## Provenance

- Same data/commit provenance as `dax-state/runs/phase1-{1,2,3}.md`.
- Notebook re-runs the mygene.info and AVIDa exclusion checks live (not cached) — reproduces the step 1/2 QA independently.
