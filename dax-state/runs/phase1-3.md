# 3 — Fetch & curate MLAEP data

## Current state
**Last updated:** 2026-07-09
**Status:** done
**Load-bearing:** `rawdata/mlaep/*` is the input for Phase 1 Step 4 (MLAEP EDA).
**What's new since last update:** Initial fetch + QA.

## Setup

| | |
|---|---|
| Conda env | `/hpc/home/emt70/micromamba/envs/eda` |
| Input source | github.com/WHan-alter/MLAEP `data/` (public repo) |
| Compute | DCC login node (CPU/IO-bound) |

## Command (literal)

```bash
MLAEP_SHA=$(curl -s https://api.github.com/repos/WHan-alter/MLAEP/commits/master | python3 -c "import json,sys;print(json.load(sys.stdin)['sha'])")
# MLAEP_SHA=cbd21f48e53aaed80c460ce8bf9fad41cc637bed
for f in Covid19_RBD_seq.txt GMM_covid_info_seq.csv merged_all.jsonl pVNT.csv pVNT_seq.csv sars-cov-2_variants_update.csv site_class.csv; do
  curl -s -o "rawdata/mlaep/$f" "https://raw.githubusercontent.com/WHan-alter/MLAEP/$MLAEP_SHA/data/$f"
done
```

## Counts

All 7 expected files fetched, sizes match repo listing exactly (201B–4.7MB). See `rawdata/mlaep/SOURCE.md` for per-file content description.

## Verification

- File sizes byte-match the GitHub repo's listed sizes for each file (cross-checked against `api.github.com/repos/WHan-alter/MLAEP/contents/data` from earlier reconnaissance).
- No exclusion filtering needed/applicable — MLAEP is entirely SARS-CoV-2-focused by design (spec explicitly exempts it from the COVID-exclusion rule that applies to PPI/AVIDa).

## Findings

- `merged_all.jsonl` contains generic protein structures (arbitrary sequence + backbone coordinates), not SARS-CoV-2-specific — likely the structural-model pretraining set, distinct in kind from the other 6 (all COVID-specific) files. Worth treating separately in EDA.
- `GMM_covid_info_seq.csv` includes per-antibody-clone escape columns (`COV2-2096_400`, etc.) — this is deep mutational scanning / escape data, not a simple binary label; EDA "positive fraction" framing may need adaptation here (e.g. escape-score distributions rather than a single binary label).
- Raw GISAID corpus not fetched (requires individual registration) — noted as deferred in spec.

## Provenance

- MLAEP commit pinned: `cbd21f48e53aaed80c460ce8bf9fad41cc637bed`.
- Output location: `rawdata/mlaep/` (gitignored).
