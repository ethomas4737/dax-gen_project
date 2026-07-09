# &lt;project-name&gt;: &lt;one-line project description&gt;

## Current state
**Last updated:** YYYY-MM-DD
**Load-bearing as of this date:** (placeholder — spec not yet written)
**What's new since last update:** Initial template; no Phase 1 content yet.

## Goal

&lt;What this project exists to do. 2–5 sentences. Should be specific enough that an outsider can tell whether a candidate result satisfies it.&gt;

## Background

&lt;Why this matters; what's already been tried; relevant context. Cite collaborator inputs, prior papers, lab tools. Be concrete — vague background is worse than no background.&gt;

## Data sources

&lt;Tables of input data: file, organism, conditions, role in the project. Note canonical-source paths and any in-repo copies. Specify ownership / read-only conventions.&gt;

| File | Origin | Role |
|---|---|---|
| &lt;path&gt; | &lt;collaborator / public DB / lab archive&gt; | &lt;primary input / reference / negative control&gt; |

## Phase 1 deliverables

1. **Step 1 — &lt;name&gt;.** &lt;What's produced and from what.&gt;
2. **Step 2 — &lt;name&gt;.** &lt;...&gt;

(Subsequent steps as needed.)

## Phase 1 acceptance criteria

- **Step 1:** &lt;what counts as "done" for this step — file existence, parse checks, numeric thresholds, etc. Be testable, not aspirational.&gt;
- **Step 2:** &lt;...&gt;
- **All steps:** code lives in `src/spikes/` first, promoted to `src/` only after the step's QA passes. Each step's outputs are linked from `dax-state/journal.md`.

## Constraints / environment

- &lt;Compute / env constraints: DCC GPU partition, specific conda env, library versions.&gt;
- &lt;Data-handling constraints: no modification of `data/raw/` after initial drop; no writes to shared / read-only resources.&gt;
- Tag generated code as study (`src/spikes/`) or working (`src/`) per Manifesto Article 6.
- Provenance per Articles 5–6: every artifact records inputs, command lines, and the tool commit it was produced under.

## Deferred (Phase 2+)

- &lt;Things scoped out of Phase 1 that are likely Phase 2.&gt;
- &lt;Open scientific questions whose answer isn't needed yet.&gt;

## Open questions

- &lt;Questions for the human to resolve before / during Phase 1. Number them; resolve via comment edit (not delete).&gt;

---

<!--
Spec-writing notes (per `../dax/agent-configs/spec-writer.md` + Legislation §3):

- spec/spec.md is append-only at section granularity. Revisions go as
  "## Revision YYYY-MM-DD — <reason>" sections appended at the bottom.
  Don't rewrite prior content — it's the audit trail of how scope evolved.
- Keep the spec ≤1 page per phase; once it exceeds ~200 lines or 3 phases,
  modularize: spec/master.md becomes a 1-page index; spec/phase{N}.md per-phase files.
- Update the `## Current state` front-matter at the top whenever a revision lands.
-->
