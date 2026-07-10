# Session handoff

**Read this first.** Live cursor of project state. Rewritten as work proceeds (Legislation §3 — `journal.md` is the history; ≤120 lines hard cap).

## Last updated

**2026-07-10** — Corrected Phase 2's scope. It's actually a **9-run matrix** (3 models M1/M2/M3 × 3 datasets D1/D2/D3, with D4 held-out for eval on all 9) — this had been discussed in an earlier conversation that never landed in this project's durable state, so it was invisible until the human raised it directly this session. `spec/spec.md` (Revision 2026-07-10b) and `dax-state/plan-phase2.md` have been rewritten to the corrected scope and are **awaiting human approval to execute** past step 0. Also: job 49561386 (the single M1-on-D1 GPU run from earlier this session) failed on its own (dirty-repo guard working as intended, no compute wasted) and needs redoing anyway once D1's curation is extended to all 6 species — the pipeline built so far only covers the human-species subset.

## Current position

**Phase 1** deliverables complete (`rawdata/{ppi,avida,mlaep}/`, `docs/eda-*`, `docs/phase1_eda_summary.md`, D1-D4 combined datasets, length-only baseline + confound follow-up). Not formally closed — no close-out checklist run yet (deferred while Phase 2 work was prioritized).

**Phase 2** (`dax-state/plan-phase2.md`) — 13-row plan (steps 0-10, with 8/9 split into a/b). All 5 open decisions **resolved** 2026-07-10. **Near-term scope narrowed 2026-07-10:** human is weighing alternatives to D2 and doesn't want D2/D3 work started — focus is the 3 D1-only runs (M1/M2/M3 × D1) first; steps 2, 3, 8b, 9b are **deferred**, not cancelled.
- Step 0 (M1 pipeline scaffold + CPU smoke test, human-species D1 subset only): **done**, but superseded — real D1 curation (step 1) needs all 6 species.
- Steps 1, 4, 5, 6, 7, 8a, 9a, 10 (D1 full-species curation → M2 attention-pooling → M3 LoRA-wrapped backbone → train_frozen.py/train_lora.py → D4 held-out harness → 3 D1 training runs → D4 eval on those 3 → eval report): **not started**, unblocked, ready to execute pending final go-ahead.
- Steps 2, 3, 8b, 9b (D2/D3 curation + the 6 D2/D3 training runs + their D4 eval): **deferred**.

## Next action

1. **Human go-ahead needed** to start executing steps 1/4/5 (can run in parallel — no interdependency between D1 curation, M2, and M3 builds).
2. Build order for the D1-only near-term scope: step 1 (D1 full-species curation) + step 4 (M2) + step 5 (M3, incl. a quick `peft`-vs-ESM-C compatibility check) in parallel → step 6 (train_frozen.py/train_lora.py) → step 7 (D4 harness) → step 8a (3 GPU training runs, human approval needed per allocation) → step 9a (D4 eval) → step 10 (D1-only eval report).
3. Independent QA-executor pass on step 0/1's dedup+filter logic is still outstanding regardless of sequencing.
4. D2/D3 work (steps 2, 3, 8b, 9b) resumes once the D2 dataset question is settled — no action needed there for now.
5. Eventually: Phase 1 close-out checklist (`../dax/phase-lifecycle.md`) — still outstanding, deferred.

## Open blockers

- Phase 2 needs a final human go-ahead to start executing (Article 1) — see Next action #1.
- D2/D3 portions (steps 2, 3, 8b, 9b) on hold pending the human's D2-alternatives decision (not currently being worked).

## DCC state

No GPU allocation currently held. Job 49561386 (single M1-on-D1 run, human-species-only D1) FAILED by design (dirty-repo guard) and is superseded by the corrected plan above — do not resubmit it as-is. Currently on a CPU-only `sys/dashboard` job (`common` partition) coordinating this work.

## WSL / local state

- **Repo:** `/hpc/group/singhlab/user/emt70/rp1_project/dax-gen_project/` on `main`, pushed to `github.com:ethomas4737/dax-gen_project` (origin). Harness at sibling `../dax/` (pinned SHA in `dax-state/pinned-dax-sha.txt`).
- **This session's commit:** `[phase2-open]` — spec revision, plan-phase2.md, journal/decisions backfill, session-handoff rewrite, stray-file cleanup.

## Recovery recipe

`git status` + `tail -15 dax-state/journal.md` + read `dax-state/plan-phase2.md`.

**Project-specific recovery steps:** before touching `src/spikes/phase2/run_full_m1_d1.sbatch`, review it — it was drafted before this session's formalization pass and its contents haven't been checked against the plan above.
