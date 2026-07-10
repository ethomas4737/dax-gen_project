# Session handoff

**Read this first.** Live cursor of project state. Rewritten as work proceeds (Legislation §3 — `journal.md` is the history; ≤120 lines hard cap).

## Last updated

**2026-07-10** — Formalized Phase 2 opening. A prior session had already built and CPU-smoke-tested a full M1-on-D1 pipeline (`src/spikes/phase2/`) without going through the phase-open protocol (no spec section, no plan, uncommitted). This session backfilled `spec/spec.md` (Revision 2026-07-10), created `dax-state/plan-phase2.md`, backfilled `journal.md` + `decisions.md`, removed a stray empty file (`src/spikes/phase2/untitled.py`), and committed.

## Current position

**Phase 1** deliverables complete (`rawdata/{ppi,avida,mlaep}/`, `docs/eda-*`, `docs/phase1_eda_summary.md`, D1-D4 combined datasets, length-only baseline + confound follow-up). Not formally closed — no close-out checklist run yet (deferred while Phase 2 work was prioritized).

**Phase 2** (`dax-state/plan-phase2.md`) now open. Goal: first PLM baseline model ("M1" = frozen ESM-C 300M + MLP head) on D1, compared against the 0.652 AUROC length-only floor.
- Step 1 (pipeline build + CPU smoke test): **done**. `src/spikes/phase2/{data_prep,model,train_m1,evaluate}.py`; curated D1 = 419,916 train / 52,424 test rows (dedup + bad-residue filtered); smoke run passed end-to-end. See `dax-state/runs/phase2-m1-d1-pipeline.md`.
- Step 1-qa: **partial** — self-verified in the run-note (independent re-derivation of key counts), no separate qa-executor dispatch yet.
- Step 2 (real GPU training run, full curated D1): **not started** — blocked on human approval to request a GPU allocation.
- Step 3 (evaluation report, length-stratified): **not started**.

## Next action

1. **Human decision needed:** approve requesting a GPU allocation for Phase 2 step 2 (`singhlab-gpu`, 1x A6000, est. ~15-30 min compute / 1hr walltime ask — see resource estimate in `dax-state/runs/phase2-m1-d1-pipeline.md`).
2. Once approved: submit the real M1-on-D1 training run via `sbatch` (there's already a draft `src/spikes/phase2/run_full_m1_d1.sbatch` — review before submitting, it predates this formalization pass and hasn't been checked this session).
3. After training: build the evaluation report (step 3) — aggregate AUROC/AUPRC + length-decile-stratified table vs. the length-only baseline, per `docs/phase1_eda_summary.md` §3.1.
4. Independent QA-executor pass on step 1 (currently only self-verified) — can happen in parallel with step 2.
5. Eventually: Phase 1 close-out checklist (`../dax/phase-lifecycle.md`) — still outstanding, deferred.

## Open blockers

- Phase 2 step 2 needs human approval before a GPU allocation is requested (see Next action #1).

## DCC state

**Job 49561386** — real M1-on-D1 training run, `singhlab-gpu` (1x A6000), submitted 2026-07-10, 1hr walltime cap (est. actual ~15-30 min). Output: `runs/phase2_m1_d1/full/slurm-49561386.out`. Check with `squeue -j 49561386` or `sacct -j 49561386 -o JobID,State,Elapsed,MaxRSS,ExitCode`. Separately: a CPU-only `sys/dashboard` job (`common` partition) is the interactive session this work is being coordinated from.

## WSL / local state

- **Repo:** `/hpc/group/singhlab/user/emt70/rp1_project/dax-gen_project/` on `main`, pushed to `github.com:ethomas4737/dax-gen_project` (origin). Harness at sibling `../dax/` (pinned SHA in `dax-state/pinned-dax-sha.txt`).
- **This session's commit:** `[phase2-open]` — spec revision, plan-phase2.md, journal/decisions backfill, session-handoff rewrite, stray-file cleanup.

## Recovery recipe

`git status` + `tail -15 dax-state/journal.md` + read `dax-state/plan-phase2.md`.

**Project-specific recovery steps:** before touching `src/spikes/phase2/run_full_m1_d1.sbatch`, review it — it was drafted before this session's formalization pass and its contents haven't been checked against the plan above.
