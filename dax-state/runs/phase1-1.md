# 1 — Fetch & curate D-SCRIPT PPI data

## Current state
**Last updated:** 2026-07-09
**Status:** done
**Load-bearing:** `rawdata/ppi/{pairs,seqs}/*` is the input for Phase 1 Step 4 (PPI EDA).
**What's new since last update:** Initial fetch + QA.

## Setup

| | |
|---|---|
| Conda env | `/hpc/home/emt70/micromamba/envs/eda` (pandas 2.3.3, requests 2.34.2) |
| Tool versions | curl (system) |
| Input file(s) | github.com/samsledje/D-SCRIPT `data/pairs/*.tsv`, `data/seqs/*.fasta` |
| Compute | DCC login node (CPU/IO-bound, no GPU needed) |

## Command (literal)

```bash
DSCRIPT_SHA=$(curl -s https://api.github.com/repos/samsledje/D-SCRIPT/commits/main | python3 -c "import json,sys;print(json.load(sys.stdin)['sha'])")
# DSCRIPT_SHA=23cbb0fbbb454d09ee41ff749c1454d8b3c8a4b8
for f in human_train.tsv human_test.tsv mouse_test.tsv fly_test.tsv yeast_test.tsv worm_test.tsv ecoli_test.tsv; do
  curl -s -o "rawdata/ppi/pairs/$f" "https://raw.githubusercontent.com/samsledje/D-SCRIPT/$DSCRIPT_SHA/data/pairs/$f"
done
for f in human.fasta mouse.fasta fly.fasta yeast.fasta worm.fasta ecoli.fasta; do
  curl -s -o "rawdata/ppi/seqs/$f" "https://raw.githubusercontent.com/samsledje/D-SCRIPT/$DSCRIPT_SHA/data/seqs/$f"
done
```

## Counts

| File | Rows/seqs |
|---|---|
| pairs/human_train.tsv | 421,792 |
| pairs/human_test.tsv | 52,725 |
| pairs/{mouse,fly,yeast}_test.tsv | 55,000 each |
| pairs/ecoli_test.tsv | 22,000 |
| seqs/human.fasta | 70,529 |
| seqs/mouse.fasta | 40,606 |
| seqs/fly.fasta | 19,310 |
| seqs/worm.fasta | 25,930 |
| seqs/yeast.fasta | 5,664 |
| seqs/ecoli.fasta | 8,848 |

## Verification

- All 13 expected files present and non-empty (`wc -l` check).
- Label column sanity: only `{0,1}` or `{0.0,1.0}` values present across all pair files — no corrupt/out-of-range labels.
- Human protein IDs (15,816 unique across train+test) resolved via mygene.info: 0 coronavirus hits; 1 non-functional IGHV pseudogene (33/474,517 pairs, all negative label) — see `rawdata/ppi/SOURCE.md`.
- `grep -i "cov|sars|antibody"` flagged hits in every fasta file, but inspection confirmed these are incidental substring matches inside amino-acid sequences (e.g. "...IDKKDECPTS...") — not real keyword content. Not an exclusion violation.

## Findings

- **Label format is inconsistent across species**: `human_{train,test}.tsv` use integer labels (`0`/`1`); `mouse/fly/yeast/worm/ecoli_test.tsv` use float-formatted labels (`0.0`/`1.0`). EDA script must cast to a common type before computing positive fraction.
- D-SCRIPT repo data is clean by construction — no separate filtering step was needed, only verification.

## Provenance

- Project repo: commit at time of run — see `dax-state/journal.md` row for this step.
- D-SCRIPT commit pinned: `23cbb0fbbb454d09ee41ff749c1454d8b3c8a4b8`.
- Output location: `rawdata/ppi/` (gitignored; not in repo history).
