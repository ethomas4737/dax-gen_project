# 4 — EDA per dataset

## Current state
**Last updated:** 2026-07-09
**Status:** done
**Load-bearing:** `docs/eda-{ppi,avida,mlaep}.md` + `docs/figures/*.png` are the Phase 1 deliverable.
**What's new since last update:** Initial EDA + independent QA spot-checks.

## Setup

| | |
|---|---|
| Conda env | `/hpc/home/emt70/micromamba/envs/eda` (added `tabulate` via pip for `to_markdown()`) |
| Spike scripts | `src/spikes/eda_ppi.py`, `src/spikes/eda_avida.py`, `src/spikes/eda_mlaep.py` |
| Input file(s) | `rawdata/{ppi,avida,mlaep}/*` |
| Compute | DCC login node (CPU-only) |

## Command (literal)

```bash
/hpc/home/emt70/micromamba/envs/eda/bin/python src/spikes/eda_ppi.py
/hpc/home/emt70/micromamba/envs/eda/bin/python src/spikes/eda_avida.py
/hpc/home/emt70/micromamba/envs/eda/bin/python src/spikes/eda_mlaep.py
```

## Counts

| Output | Count |
|---|---|
| `docs/eda-ppi.md` | 1 report (7 species/split rows, 6 species seq-length rows) |
| `docs/eda-avida.md` | 1 report (2 datasets, 31+1 antigen rows) |
| `docs/eda-mlaep.md` | 1 report (7 file sections) |
| `docs/figures/*.png` | 8 figures |

## Verification

Independently recomputed 3 headline positive-fraction numbers by a separate method (awk / fresh pandas read, not reusing the EDA script's dataframe) and confirmed exact match:
- PPI `human_train`: awk `38344/421792=0.0909074` vs report `0.0909`. Match.
- AVIDa hIL6 overall: fresh read `20980/573891=0.036557` vs report `0.0366`. Match.
- MLAEP `ace2_bind`: fresh read `1540/19132=0.080493` vs report `0.0805`. Match.

All 8 PNG figures verified non-empty with valid PNG magic bytes (`89504e47`). All 3 markdown reports checked for leftover `NaN`/`Traceback`/`Error` artifacts — clean.

## Findings

- **PPI**: positive fraction is exactly ~9.09% (1/11) across every species/split — fixed 1:10 sampling ratio by construction. Sequence lengths hard-capped [50,800]aa. Large duplicate-sequence fractions (human 78%, mouse 56%) reflect isoform redundancy, not error. `ecoli_test.tsv` uniquely has 3,761 duplicate rows.
- **AVIDa**: hIL6 overall positive fraction 3.66%, varies substantially by antigen mutant (see `docs/eda-avida.md` table); hTNFa overall 12.22% (single antigen). hIL6's apparent 93% "duplicate VHH sequence" rate is expected — each of 38,599 unique VHH clones is tested against a median of 14 (up to 31) antigen variants.
- **MLAEP**: `GMM_covid_info_seq.csv` ACE2-binding positive fraction 8.05%; per-antibody escape fractions range 4.1%–18.2% across the 8 clones. `merged_all.jsonl` (18 generic structures) has no interaction label — "positive fraction" doesn't apply there. `pVNT.csv` has 2 variants with *negative* neutralization-reduction (enhanced neutralization, not an error).

## Provenance

- Data commit/revision SHAs: see `rawdata/{ppi,avida,mlaep}/SOURCE.md` and `dax-state/runs/phase1-{1,2,3}.md`.
- Scripts remain in `src/spikes/` (not promoted) — hardcoded paths/dates, no CLI args; fails promotion criterion 2 (reusability). Promotion decision deferred to phase close per `../dax/agent-configs/promotion-rules.md`.
