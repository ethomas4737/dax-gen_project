# Session handoff

**Read this first.** Live cursor of project state. Rewritten as work proceeds (Legislation §3 — `journal.md` is the history; ≤120 lines hard cap).

## Last updated

**2026-07-09** — Human reviewed `docs/length_baseline_results.md` interactively (validity of the length-only baseline, D1 vs D2 mechanisms, whether resampling could fix the confound). Follow-up checks run and verified via `src/spikes/length_confound_followup.py`: D1's length confound is a curation/ascertainment-bias artifact that rebalancing does *not* fix; D2-hIL6's length signal is real biology (survives a clone-disjoint re-split), not split leakage. `docs/phase1_eda_summary.md` updated in 5 places accordingly. See `dax-state/runs/length-baseline-review-2026-07-09.md`.

## Current position

**Phase 1 deliverables:** `rawdata/{ppi,avida,mlaep}/` (gitignored, each with `SOURCE.md`) + `docs/eda-{ppi,avida,mlaep}.md` + `docs/figures/*.png` + `docs/phase1_eda_walkthrough.ipynb` (executed) + `docs/phase1_eda_summary.md`/`.html` (consolidated report, also a Claude Artifact). Not formally closed (no close-out checklist run yet).

**Combined-dataset deliverables:** `rawdata/combined/{d1_ppi,d2_avida,d3_ppi_avida,d4_heldout_mlaep_ace2,d4_heldout_mlaep_antibodies}.csv` (gitignored, `SOURCE.md` present) + `docs/eda-combined.md`/`.html` (also a Claude Artifact). D1=D-SCRIPT PPI (716,517 rows), D2=AVIDa no-COVID (579,471), D3=D1∪D2 training pool (1,295,988). D4 held-out has two axes (ACE2: 19,132 rows; 8-antibody escape panel: 153,056 rows), both verified zero-overlap with D3.

**Length-only baseline (`docs/length_baseline_results.md`):** D1 AUROC 0.652, D2-hIL6 **0.803** (stronger than PPI), D2-hTNFa 0.762 (small n, more variance) — all clear a random floor by a real margin.

**Length-confound follow-up (this session, `dax-state/runs/length-baseline-review-2026-07-09.md`):**
- D1: confound = ascertainment bias (positive-associated proteins longer/higher-degree than negative-only ones); length ⊥ hub-degree (r=-0.066); **rebalancing (random or length-matched) does not remove it** — tested, AUROC unchanged (0.652/0.651/0.653).
- D2-hIL6: confound = real biology (CDR3-length-149 promiscuity, 3,351 distinct clones, 31.8% vs 10.1% population posrate); **confirmed via clone-disjoint re-split** (AUROC 0.809 vs 0.803 original, unchanged) — not split leakage, should not be "corrected."
- Actionable mitigations now in `docs/phase1_eda_summary.md`: §3.1 stratified-reporting requirement (required, not optional), §2.1 dedup requirement (`human_test` 89 exact train-dupes; `ecoli_test` 3,761 within-file dupes), §6 rec #7.

**Recent commits:**
- (pending) — This session's `docs/phase1_eda_summary.md` edits + `src/spikes/length_confound_followup.py` + run-note + journal/handoff sync.
- `2e7ccbe` — Add length-only baseline for D1 (PPI) and D2 (AVIDa).
- `64484a9` — Add docs/eda-combined.html companion report.

## Next action

1. Decide whether D3/D4 become inputs to a PLM fine-tuning run next (with the length-only floor + stratified-reporting requirement as mandatory comparisons), or whether more EDA is wanted first.
2. If/when a modeling phase starts: implement the two dedup steps (`docs/phase1_eda_summary.md` §2.1) in the data loader, and check whether `ecoli_test`'s removed duplicate rows are label-skewed before trusting any cross-species metric.
3. Eventually: Phase 1 close-out checklist (`../dax/phase-lifecycle.md`) — promotion pass (`length_baseline.py` + `length_confound_followup.py` are still `src/spikes/`, study code), phase-summary run-note, `[phase1-done]` commit — still outstanding, deferred while combined-dataset/baseline work was prioritized.

## Open blockers

None.

## DCC state

Not in use for Phase 1 (fetch + EDA + follow-up analysis is CPU/IO-bound; no GPU compute needed). Revisit once a downstream modeling task is scoped.

## WSL / local state

- **Repo:** `/hpc/group/singhlab/user/emt70/rp1_project/dax-gen_project/` on `main`, pushed to `github.com:ethomas4737/dax-gen_project` (origin). Harness at sibling `../dax/` (pinned SHA in `dax-state/pinned-dax-sha.txt`).
- **Pending changes:** this session's doc edits + new spike script + run-note + journal, about to be committed.

## Recovery recipe

`git status` + `tail -10 dax-state/journal.md`.

**Project-specific recovery steps:** none yet — add env activations, checkpoint paths, etc. as the project develops.
