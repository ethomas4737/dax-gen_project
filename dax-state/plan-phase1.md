# Phase 1 plan — &lt;short phase name&gt;

## Current state
**Last updated:** YYYY-MM-DD
**Load-bearing as of this date:** (placeholder — phase not yet open)
**What's new since last update:** Template only.

<!--
This file is a template. The orchestrator (or the architect, dispatched by the orchestrator)
writes the real plan once `spec/spec.md` is finalized for Phase 1.

The step table below shows the canonical schema:
  - Notes column ≤200 chars (plan-time guidance only; not execution narrative)
  - Outcome column ≤80 chars (`done|blocked|partial` + run-note link)
Plan-time guidance goes in Notes. Execution narrative goes in `dax-state/runs/<step>.md`.
See `../dax/phase-lifecycle.md` for phase open/during/close protocol.
-->

Active execution plan for Phase 1. Step IDs map to spec deliverables; sub-steps decompose where it helps separation of concerns or independent QA. Status defaults to `not started`; update on step start/complete per the operational protocol in `CLAUDE.md`.

| Step ID | Status | Description | Inputs | Outputs | Role | Deps | Notes (plan-time, ≤200 chars) | Outcome (≤80 chars) |
|---|---|---|---|---|---|---|---|---|
| 0 | not started | &lt;DCC bringup / repo sync / env verify&gt; | | | executor | — | | |
| 1 | not started | &lt;first deliverable&gt; | | | executor | 0 | | |
| 1-qa | not started | QA for step 1 | | | qa-executor | 1 | | |

After all step-QA passes for a step group: promote the spike script(s) from `src/spikes/` to `src/` per `../dax/agent-configs/promotion-rules.md`, append journal rows, update `session-handoff.md`, commit per `[<step-id>] <short action>`.
