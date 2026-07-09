# Session handoff

**Read this first.** Live cursor of project state. Rewritten as work proceeds (Legislation §3 — `journal.md` is the history; ≤120 lines hard cap).

## Last updated

**2026-07-09** — Bootstrapped from `dax-demo` template. Phase 1 spec drafted and approved (three-dataset curation + EDA). README/CLAUDE.md updated for the real project. No phase opened yet.

## Current position

**Phase:** None open yet. Spec is drafted: curate D-SCRIPT PPI data (excl. COVID/antibody), AVIDa-hIL6 + AVIDa-hTNFa antibody data (excl. SARS-CoV-2), and MLAEP repo-included preprocessed data — kept separate, not merged — then produce EDA per dataset. See `spec/spec.md`.

**Verified so far:** D-SCRIPT human PPI pairs independently checked via mygene.info — 0 COVID hits, 1 negligible non-functional IGHV pseudogene entry (kept, per human decision).

**Recent commits:**
- `6c510bd` — Bootstrap: spec, README/CLAUDE.md, dax-state rewrite for 3-dataset curation + EDA.
- `ef7a509` — init from dax-demo template.

## Next action

1. **Draft `plan-phase1.md`** from the approved spec (4 steps: fetch+curate D-SCRIPT, fetch+curate AVIDa, fetch+curate MLAEP, per-dataset EDA).
2. **Surface the plan to the human** before executing (Article 1).
3. Dispatch `executor` per step once approved.

## Open blockers

None.

## DCC state

Not in use for Phase 1 (fetch + EDA is CPU/IO-bound; no GPU compute needed). Revisit once a downstream modeling task is scoped in a later phase.

## WSL / local state

- **Repo:** `/hpc/group/singhlab/user/emt70/rp1_project/dax-gen_project/` on `main`, pushed to `github.com:ethomas4737/dax-gen_project` (origin). Reinitialized fresh (not carrying `dax-demo`'s git history). Harness at sibling `../dax/` (pinned SHA in `dax-state/pinned-dax-sha.txt`).
- **Pending changes:** none (bootstrap rewrites committed at `6c510bd`).

## Recovery recipe

`git status` + `tail -10 dax-state/journal.md`.

**Project-specific recovery steps:** none yet — add env activations, checkpoint paths, etc. as the project develops.
