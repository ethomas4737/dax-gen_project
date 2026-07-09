# Session handoff

**Read this first.** Live cursor of project state. Rewritten as work proceeds (Legislation §3 — `journal.md` is the history; ≤120 lines hard cap).

## Last updated

**YYYY-MM-DD** — Project scaffolded from `dax-demo` template. No spec yet, no phases yet, no DCC project dir yet. The first action is to write the Phase 1 spec.

## Current position

**Phase:** None. Project bootstrapped from `dax-demo`; spec not yet drafted.

**Recent commits:**
- Project init: `<sha>` — copied from `dax-demo` template; renamed; pinned harness SHA refreshed.

## Next action

1. **Write the Phase 1 spec** in `spec/spec.md`. Use the template that's already in the file; replace placeholder content with the real goal, deliverables, acceptance criteria, constraints, and open questions. Dispatch the spec-writer role (`../dax/agent-configs/spec-writer.md`) if scope warrants it; for a small first project the orchestrator can write it inline.
2. **Surface the draft to the human** before going further (Article 1).
3. **Draft `plan-phase1.md`** once the spec is approved.

## Open blockers

None.

## DCC state

| | |
|---|---|
| Mount | `~/dcc/` (check before any DCC work) |
| SSH master | (check on first DCC interaction) |
| Interactive GPU alloc | **None.** This project hasn't started any DCC work yet. |
| DCC project dir | **Not yet created.** Run `CREATENEWPROJECT` (or equivalent) on DCC to set up `~/projects/<projname>/` with the standard `src/`/`qa/`/`spec/`/`data/`/`runs/`/`rawdata/` layout before any sbatch work. |

## WSL state

- **Repo:** `~/work/rohitsinghlab/repos/<projname>/` on `main`. Init commit only.
- **Pending changes:** none.

## Recovery recipe

**WSL.** `git status` + `tail -10 dax-state/journal.md`.

**DCC** (run after >30-min gap or session resume):

```
mount | grep -q "rsingh/dcc"    || mount-dcc
ssh -O check dcc-login 2>&1     || ssh dcc-login true
dcc-gpu-status                  # if no active alloc, surface — do NOT silently reallocate
```

**Project-specific recovery steps:** (add here as the project develops — env activations, checkpoint paths, daemon restarts, etc.)
