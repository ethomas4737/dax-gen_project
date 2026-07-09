# Combined dataset variants (D1-D4) + EDA

## Current state
**Last updated:** 2026-07-09
**Status:** done
**Load-bearing:** `rawdata/combined/{d1_ppi,d2_avida,d3_ppi_avida,d4_heldout_mlaep_ace2}.csv` are the training-pool/held-out-eval artifacts for whatever downstream PLM fine-tuning follows. `docs/eda-combined.md` is the human-facing report.
**What's new since last update:** Initial build + EDA, pulling forward the Phase-1-deferred dataset-merging item at explicit human request (see `spec/spec.md` Revision 2026-07-09).

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

D1 row count verified against the sum of its 7 source files (716,517 = 421,792+52,725+55,000×4+22,000). D2 = 573,891+5,580. D3 = 716,517+579,471. All match.

## Verification

- Zero missing values in any of the 4 files.
- **Held-out cleanliness (the key check for this design):** confirmed zero sequence overlap between D4's held-out set (ACE2 + all 19,132 RBD mutants) and the D3 training pool, in both directions. The held-out evaluation is genuinely uncontaminated.
- ACE2 sequence vocabulary: fully standard-alphabet (0 non-standard residues). Same for all RBD mutants.
- Positive fractions per source match the individually-curated Phase-1 numbers exactly (D1 species rates = 9.09%, D2 hIL6/hTNFa = 3.66%/12.22%, D4 held-out ACE2-bind = 8.05%) — combining didn't alter per-source statistics, as expected for a straight concatenation.

## Findings

- **D1↔D2 overlap:** exactly 1 sequence (human TNF-alpha, 233aa) appears in both D1 (as a generic PPI protein) and D2 (as the AVIDa-hTNFa antigen). Not a leakage concern since both are part of the same D3 training pool — just a notable cross-dataset subject-matter overlap.
- **D4 held-out has zero length variance:** every RBD mutant is exactly 201aa; ACE2 is a constant 805aa. This means the Phase-1 length-confound (positive fraction varying with pair length) mechanically cannot manifest in the held-out evaluation — there's no length variation to correlate with there.
- **ACE2 (805aa) exceeds D1's training length cap (800aa) by 5 residues** — a minor but real distribution-shift point: the held-out set isn't only a new domain, it also sits just past the edge of the training length distribution.
- **Column semantics are inconsistent across D3's `pair_type`s:** `seq_a`/`seq_b` are symmetric generic proteins in the `ppi` rows but asymmetric (antibody vs. antigen) in the `antibody_antigen` rows. Worth an explicit role indicator if the downstream architecture needs to distinguish these.
- D3 has 3,886 exact duplicate rows, inherited almost entirely from D1's known `ecoli_test.tsv` duplicates (see `docs/eda-ppi.md`) — not a new issue introduced by combining.

## Provenance

- Phase 1 curated data commit provenance: see `rawdata/{ppi,avida,mlaep}/SOURCE.md`.
- ACE2 sequence: UniProt Q9BYF1, canonical isoform, fetched live 2026-07-09 via `rest.uniprot.org`.
- Output location: `rawdata/combined/` (gitignored; provenance in `rawdata/combined/SOURCE.md`).
- Spec revision recorded: `spec/spec.md` "Revision 2026-07-09 — dataset combinations requested".
