# Session handoff

**Read this first.** Live cursor of project state. Rewritten as work proceeds (Legislation §3 — `journal.md` is the history; ≤120 lines hard cap).

## Last updated

**2026-07-10** — Corrected Phase 2's scope. It's actually a **9-run matrix** (3 models M1/M2/M3 × 3 datasets D1/D2/D3, with D4 held-out for eval on all 9) — this had been discussed in an earlier conversation that never landed in this project's durable state, so it was invisible until the human raised it directly this session. `spec/spec.md` (Revision 2026-07-10b) and `dax-state/plan-phase2.md` have been rewritten to the corrected scope and are **awaiting human approval to execute** past step 0. Also: job 49561386 (the single M1-on-D1 GPU run from earlier this session) failed on its own (dirty-repo guard working as intended, no compute wasted) and needs redoing anyway once D1's curation is extended to all 6 species — the pipeline built so far only covers the human-species subset.

## Current position

**Phase 1** deliverables complete (`rawdata/{ppi,avida,mlaep}/`, `docs/eda-*`, `docs/phase1_eda_summary.md`, D1-D4 combined datasets, length-only baseline + confound follow-up). Not formally closed — no close-out checklist run yet (deferred while Phase 2 work was prioritized).

**Phase 2** (`dax-state/plan-phase2.md`) — 11-step plan (steps 0-10), **plan presented, not yet approved to execute**. Only step 0 is done:
- Step 0 (M1 pipeline scaffold + CPU smoke test, human-species D1 subset only): **done**, but superseded — real D1 curation (step 1) needs all 6 species.
- Steps 1-10 (multi-species D1 curation, D2/D3 curated splits, M2 attention-pooling, M3 LoRA-wrapped backbone, generalized train/eval scripts, D4 held-out harness, 9 training runs, 9 D4 evals, consolidated report): **not started**.
- **5 open decisions block specific steps** — see `dax-state/plan-phase2.md` "Open decisions" section (D1 concatenation approach, D2 split methodology, D3 split assumption, M3's LoRA approach + resource estimate, how much M1/M2 vs. M3 training code to share).

## Next action

1. **Human decision needed:** approve the rewritten `plan-phase2.md` (or redirect it) before any execution starts — this is a much larger scope than the single M1-on-D1 run this session began with.
2. Resolve the 5 open decisions listed in `plan-phase2.md`, at least for whichever steps get tackled first.
3. Once approved: likely build order is step 1 (D1 full-species curation) → step 4 (M2, independent, can parallelize) → steps 2-3 (D2/D3 splits) → step 5-6 (M3 + generalized scripts) → step 7 (D4 harness) → steps 8-10 (run + eval + report). Not yet confirmed with the human.
4. Independent QA-executor pass on step 0/1's dedup+filter logic is still outstanding regardless of sequencing.
5. Eventually: Phase 1 close-out checklist (`../dax/phase-lifecycle.md`) — still outstanding, deferred.

## Open blockers

- Phase 2's rewritten plan needs human approval before execution (Article 1) — see Next action #1.
- 5 open decisions in `plan-phase2.md` block their respective steps.

## DCC state

No GPU allocation currently held. Job 49561386 (single M1-on-D1 run, human-species-only D1) FAILED by design (dirty-repo guard) and is superseded by the corrected plan above — do not resubmit it as-is. Currently on a CPU-only `sys/dashboard` job (`common` partition) coordinating this work.

## WSL / local state

- **Repo:** `/hpc/group/singhlab/user/emt70/rp1_project/dax-gen_project/` on `main`, pushed to `github.com:ethomas4737/dax-gen_project` (origin). Harness at sibling `../dax/` (pinned SHA in `dax-state/pinned-dax-sha.txt`).
- **This session's commit:** `[phase2-open]` — spec revision, plan-phase2.md, journal/decisions backfill, session-handoff rewrite, stray-file cleanup.

## Recovery recipe

`git status` + `tail -15 dax-state/journal.md` + read `dax-state/plan-phase2.md`.

**Project-specific recovery steps:** before touching `src/spikes/phase2/run_full_m1_d1.sbatch`, review it — it was drafted before this session's formalization pass and its contents haven't been checked against the plan above.
