# Session handoff

**Read this first.** Live cursor of project state. Rewritten as work proceeds (Legislation §3 — `journal.md` is the history; ≤120 lines hard cap).

## Last updated

**2026-07-09** — Phase 1 (curate 3 datasets + EDA) fully executed, not yet formally closed. Human pulled forward the previously-deferred dataset-merging item: built + EDA'd 4 combined variants (D1-D4), including a second held-out axis (8-antibody escape panel, sequences sourced from CoV-AbDab). Also ran a length-only baseline that found length is a **stronger-than-expected** confound in both D1 and D2. See `spec/spec.md` "Revision 2026-07-09".

## Current position

**Phase 1 deliverables:** `rawdata/{ppi,avida,mlaep}/` (gitignored, each with `SOURCE.md`) + `docs/eda-{ppi,avida,mlaep}.md` + `docs/figures/*.png` + `docs/phase1_eda_walkthrough.ipynb` (executed) + `docs/phase1_eda_summary.md`/`.html` (consolidated report, also a Claude Artifact). Not formally closed (no close-out checklist run yet).

**Combined-dataset deliverables:** `rawdata/combined/{d1_ppi,d2_avida,d3_ppi_avida,d4_heldout_mlaep_ace2,d4_heldout_mlaep_antibodies}.csv` (gitignored, `SOURCE.md` present) + `docs/eda-combined.md`/`.html` (also a Claude Artifact). D1=D-SCRIPT PPI (716,517 rows), D2=AVIDa no-COVID (579,471), D3=D1∪D2 training pool (1,295,988). D4 held-out has **two axes**: (a) ACE2 (19,132 rows, RBD_mutant+human_ACE2, `ace2_bind` label) and (b) an 8-antibody escape panel (153,056 rows = 8×19,132, RBD_mutant+VH/VL, label flipped to `1=binds`) — VH/VL sourced from CoV-AbDab since the original paper (Zost et al. 2020) gates its sequences behind "available on request." Both axes verified zero-overlap with the D3 training pool. Built by `src/spikes/build_combined_datasets.py` + `eda_combined.py`.

**Key findings (Phase 1):** PPI positive fraction fixed ~9.09% (1:10 sampling); AVIDa hIL6 3.66%/hTNFa 12.22%; MLAEP ACE2-bind 8.05%. PLM-readiness: PPI human train/test shares 100% of proteins (pair-level split by design, not a flaw); PPI positive fraction confounded with pair length (remediation steps in `docs/phase1_eda_summary.md` §3.1); all seqs within PLM context limits; PPI has U/X in ~0.1-0.3% of seqs.

**Key findings (combined D1-D4):** Both held-out axes verified genuinely clean (zero sequence overlap with D3, both directions). 1 sequence (human TNF-alpha) shared between D1/D2 (not a leakage concern). ACE2 axis has zero length variance and ACE2 (805aa) exceeds D1's 800aa training cap by 5aa. `seq_a`/`seq_b` column semantics differ by `pair_type` in D3 (symmetric PPI vs. asymmetric antibody/antigen). Antibody-panel binds-fractions (82-96% per clone) cross-checked as exactly `1-escape_fraction` against original MLAEP numbers. Full detail in `dax-state/runs/combined-datasets-2026-07-09.md` and `docs/eda-combined.md`.

**Length-only baseline results (`docs/length_baseline_results.md`):** length-derived features alone (no sequence content) meaningfully beat random in **all 3 cases tested**: D1-PPI AUROC 0.652/AUPRC 2x floor; D2-hIL6 AUROC **0.803**/AUPRC 3.9x floor (stronger than PPI); D2-hTNFa AUROC 0.762/AUPRC 3.3x floor (small n, more variance). hIL6's strength isn't fully explained by antigen-mean-length differences (only 150.8-151.2aa spread) — likely reflects CDR3-length-correlated binding promiscuity at the individual-VHH level. **Any future PLM-based model must clear these numbers by a real margin** to demonstrate real sequence-specific learning rather than a length/composition shortcut.

**Recent commits:**
- (pending) — Add length-only baseline script + results.
- `64484a9` — Add docs/eda-combined.html companion report.

## Next action

1. **Human review** of `docs/length_baseline_results.md` — the length signal is stronger than initially expected in both D1 and D2, worth discussing before scoping any fine-tuning run.
2. Decide whether D3/D4 are inputs to an actual PLM fine-tuning run next (with the length-only floor as a required side-by-side comparison), or whether more EDA/variants are wanted first.
3. Eventually: Phase 1 close-out checklist (`../dax/phase-lifecycle.md`) — promotion pass, phase-summary run-note, `[phase1-done]` commit — still outstanding, deferred while this combined-dataset/baseline work was prioritized.

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
