# Session handoff

**Read this first.** Live cursor of project state. Rewritten as work proceeds (Legislation §3 — `journal.md` is the history; ≤120 lines hard cap).

## Last updated

**2026-07-09** — All Phase 1 steps (0 through 4-qa) done: 3 datasets fetched/curated into `rawdata/` and EDA reports generated + independently QA'd. Phase not formally closed yet (no close-out checklist run, no human sign-off on findings).

## Current position

**Phase:** Phase 1 plan fully executed (`dax-state/plan-phase1.md`, all rows `done`). Deliverables: `rawdata/{ppi,avida,mlaep}/` (gitignored, each with `SOURCE.md`) + `docs/eda-{ppi,avida,mlaep}.md` + `docs/figures/*.png` (10 figures) + `docs/phase1_eda_walkthrough.ipynb` (executed notebook, incl. PLM-readiness section) + `docs/phase1_eda_summary.md` (consolidated cross-dataset report with recommendations). Scripts in `src/spikes/eda_{ppi,avida,mlaep}.py` (not promoted — hardcoded paths/dates, promotion deferred to phase close).

**Key EDA findings:** PPI positive fraction fixed at ~9.09% (1:10 sampling) across all species; AVIDa hIL6 3.66% / hTNFa 12.22% positive; MLAEP ACE2-bind 8.05% + 8 per-antibody-clone escape fractions (4.1–18.2%). **PLM-readiness (human plans to use a PLM downstream):** (1) **100% of PPI's `human_test` proteins already appear in `human_train`** (by ID and exact sequence) — verified fact, but framing corrected after human pushback: this is very likely an intentional pair-level/interactome-completion split (D-SCRIPT's real generalization claim is cross-species transfer via mouse/fly/yeast/worm/ecoli), not a benchmark flaw. Only matters if downstream work needs a novel-*human*-protein-specific generalization claim, which would need a custom protein-disjoint split; (2) PPI positive fraction is confounded with pair length (0.165 shortest decile vs ~0.07-0.08 mid-range vs 0.103 longest); (3) all sequences within PLM context limits; (4) PPI has `U`/`X` residues in ~0.1-0.3% of seqs. Full findings in `dax-state/runs/phase1-{1,2,3,4,notebook}.md` and `docs/phase1_eda_summary.md`.

**Recent commits:**
- (pending) — Correct train/test overlap framing per human pushback.
- `4175dbc` — Add train/test identity-leakage check for PPI.

## Next action

1. **Human review** of the 3 EDA reports (`docs/eda-*.md`) and findings.
2. If satisfied: run the Phase 1 **close-out checklist** (`../dax/phase-lifecycle.md`) — promotion pass, phase-summary run-note, decisions/session-handoff rewrite, `[phase1-done]` commit.
3. Then scope the downstream modeling task (deferred in spec) and open Phase 2.

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
