# Journal

Append-only chronology. One row per event. Write with `Edit` (append) never with `Write` (overwrite).

Event categories: `session` (session-start / -resume / -end), `plan` (plan revision), `step` (step-start / -complete / -blocked), `decision`, `dispatch` (agent call — append cost block at end of summary), `qa` (QA result), `ops` (infra action, e.g., commits, pushes, DCC ops), `promote` (spike→src move), `note` (anything else).

For `dispatch` rows, append a cost block at the end of the summary: `(model=…, tokens=…, tool_uses=…, wall=…s)`.

| Timestamp (ET) | Category | Step | Summary |
|---|---|---|---|
| 2026-07-09 | ops | — | Scaffolded `dax-gen_project` from `dax-demo` template (moved template content up one level, dropped redundant nested harness/tools clones, fresh git init). Pinned harness SHA `f29e04997e9e310fd0cf26e330cc87f4d8e08845`. |
| 2026-07-09 | note | — | Drafted Phase 1 spec: curate D-SCRIPT PPI, AVIDa-hIL6+hTNFa antibody, and MLAEP viral-evolution datasets separately; produce EDA per dataset. Downstream modeling task deliberately deferred. |
| 2026-07-09 | note | — | Verified D-SCRIPT human PPI pairs (15,816 unique proteins) via mygene.info: 0 COVID/coronavirus hits; 1 non-functional IGHV pseudogene entry (33/474,517 pairs, all negative labels) — kept, per human decision. |
| 2026-07-09 | ops | — | Updated README.md + CLAUDE.md for the real project name/goal; renamed `docs/walkthrough.md` → `docs/dax-demo-walkthrough.md`; refreshed dax-state placeholders. |
