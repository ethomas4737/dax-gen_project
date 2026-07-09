# dax-demo — Claude Code Instructions

This is a DAX project repo (skeleton template). The DAX harness lives at `../dax/`.

> **Template note.** When you copy this repo into a real project (`cp -r dax-demo dax-<your-project>`), update: project name throughout this file; project name in `README.md`; spec content in `spec/spec.md`; the placeholder rows in `dax-state/journal.md` and `dax-state/session-handoff.md`; and refresh `dax-state/pinned-dax-sha.txt` to the current `../dax/` HEAD. See `docs/walkthrough.md` for the full bootstrap sequence.

## At session start

1. Verify `../dax/MANIFESTO.md` exists. If missing, STOP and report to the user — DAX guidance cannot be loaded.
2. Read `../dax/MANIFESTO.md` (governing document; Constitution Articles 1–9 + Legislation §1–6).
3. Read `../dax/user-guidance/` (global preferences).
4. Read `./user-guidance/` (project-specific preferences).
5. Read `./dax-state/session-handoff.md` — live state: current step, DCC status, open blockers, reconnection recipe (≤120 lines per Legislation §3).
6. Read `./spec/spec.md`'s `## Current state` front-matter (cheap; full file only if needed). Read the active phase plan's `## Current state` front-matter (cheap; full file only if a phase is open). Read the most recent ~20 rows of `./dax-state/journal.md`.

Before acting in a role, read `../dax/agent-configs/<role>.md`.

Cross-cutting harness conventions referenced from this repo:
- `../dax/phase-lifecycle.md` — open / during / close protocol per phase (Legislation §6).
- `../dax/agent-configs/run-note-template.md` — required structure for `dax-state/runs/<step>.md` files.
- `../dax/agent-configs/promotion-rules.md` — spike → src promotion criteria (study/working × one-shot/reusable).

## Folder structure

- `spec/` — Goals, deliverables, acceptance criteria
- `src/` — Working code; `src/spikes/` for study / exploratory code
- `qa/` — Tests and validation
- `data/`, `runs/`, `rawdata/` — **Not tracked.** Environment-local. On DCC these are symlinks into `/hpc/group/singhlab/`.
- `reading/`, `docs/`, `logs/`
- `dax-state/` — Live plans, journal, decisions, QA results. See `dax-state/README.md` for the index.
- `user-guidance/` — Project-specific preferences.

## Rules

- Tag generated code as study (`src/spikes/`) or working (`src/`).
- Never modify `data/raw/` after the initial download (DCC-side; convention, not permission).
- When in doubt about scope, ask. Article 1 (human sovereignty) applies.

## Operational protocol for executing steps

Each numbered plan step follows this lifecycle (mirror of `../dax/phase-lifecycle.md` "During a phase"):

**Before start.**
1. Read `../dax/agent-configs/<role>.md` for the role you'll dispatch.
2. Mark the step's Status cell in the active plan as `in progress`.
3. If the step runs on DCC **and** the last DCC interaction was > 30 min ago, run the DCC preflight (below) before dispatching.

**During.**
- Log every subagent dispatch as a single row in `dax-state/journal.md` with `category=dispatch` and an inline cost block at end of summary: `(model=…, tokens=…, tool_uses=…, wall=…s)`. There is no separate `agent-usage-log.md`.
- Log any autonomous decision to `dax-state/decisions.md`.
- Run-notes per step at `dax-state/runs/<step>.md` follow `../dax/agent-configs/run-note-template.md`. Soft cap 200 lines per stage.

**On completion (or block).**
1. Update Status + Outcome cells in the active plan (Outcome ≤80 chars: `done|blocked|partial` + run-note link).
2. Append one row to `dax-state/journal.md`.
3. Rewrite the relevant section(s) of `dax-state/session-handoff.md` if affected. Keep ≤120 lines (Legislation §3).
4. Commit with subject `[<step-id>] <short action>` and a body that references produced artifacts and QA outcome. Push when sensible.

**If blocked.**
- Set Status = `blocked`; Outcome = `blocked — <one-line reason>`.
- Record the blocker in `session-handoff.md` under "Open blockers".
- Surface to the human. Do not silently absorb scope changes (Manifesto Article 1).

## Relevant skills

The following Claude Code skills are commonly invoked from a DAX project. See `docs/walkthrough.md` § Skill ecosystem for when each applies:

- **`rohit-dax-session`** — orchestrator boot at session start.
- **`rohit-dcc-workflow`** — WSL-side DCC operations via the `dcc`/`dcc-gpu` wrappers and SSHFS mount at `~/dcc/`.
- **`rohit-dcc-onnode`** — DCC operations from the cluster itself (login or compute node).
- **`rohit-precise-workflow`** — PRECISE virtual-screening + Uni-Dock pipeline (for projects that use PRECISE).

## DCC preflight

Before any `dcc` / `dcc-gpu` call that follows a > 30-min gap, or on session resume:

```
mount | grep -q "rsingh/dcc"    || mount-dcc
ssh -O check dcc-login 2>&1     || ssh dcc-login true
dcc-gpu-status                  # must show a running job; otherwise STOP and ask human
```

If the GPU allocation is gone, do not silently reallocate — surface to the human (DCC-workflow skill rule 5).

## Provenance

`dax-state/pinned-dax-sha.txt` records the DAX harness SHA at project init. Projects pull the latest harness conventions by default; the pinned SHA lets you reconstruct exact harness state if reproducibility requires it.
