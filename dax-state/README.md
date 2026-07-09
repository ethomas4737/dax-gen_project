# Dax State

Working memory for this project: plans, decisions, QA results, cost logs, and agent traces. The project's audit trail.

## Index

| File | Purpose | Lifecycle |
|---|---|---|
| `session-handoff.md` | Live "read me first" on session resume. Current position, DCC state, open blockers, recovery recipe. | **Overwritten** as state changes. ≤120 lines hard cap (Legislation §3). |
| `journal.md` | Append-only chronology. One row per event (`session`, `plan`, `step`, `decision`, `dispatch`, `qa`, `ops`, `promote`, `note`). For `dispatch`, append cost block to summary. | **Append only.** |
| `decisions.md` | Material autonomous decisions and their rationale. | **Append only.** Phase-end appends a load-bearing index. |
| `architecture-phase{N}.md` | Per-phase architectural decisions when warranted (>5 plan rows OR new tools). | **Append only at section granularity.** |
| `plan-phase{N}.md` | Per-phase step table. Notes col ≤200 chars; Outcome col ≤80 chars + run-note link. | Status cells updated as steps progress; otherwise stable. |
| `runs/<step>.md` | Per-step run-notes per `../dax/agent-configs/run-note-template.md`. Soft cap 200 lines/stage. | **Append-by-section** within a stage. |
| `qa/<step>.md` | QA pass/fail per step. | **Append only.** |
| `pinned-dax-sha.txt` | SHA of `../dax/` harness at project init. For reproducibility. | Written once. |

A phase plan (e.g. `plan-phase1.md`) is added by the architect/orchestrator once the spec is fleshed out. See `../dax/phase-lifecycle.md` for phase open/during/close protocol.

## Reading order on session resume

1. `session-handoff.md` — orient.
2. Last 20 rows of `journal.md` — recent history.
3. Active phase plan — current step + next steps.
4. `decisions.md` — only if session-handoff references an open decision.

## Update discipline

Every plan step ends with (in this order):

1. Update the active plan's Status + Outcome cells.
2. Append one row to `journal.md`. If a subagent was dispatched, append a cost block to the summary inline: `(model=…, tokens=…, tool_uses=…, wall=…s)`.
3. If an autonomous decision was made → append to `decisions.md`.
4. Rewrite the relevant section(s) of `session-handoff.md` as needed; keep ≤120 lines.
5. Git commit with subject `[<step-id>] <short action>`.

See `../CLAUDE.md` "Operational protocol for executing steps" for the full per-step lifecycle, and `../dax/phase-lifecycle.md` for the phase-level open/close protocol.
