# Combined dataset variants (D1-D4) + EDA

## Current state
**Last updated:** 2026-07-09
**Status:** done
**Load-bearing:** `rawdata/combined/{d1_ppi,d2_avida,d3_ppi_avida,d4_heldout_mlaep_ace2,d4_heldout_mlaep_antibodies}.csv` are the training-pool/held-out-eval artifacts for whatever downstream PLM fine-tuning follows. `docs/eda-combined.md` is the human-facing report.
**What's new since last update:** Added a second held-out axis — sourced real VH/VL sequences for MLAEP's 8-antibody escape panel from CoV-AbDab (after the original paper's authors gated the data behind "available on request"), built 153,056 additional held-out rows, label-flipped to `1=binds` per human's direction.

## Setup

| | |
|---|---|
| Conda env | `/hpc/home/emt70/micromamba/envs/eda` |
| Build script | `src/spikes/build_combined_datasets.py` |
| EDA script | `src/spikes/eda_combined.py` |
| Inputs | `rawdata/{ppi,avida,mlaep}/*` (Phase 1 curated data) + human ACE2 sequence (UniProt Q9BYF1, fetched live) |
| Compute | DCC login node (CPU/IO-bound) |

## Command (literal)

```bash
/hpc/home/emt70/micromamba/envs/eda/bin/python src/spikes/build_combined_datasets.py
/hpc/home/emt70/micromamba/envs/eda/bin/python src/spikes/eda_combined.py
```

## Counts

| Variant | Rows | File |
|---|---|---|
| D1 (PPI, all species) | 716,517 | `d1_ppi.csv` |
| D2 (AVIDa, no COVID) | 579,471 | `d2_avida.csv` |
| D3 (D1 ∪ D2) | 1,295,988 | `d3_ppi_avida.csv` |
| D4 held-out (MLAEP/ACE2) | 19,132 | `d4_heldout_mlaep_ace2.csv` |
| D4 held-out (MLAEP/8-antibody panel) | 153,056 | `d4_heldout_mlaep_antibodies.csv` |

D1 row count verified against the sum of its 7 source files (716,517 = 421,792+52,725+55,000×4+22,000). D2 = 573,891+5,580. D3 = 716,517+579,471. Antibody panel = 8 × 19,132. All match.

## Sourcing the antibody panel (COV2-2050/2096/2094/2677/2479/2165/2499/2832)

The human explicitly asked to try sourcing real sequences for these 8 named clones (MLAEP only has escape *labels*, not the antibodies' own sequences). Search path:
1. Bloom lab GitHub repo (`jbloomlab/SARS-CoV-2-RBD_MAP_Crowe_antibodies`) — confirmed correct source paper, but no antibody sequences (RBD-side data only).
2. Original paper (Zost et al. 2020, *Nature Medicine*, PMC8194108) — explicitly states "Datasets are available from the corresponding authors upon reasonable request." No GenBank accessions.
3. Vanderbilt/Crowe patent family (US11345741, WO2021195418A1, US20210300999A1) — has real sequences, but only for the 2 clones that became the clinical candidate (COV2-2196/2130, aka Evusheld) — none of our 8.
4. PDB full-text search — hits were false positives (different antibodies/structures citing our clone names in passing).
5. **CoV-AbDab** (Oxford OPIG, `opig.stats.ox.ac.uk/webapps/covabdab`) — downloaded the full CSV (`CoV-AbDab_080224.csv`, 12,918 entries) and found exact `Name` matches for all 8 clones, each correctly citing Zost et al. 2020 as source, each with populated `VHorVHH`/`VL` columns. This succeeded where 1-4 didn't — CoV-AbDab evidently obtained/curated these independently of the "on request" gate.

## Verification

- Zero missing values in any of the 5 files.
- **Held-out cleanliness (the key check for this design):** confirmed zero sequence overlap between the D3 training pool and BOTH held-out axes — ACE2+RBD mutants, and the 8 antibodies+RBD mutants — in both directions. Both held-out evaluations are genuinely uncontaminated.
- ACE2 and all 8 antibody VH/VL sequences: fully standard-alphabet (0 non-standard residues). Same for all RBD mutants.
- Positive fractions per source match the individually-curated Phase-1 numbers exactly (D1 species rates = 9.09%, D2 hIL6/hTNFa = 3.66%/12.22%, D4 held-out ACE2-bind = 8.05%) — combining didn't alter per-source statistics, as expected for a straight concatenation.
- **Label polarity flip verified correct:** antibody-panel `binds` fractions (82–96% per clone) cross-checked as exactly `1 - escape_fraction` against the original MLAEP escape numbers reported in `docs/eda-mlaep.md` — e.g. COV2-2050: 1−0.077=0.923 ✓, COV2-2096: 1−0.182=0.818 ✓ (all 8 matched).

## Findings

- **D1↔D2 overlap:** exactly 1 sequence (human TNF-alpha, 233aa) appears in both D1 (as a generic PPI protein) and D2 (as the AVIDa-hTNFa antigen). Not a leakage concern since both are part of the same D3 training pool — just a notable cross-dataset subject-matter overlap.
- **D4 held-out has zero length variance:** every RBD mutant is exactly 201aa; ACE2 is a constant 805aa. This means the Phase-1 length-confound (positive fraction varying with pair length) mechanically cannot manifest in the held-out evaluation — there's no length variation to correlate with there.
- **ACE2 (805aa) exceeds D1's training length cap (800aa) by 5 residues** — a minor but real distribution-shift point: the held-out set isn't only a new domain, it also sits just past the edge of the training length distribution.
- **Column semantics are inconsistent across D3's `pair_type`s:** `seq_a`/`seq_b` are symmetric generic proteins in the `ppi` rows but asymmetric (antibody vs. antigen) in the `antibody_antigen` rows. Worth an explicit role indicator if the downstream architecture needs to distinguish these.
- D3 has 3,886 exact duplicate rows, inherited almost entirely from D1's known `ecoli_test.tsv` duplicates (see `docs/eda-ppi.md`) — not a new issue introduced by combining.

## Provenance

- Phase 1 curated data commit provenance: see `rawdata/{ppi,avida,mlaep}/SOURCE.md`.
- ACE2 sequence: UniProt Q9BYF1, canonical isoform, fetched live 2026-07-09 via `rest.uniprot.org`.
- 8-antibody VH/VL: CoV-AbDab download (`CoV-AbDab_080224.csv`, 2026-07-09), originating from Zost et al. 2020, *Nature Medicine* (https://www.nature.com/articles/s41591-020-0998-x). Hardcoded in `src/spikes/build_combined_datasets.py` (`ANTIBODY_VH_VL` dict) with full provenance comment.
- Output location: `rawdata/combined/` (gitignored; provenance in `rawdata/combined/SOURCE.md`).
- Spec revision recorded: `spec/spec.md` "Revision 2026-07-09 — dataset combinations requested".
