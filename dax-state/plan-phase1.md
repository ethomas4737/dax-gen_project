# Phase 1 plan — curate 3 datasets + per-dataset EDA

## Current state
**Last updated:** 2026-07-09
**Load-bearing as of this date:** Steps 0–3-qa done (all 3 datasets fetched+curated+QA'd into `rawdata/`). Step 4 (EDA) in progress.
**What's new since last update:** Data fetch/curation complete for all 3 datasets; see `dax-state/runs/phase1-{1,2,3}.md`.

Active execution plan for Phase 1. Step IDs map to spec deliverables 1–4. Status defaults to `not started`; update on step start/complete per the operational protocol in `CLAUDE.md`.

| Step ID | Status | Description | Inputs | Outputs | Role | Deps | Notes (plan-time, ≤200 chars) | Outcome (≤80 chars) |
|---|---|---|---|---|---|---|---|---|
| 0 | done | Env verify | — | working env | executor | — | No DCC/GPU needed. | done — using existing `eda` micromamba env, no new installs needed |
| 1 | done | Fetch & curate D-SCRIPT PPI data | github.com/samsledje/D-SCRIPT `data/pairs`,`data/seqs` | `rawdata/ppi/` + `SOURCE.md` | executor | 0 | Pinned commit `23cbb0f...`. | done — see runs/phase1-1.md |
| 1-qa | done | QA: verify all 6 species train/test pairs+fasta present, row counts match source, no excluded content | `rawdata/ppi/` | qa note | qa-executor | 1 | | done — all present; label format inconsistency noted (int vs float) |
| 2 | done | Fetch & curate AVIDa antibody data (hIL6 + hTNFa only) | huggingface.co/datasets/COGNANO/AVIDa-hIL6, AVIDa-hTNFa | `rawdata/avida/` + `SOURCE.md` | executor | 0 | Pinned HF revisions. hTNFa license confirmed CC-BY-NC-4.0. | done — see runs/phase1-2.md |
| 2-qa | done | QA: confirm only hIL6+hTNFa present, zero SARS-CoV-2 rows, schema matches AVIDa-hIL6 docs | `rawdata/avida/` | qa note | qa-executor | 2 | | done — 0 SARS-CoV-2 Ag_labels; column-order mismatch noted |
| 3 | done | Fetch & curate MLAEP data | github.com/WHan-alter/MLAEP `data/` (7 listed files) | `rawdata/mlaep/` + `SOURCE.md` | executor | 0 | Pinned commit `cbd21f4...`. | done — see runs/phase1-3.md |
| 3-qa | done | QA: confirm all 7 files present, pinned commit recorded | `rawdata/mlaep/` | qa note | qa-executor | 3 | | done — all 7 files size-verified |
| 4 | in progress | EDA per dataset (3 separate reports, not merged): row counts, **positive fraction** (overall + by species/antigen/variant), sequence-length distributions, category breakdowns, missingness, duplicate-sequence checks | `rawdata/{ppi,avida,mlaep}/` | `docs/eda-ppi.*`, `docs/eda-avida.*`, `docs/eda-mlaep.*` | executor | 1-qa, 2-qa, 3-qa | Keep reports separate per dataset — no merged/joint analysis this phase. | |
| 4-qa | not started | QA: each EDA report runs end-to-end; spot-check reported stats against raw files | `docs/eda-*` | qa note | qa-executor | 4 | | |

After all step-QA passes: promote spike script(s) from `src/spikes/` to `src/` per `../dax/agent-configs/promotion-rules.md`, append journal rows, update `session-handoff.md`, commit per `[<step-id>] <short action>`.
