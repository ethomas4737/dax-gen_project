# Session handoff

**Read this first.** Live cursor of project state. Rewritten as work proceeds (Legislation §3 — `journal.md` is the history; ≤120 lines hard cap).

## Last updated

**2026-07-10, ~13:20** — Full rewrite (prior version was stale by ~3h: steps 1/4/5/6 had completed and gone uncaptured). Since the last handoff: implemented M2/M3/train_frozen.py/train_lora.py/evaluate.py (steps 1,4,5,6); human then decided (a) cross-species PPI is internal-eval-only, never trained on, (b) validation monitoring during training must come from a fresh 90/10-stratified split carved out of `human_train` (not `human_test`), (c) **D4 (RBD-ACE2 + antibody escape) is the headline/primary metric**, not a secondary check. This reopened steps 1 (new step 1c) and 6. An executor is currently implementing both, mid-flight (not yet committed). Also verified D4 needs no further data cleaning (0 dupes, 0 non-standard residues, 0 nulls on both axes) — one real, already-documented caveat stands: ACE2's 805aa sequence is 5aa past D1's 800aa training-length cap (`docs/eda-combined.md`), a compatibility point for step 7's eval harness, not a cleaning issue.

## Current position

**Phase 1** deliverables complete. Not formally closed — close-out checklist still deferred.

**Phase 2** (`dax-state/plan-phase2.md`) — D4 is now the framing objective; D1 training + cross-species eval exist in service of it.
- Steps 0, 1, 4, 5: **done**.
- Step 1b (cross-species PPI as internal held-out eval, confirmed non-training): **not started**.
- Step 1c (carve 90/10 stratified val split from `human_train`) + step 6 (reopened — add real per-epoch val-loss/AUROC monitoring to `train_frozen.py`/`train_lora.py`): **in progress**, executor dispatched this session, currently running a CPU smoke-test job (`49568082 phase2-smoke6`) validating all 6 train+eval combinations against the new split. Uncommitted diff touches `data_prep.py`, `evaluate.py`, `model.py`, `train_frozen.py`, `train_lora.py`, `plan-phase2.md`, + new `make_synthetic_short_seqs.py`.
- Steps 7 (D4 eval harness), 8a (3 D1-only GPU runs), 9a, 10: **not started**.
- Steps 2, 3, 8b, 9b (D2/D3): **deferred**, not cancelled.

## Next action

1. **Wait for the in-flight executor** (steps 1c/6) to finish, smoke-pass, and commit. Check `git log` / `squeue -u $USER` for job `49568082` completion.
2. Once landed: step 1b (cross-species curation) and step 7 (D4 eval harness — data already confirmed clean) are both unblocked and parallelizable.
3. Step 8a (3 GPU training runs) still needs explicit human approval before each allocation request.
4. Step 1-qa (independent QA on step 0/1's dedup+filter logic) remains outstanding, unscheduled.
5. D2/D3 (steps 2, 3, 8b, 9b) resume once the human's D2-alternatives decision lands — no action needed now.
6. Eventually: Phase 1 close-out checklist — still outstanding, deferred.

## Open blockers

- Step 8a needs human approval before each GPU allocation request.
- D2/D3 portions on hold pending the human's D2-alternatives decision.
- Step 7 (when built) must confirm the eval harness doesn't silently mishandle ACE2's 805aa sequence (5aa past D1's 800aa training cap).

## DCC state

No GPU allocation held. Two CPU jobs running (`common` partition): `49561144` (`sys/dashboard`, ~3.5h in, coordinating this session) and `49568082` (`phase2-smoke6`, started 13:15, 30-min budget, validating the executor's steps 1c/6 work).

## WSL / local state

- **Repo:** `/hpc/group/singhlab/user/emt70/rp1_project/dax-gen_project/` on `main`, on-cluster (this session runs directly on DCC, node `dcc-core-ferc-u-ab39-5-4`). Origin: `github.com:ethomas4737/dax-gen_project`.
- **4 commits ahead of `origin/main`**, not pushed: `[phase2-rescope]`, `[phase2-decisions]` (5 open decisions), `[phase2-narrow]`, `[phase2-1-4]`, `[phase2-5]`, `[phase2-6]` ×2, `[phase2-decisions]` (val-split/D4-objective). *(exact list: `git log --oneline -8`)*
- **Uncommitted right now:** the in-flight executor's steps 1c/6 diff (see Current position) — do not assume `plan-phase2.md`'s on-disk state matches its last-committed version until that lands.

## Recovery recipe

```
git status --short --branch
git log --oneline -8
squeue -u $USER                      # check job 49568082 (smoke test) status
tail -15 dax-state/journal.md
```

Read `dax-state/plan-phase2.md` steps 1c/6 rows once the executor's commit lands, and `dax-state/decisions.md`'s 2026-07-10 val-split entry for full rationale before touching training scripts.
