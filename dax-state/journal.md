# Journal

Append-only chronology. One row per event. Write with `Edit` (append) never with `Write` (overwrite).

Event categories: `session` (session-start / -resume / -end), `plan` (plan revision), `step` (step-start / -complete / -blocked), `decision`, `dispatch` (agent call — append cost block at end of summary), `qa` (QA result), `ops` (infra action, e.g., commits, pushes, DCC ops), `promote` (spike→src move), `note` (anything else).

For `dispatch` rows, append a cost block at the end of the summary: `(model=…, tokens=…, tool_uses=…, wall=…s)`.

| Timestamp (ET) | Category | Step | Summary |
|---|---|---|---|
| 2026-07-09 | ops | — | Scaffolded `dax-gen_project` from `dax-demo` template (moved template content up one level, dropped redundant nested harness/tools clones, fresh git init). Pinned harness SHA `f29e04997e9e310fd0cf26e330cc87f4d8e08845`. |
| 2026-07-09 | note | — | Drafted Phase 1 spec: curate D-SCRIPT PPI, AVIDa-hIL6+hTNFa antibody, and MLAEP viral-evolution datasets separately; produce EDA per dataset. Downstream modeling task deliberately deferred. |
| 2026-07-09 | note | — | Verified D-SCRIPT human PPI pairs (15,816 unique proteins) via mygene.info: 0 COVID/coronavirus hits; 1 non-functional IGHV pseudogene entry (33/474,517 pairs, all negative labels) — kept, per human decision. |
| 2026-07-09 | ops | — | Updated README.md + CLAUDE.md for the real project name/goal; renamed `docs/walkthrough.md` → `docs/dax-demo-walkthrough.md`; refreshed dax-state placeholders. |
| 2026-07-09 | plan | — | Drafted `plan-phase1.md` (9 steps: env verify, fetch+QA x3 datasets, EDA+QA). Human approved. |
| 2026-07-09 | step | 0 | Env verify done: existing user micromamba env `eda` has pandas/numpy/matplotlib/seaborn/requests; no new installs needed (fetch via plain HTTP, no `datasets`/`huggingface_hub` required). |
| 2026-07-09 | step | 1 | D-SCRIPT PPI data fetched into `rawdata/ppi/` (commit `23cbb0f`); all 13 files present, row counts match. See runs/phase1-1.md. |
| 2026-07-09 | qa | 1-qa | PASS. Label format inconsistency found: human files use int `0`/`1`, other species use float `0.0`/`1.0` — EDA must normalize. |
| 2026-07-09 | step | 2 | AVIDa-hIL6 + AVIDa-hTNFa fetched into `rawdata/avida/` (HF revisions pinned); hTNFa license confirmed CC-BY-NC-4.0. See runs/phase1-2.md. |
| 2026-07-09 | qa | 2-qa | PASS. 0 SARS-CoV-2 Ag_labels in either file. Column order differs between hIL6/hTNFa files (label/Ag_label swapped) — EDA must read by name. |
| 2026-07-09 | step | 3 | MLAEP 7 preprocessed files fetched into `rawdata/mlaep/` (commit `cbd21f4`). See runs/phase1-3.md. |
| 2026-07-09 | qa | 3-qa | PASS. All files size-verified. Noted `merged_all.jsonl` is generic (non-COVID) structural data, distinct from the other 6 COVID-specific files. |
| 2026-07-09 | step | 4 | EDA generated for all 3 datasets: `docs/eda-{ppi,avida,mlaep}.md` + 8 figures. Positive fraction reported per spec (PPI ~9.09% fixed ratio; AVIDa hIL6 3.66%/hTNFa 12.22%; MLAEP ACE2-bind 8.05% + 8 per-clone escape fractions). See runs/phase1-4.md. |
| 2026-07-09 | qa | 4-qa | PASS. Independently recomputed 3 headline positive-fraction numbers by separate method (awk / fresh pandas read) — exact match. All 8 figures valid PNGs; reports clean of leftover errors. |
| 2026-07-09 | note | — | Built `docs/phase1_eda_walkthrough.ipynb` — human follow-along notebook consolidating steps 1-4, executed end-to-end (16 code cells, 0 errors) with the `eda` conda env registered as a Jupyter kernel. Re-verifies exclusions live. See runs/phase1-notebook.md. |
| 2026-07-09 | note | — | Added "PLM-readiness" section to the walkthrough notebook (human plans to use a PLM downstream): context-window fit (all clear), vocabulary check (PPI has U/X in ~0.1-0.3% of seqs), positive-fraction-vs-length-bin. **New finding: PPI positive fraction is not flat by pair length** (0.165 shortest decile vs ~0.07-0.08 mid-range vs 0.103 longest) — a real shortcut-learning risk flagged for the downstream modeling phase. 21 code cells, 0 errors. See runs/phase1-notebook.md. |
| 2026-07-09 | note | — | Drafted `docs/phase1_eda_summary.md` — consolidated cross-dataset EDA report (TL;DR, per-dataset numbers, length-confound writeup, PLM-readiness table, data-quality notes, recommendations for Phase 2 scoping). Adds 2 new saved figures (`plm_length_vs_context_window.png`, `plm_ppi_positive_fraction_by_length.png`) previously only inline in the notebook. |
