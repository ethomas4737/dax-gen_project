# 2 — Fetch & curate AVIDa antibody data

## Current state
**Last updated:** 2026-07-09
**Status:** done
**Load-bearing:** `rawdata/avida/*.csv` is the input for Phase 1 Step 4 (AVIDa EDA).
**What's new since last update:** Initial fetch + QA.

## Setup

| | |
|---|---|
| Conda env | `/hpc/home/emt70/micromamba/envs/eda` |
| Input source | huggingface.co/datasets/COGNANO/{AVIDa-hIL6,AVIDa-hTNFa} (public, not gated) |
| Compute | DCC login node (CPU/IO-bound) |

## Command (literal)

```bash
curl -sL -o rawdata/avida/AVIDa-hIL6.csv "https://huggingface.co/datasets/COGNANO/AVIDa-hIL6/resolve/main/AVIDa-hIL6.csv"
curl -sL -o rawdata/avida/hIL6_antigen_sequences.csv "https://huggingface.co/datasets/COGNANO/AVIDa-hIL6/resolve/main/antigen_sequences.csv"
curl -sL -o rawdata/avida/AVIDa-hTNFa.csv "https://huggingface.co/datasets/COGNANO/AVIDa-hTNFa/resolve/main/AVIDa-hTNFa.csv"
curl -sL -o rawdata/avida/hTNFa_antigen_sequences.csv "https://huggingface.co/datasets/COGNANO/AVIDa-hTNFa/resolve/main/antigen_sequences.csv"
```

## Counts

| File | Rows (excl. header) |
|---|---|
| AVIDa-hIL6.csv | 573,891 |
| hIL6_antigen_sequences.csv | 31 |
| AVIDa-hTNFa.csv | 5,580 |
| hTNFa_antigen_sequences.csv | 1 |

## Verification

- Row counts match published dataset size (573,891 for hIL6, per paper).
- `Ag_label` unique-value check: hIL6 = 31 values, all `IL-6_*` (WT + 30 point mutants); hTNFa = 1 value, `TNFa-WT-beads`. Zero SARS-CoV-2/coronavirus antigen labels — confirms `AVIDa-SARS-CoV-2` exclusion holds.
- License confirmed CC-BY-NC-4.0 for both via HF API tags (resolves spec open question #1).

## Findings

- **Column order differs between files**: hIL6 is `VHH_sequence,label,Ag_label,...`; hTNFa is `VHH_sequence,Ag_label,label,...` (label/Ag_label swapped). EDA script must read by column name.
- hTNFa dataset is ~100x smaller than hIL6 (5,580 vs 573,891 pairs) and has only 1 antigen variant vs 31 — expect very different EDA profile between the two.

## Provenance

- HF dataset revisions pinned: hIL6 `cd783d573e015f83364e42287810ad597850aeed`; hTNFa `60c8288fd3721b0dca4f76655b491cfe7dd82d5d` (see `rawdata/avida/SOURCE.md`).
- Output location: `rawdata/avida/` (gitignored).
