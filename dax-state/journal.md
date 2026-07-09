# Journal

Append-only chronology. One row per event. Write with `Edit` (append) never with `Write` (overwrite).

Event categories: `session` (session-start / -resume / -end), `plan` (plan revision), `step` (step-start / -complete / -blocked), `decision`, `dispatch` (agent call — append cost block at end of summary), `qa` (QA result), `ops` (infra action, e.g., commits, pushes, DCC ops), `promote` (spike→src move), `note` (anything else).

For `dispatch` rows, append a cost block at the end of the summary: `(model=…, tokens=…, tool_uses=…, wall=…s)`.

| Timestamp (ET) | Category | Step | Summary |
|---|---|---|---|
| YYYY-MM-DD — project init | ops | — | Scaffolded `<projname>` from `dax-demo` template. Created standard layout, CLAUDE.md, README, .gitignore, skeleton spec, dax-state seed files. Pinned harness SHA `<sha>`. |
