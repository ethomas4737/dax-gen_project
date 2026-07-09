# Session handoff

**Read this first.** Live cursor of project state. Rewritten as work proceeds (Legislation §3 — `journal.md` is the history; ≤120 lines hard cap).

## Last updated

**2026-07-09** — Phase 1 (curate 3 datasets + EDA) fully executed, not yet formally closed. On top of that, human pulled forward the previously-deferred dataset-merging item: built + EDA'd 4 combined variants (D1-D4). See `spec/spec.md` "Revision 2026-07-09".

## Current position

**Phase 1 deliverables:** `rawdata/{ppi,avida,mlaep}/` (gitignored, each with `SOURCE.md`) + `docs/eda-{ppi,avida,mlaep}.md` + `docs/figures/*.png` + `docs/phase1_eda_walkthrough.ipynb` (executed) + `docs/phase1_eda_summary.md`/`.html` (consolidated report, also a Claude Artifact). Not formally closed (no close-out checklist run yet).

**Combined-dataset deliverables (new):** `rawdata/combined/{d1_ppi,d2_avida,d3_ppi_avida,d4_heldout_mlaep_ace2}.csv` (gitignored, `SOURCE.md` present) + `docs/eda-combined.md`. D1=D-SCRIPT PPI (716,517 rows), D2=AVIDa no-COVID (579,471), D3=D1∪D2 training pool (1,295,988), D4-heldout=MLAEP reframed as (RBD_mutant, human_ACE2, ace2_bind) (19,132), kept separate from D3 by design (held-out eval, not merged into training). Built by `src/spikes/build_combined_datasets.py` + `eda_combined.py`.

**Key findings (Phase 1):** PPI positive fraction fixed ~9.09% (1:10 sampling); AVIDa hIL6 3.66%/hTNFa 12.22%; MLAEP ACE2-bind 8.05%. PLM-readiness: PPI human train/test shares 100% of proteins (pair-level split by design, not a flaw — see corrected framing in journal); PPI positive fraction confounded with pair length (remediation steps in `docs/phase1_eda_summary.md` §3.1); all seqs within PLM context limits; PPI has U/X in ~0.1-0.3% of seqs.

**Key findings (combined D1-D4):** D4's held-out set is verified genuinely clean — zero sequence overlap with the D3 training pool in either direction. 1 sequence (human TNF-alpha) shared between D1/D2 (not a leakage concern). D4 held-out has zero length variance (RBD mutants constant 201aa, ACE2 constant 805aa — 5aa past D1's 800aa training cap). `seq_a`/`seq_b` column semantics differ by `pair_type` in D3 (symmetric in PPI rows, asymmetric antibody/antigen in AVIDa rows) — worth an explicit role column if the downstream architecture needs it. Full detail in `dax-state/runs/combined-datasets-2026-07-09.md` and `docs/eda-combined.md`.

**Recent commits:**
- (pending) — Build D1-D4 combined datasets + EDA.
- `721abcf` — Add §3.1 length-confound remediation steps + docs/phase1_eda_summary.html report.

## Next action

1. **Human review** of `docs/eda-combined.md` and the combined-dataset design (esp. the `seq_a`/`seq_b` role-asymmetry note).
2. Decide whether D3/D4 are inputs to an actual PLM fine-tuning run next, or whether more EDA/variants are wanted first.
3. Eventually: Phase 1 close-out checklist (`../dax/phase-lifecycle.md`) — promotion pass, phase-summary run-note, `[phase1-done]` commit — still outstanding, deferred while this combined-dataset work was prioritized.

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
