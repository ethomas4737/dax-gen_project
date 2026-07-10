# dax-gen_project: curate three independent sequence-interaction datasets (PPI, antibody-antigen, viral antigenic evolution) and characterize each via EDA

## Current state
**Last updated:** 2026-07-10
**Load-bearing as of this date:** Phase 1 (curate 3 datasets + EDA + D1-D4 combinations + length-only baseline) complete, not yet formally closed. Phase 2's **real scope is a 3x3 matrix** (models M1/M2/M3 × datasets D1/D2/D3, D4 held-out for eval) — see "Revision 2026-07-10b" below, which supersedes the single-run framing in "Revision 2026-07-10".
**What's new since last update:** Human clarified the 9-run matrix (previously undocumented). Also surfaced: the M1-on-D1 pipeline built so far only curates D1's human-species subset, not the full 6-species D1 the spec defines — needs extending before any run counts as a valid D1 result.

## Goal

Locate, fetch, and curate three independent, publicly-available biological sequence-interaction datasets — kept **separate, not merged** — and produce descriptive exploratory data analysis (EDA) for each. This is a data-foundation phase: the downstream modeling task (e.g. binding-affinity prediction, antigenic-escape prediction) is deliberately **not** decided yet and will be scoped in a later phase once the data is understood. A candidate result satisfies this phase if each of the three datasets is present in a documented, provenance-tracked form under `rawdata/`, with the stated exclusions applied, and an EDA report exists per dataset covering size, label balance, sequence-length distribution, and any relevant category breakdown (species / antigen / variant).

## Background

Three dataset families were identified, each associated with a specific published tool/paper:

1. **D-SCRIPT** (Sledzieski, Singh et al., *Cell Systems* 2021) — a sequence-based, structure-aware protein-protein interaction (PPI) predictor. Its GitHub repo ships ready-to-use PPI pair files per species (human/mouse/fly/yeast/worm/ecoli), separate from any virus- or antibody-specific application data used elsewhere in the paper.
2. **AVIDa** (COGNANO, NeurIPS 2023 workshop lineage) — large-scale VHH (single-domain antibody) to antigen binding datasets, one file per antigen: `AVIDa-hIL6` (human IL-6), `AVIDa-hTNFa` (human TNF-alpha), and `AVIDa-SARS-CoV-2` (SARS-CoV-2 spike variants). Hosted on HuggingFace under `COGNANO/*`.
3. **MLAEP** (Han et al., *Nat. Commun.* 2023) — Machine Learning-guided Antigenic Evolution Prediction for SARS-CoV-2. Its GitHub repo bundles small preprocessed derived files (variant sequences, escape/binding scores, site-class annotations); the full raw GISAID corpus it was originally trained on requires individual GISAID registration and is out of scope for this phase.

Two explicit exclusion rules apply (human-specified, not incidental): the PPI dataset must exclude any COVID- or antibody-specific data, and the AVIDa antibody dataset must exclude the SARS-CoV-2 antigen subset. MLAEP is inherently and entirely SARS-CoV-2-focused by design, so the exclusion rule does not apply to it.

## Data sources

| File / dataset | Origin | Role |
|---|---|---|
| `data/pairs/{human,mouse,fly,yeast,worm,ecoli}_{train,test}.tsv` + `data/seqs/*.fasta` | github.com/samsledje/D-SCRIPT (repo-included, not the ~4GB Zenodo archive) | Primary input — generic PPI pairs. Clean of COVID/antibody data by construction (excluded per instruction). |
| `AVIDa-hIL6` (573,891 VHH-antigen pairs, wild-type + 30 IL-6 mutants) | huggingface.co/datasets/COGNANO/AVIDa-hIL6 (CC-BY-NC-4.0) | Primary input — antibody(VHH)-antigen binding data. |
| `AVIDa-hTNFa` | huggingface.co/datasets/COGNANO/AVIDa-hTNFa (CC-BY-NC-4.0, presumed same license family) | Primary input — antibody(VHH)-antigen binding data, second antigen for broader coverage. |
| MLAEP repo-included preprocessed files (`GMM_covid_info_seq.csv`, `merged_all.jsonl`, `sars-cov-2_variants_update.csv`, `site_class.csv`, `pVNT_seq.csv`, `pVNT.csv`, `Covid19_RBD_seq.txt`) | github.com/WHan-alter/MLAEP `data/` | Primary input — SARS-CoV-2 antigenic-evolution / escape data. |

**Explicitly excluded:** `COGNANO/AVIDa-SARS-CoV-2`; the D-SCRIPT Zenodo archive's virus-application subset (not fetched at all — using the lightweight repo data instead); MLAEP's raw GISAID corpus (requires individual registration, deferred).

**Verified (2026-07-09):** all 15,816 unique human proteins across `human_train.tsv`/`human_test.tsv` resolved via mygene.info — 0 SARS-CoV-2/coronavirus hits (impossible anyway, since pairs are intra-species). 1 protein (`ENSP00000474135`, gene `IGHV3OR16-17`, a non-functional immunoglobulin-variable-region pseudogene) appears in 33/474,517 pairs, always as a negative (non-interacting) label — judged not to constitute antibody-antigen data and left in.

All three land under `rawdata/` (gitignored, per project convention) with a `SOURCE.md` per subfolder recording the exact URL/commit/DOI fetched and fetch date. `rawdata/` is treated as read-only after the initial drop (Manifesto Articles 5–6 provenance).

## Phase 1 deliverables

1. **Step 1 — Fetch & curate D-SCRIPT PPI data.** Pull `data/pairs/*.tsv` + `data/seqs/*.fasta` from the D-SCRIPT GitHub repo (pinned commit) into `rawdata/ppi/`.
2. **Step 2 — Fetch & curate AVIDa antibody data.** Pull `AVIDa-hIL6` and `AVIDa-hTNFa` from HuggingFace into `rawdata/avida/`, explicitly verifying no SARS-CoV-2 rows are present.
3. **Step 3 — Fetch & curate MLAEP data.** Pull the listed preprocessed files from the MLAEP GitHub repo (pinned commit) into `rawdata/mlaep/`.
4. **Step 4 — EDA per dataset.** Three separate EDA reports/notebooks (not a merged analysis): row counts, **positive fraction** (share of rows labeled interacting/binding=1, overall and broken down by species/antigen/variant where applicable), sequence-length distributions, species/antigen/variant breakdowns, missingness, duplicate-sequence checks.

(Subsequent steps as needed.)

## Phase 1 acceptance criteria

- **Step 1:** `rawdata/ppi/` contains all six species' train/test pair files + fasta seqs; a `SOURCE.md` records the pinned commit SHA; spot-check confirms no SARS-CoV-2 or antibody-labeled sequences present.
- **Step 2:** `rawdata/avida/` contains `AVIDa-hIL6` and `AVIDa-hTNFa` only; a row-level check confirms zero SARS-CoV-2-antigen rows; `SOURCE.md` records HF dataset revision/commit.
- **Step 3:** `rawdata/mlaep/` contains the seven listed files; `SOURCE.md` records the pinned commit SHA; a note documents that full raw GISAID access is deferred.
- **Step 4:** Three EDA notebooks/reports exist (`docs/eda-ppi.*`, `docs/eda-avida.*`, `docs/eda-mlaep.*` or similar), each runnable end-to-end and covering the stats listed in deliverable 4.
- **All steps:** code lives in `src/spikes/` first, promoted to `src/` only after the step's QA passes. Each step's outputs are linked from `dax-state/journal.md`.

## Constraints / environment

- No modification of `rawdata/` after initial drop; `rawdata/` is gitignored (large files, not tracked).
- Tag generated code as study (`src/spikes/`) or working (`src/`) per Manifesto Article 6.
- Provenance per Articles 5–6: every artifact records inputs, command lines/URLs, and the source commit/revision it was fetched from.
- No DCC GPU compute required for this phase (fetch + EDA is CPU/IO-bound); revisit compute needs once a downstream modeling task is scoped.

## Deferred (Phase 2+)

- Defining the actual downstream modeling task (binding prediction, antigenic-escape prediction, or something else) — deliberately deferred until the EDA is in hand.
- Whether to expand D-SCRIPT to the full ~4GB Zenodo archive (more comprehensive PPI data, would need explicit COVID/antibody filtering).
- Whether to pursue full raw GISAID access for MLAEP (requires individual registration).
- Any merging/unification of the three datasets into a common schema (explicitly out of scope for Phase 1 — datasets stay separate and curated individually).

## Open questions

1. Is `AVIDa-hTNFa`'s license confirmed as CC-BY-NC-4.0 (same as `AVIDa-hIL6`)? Not yet independently verified — check on fetch.
2. Should `COGNANO/VHHCorpus-2M` (generic VHH sequence corpus, no antigen labels) be included as a fourth reference set, or is it out of scope since it's not antigen-interaction data?

---

## Revision 2026-07-09 — dataset combinations requested (pulls forward a deferred item)

Human requested 4 combined-dataset variants, ahead of the "any merging/unification" item originally deferred to Phase 2+:

- **D1** = D-SCRIPT PPI (all species/splits), unified to `(seq_a, seq_b, label)`.
- **D2** = AVIDa, no COVID (hIL6 + hTNFa), unified to `(seq_a=VHH, seq_b=antigen, label)`.
- **D3** = D1 ∪ D2 (concatenated, common schema, tagged by `pair_type`/`source_dataset`).
- **D4** = D3 as the training pool, with MLAEP reframed as a **held-out evaluation partition** (not merged into training rows): each of the 19,132 RBD mutants in `GMM_covid_info_seq.csv` is paired with the human ACE2 receptor sequence (fetched from UniProt Q9BYF1) using the `ace2_bind` column as the label — a genuine PPI-shaped row (viral RBD ↔ host receptor), used only to evaluate whether a model trained on D3 (zero viral data) generalizes to viral antigen binding.

This narrows/operationalizes the previously-deferred "Any merging/unification of the three datasets into a common schema" item — decided now rather than left fully open. See `dax-state/journal.md` for build details and `dax-state/runs/` for the run-note.

---

## Revision 2026-07-10 — Phase 2 opened: PLM baseline modeling (M1 on D1)

Phase 2 goal: establish a first PLM-based baseline model ("M1": frozen ESM-C 300M backbone + a small trainable MLP head over mean-pooled per-protein embeddings) on **D1** (D-SCRIPT PPI), and compare it against the Phase 1 length-only baseline (`docs/length_baseline_results.md`, D1 AUROC 0.652) using the stratified-reporting requirement from `docs/phase1_eda_summary.md` §3.1.

Deliverables:
1. **M1-on-D1 pipeline** — data prep (dedup + bad-residue filtering per §2.1's requirement), model, train, eval scripts. **Done** (`src/spikes/phase2/{data_prep,model,train_m1,evaluate}.py`), CPU-smoke-tested end-to-end (loss decreases monotonically over 8 epochs, both scripts exit 0). See `dax-state/runs/phase2-m1-d1-pipeline.md`.
2. **Real training run** on the full curated D1 (419,916 train / 52,424 test rows) — requires a GPU allocation (est. 1x A6000, `singhlab-gpu`, ~15-30 min compute / 1hr walltime ask). **Not started** — GPU allocation must be requested and approved by the human before submission (no autonomous GPU allocation, per Manifesto + `rohit-dcc-onnode`).
3. **Evaluation report** — aggregate AUROC/AUPRC plus the length-decile-stratified table (per §3.1) versus the length-only floor. **Not started.**

Acceptance criteria: the pipeline runs end-to-end on a real GPU allocation against the full curated D1 data (not just the CPU smoke subset); the evaluation report includes both the aggregate metric and the length-stratified breakdown, explicitly compared to the 0.652 AUROC length-only floor.

Note: deliverable 1 was actually built in a prior session without a formal phase-open (no `plan-phase2.md` existed yet at the time). This revision retroactively formalizes it per Manifesto §6. See `dax-state/decisions.md` for the one autonomous technical decision made during that build (ESM-C checkpoint loader workaround).

---

## Revision 2026-07-10b — Phase 2's real scope: 3 models × 3 datasets, D4 held-out

Supersedes the single-run (M1-on-D1-only) framing above, which was incomplete — the human clarified the actual intended scope (from an earlier conversation not captured in this project's durable state at the time):

**9 training runs = models {M1, M2, M3} × datasets {D1, D2, D3}.** **D4 is not a training input** for any of the 9 — it stays the held-out evaluation partition (both its ACE2 axis and its 8-antibody-escape-panel axis, per the Phase 1 combined-dataset work) used to evaluate all 9 trained models' generalization to viral antigen binding.

- **M1** — frozen ESM-C 300M backbone (mean-pooled) + trainable MLP head. Built and CPU-smoke-tested (Revision 2026-07-10 deliverable 1). `model.py` already structures the backbone/pooling/head as swappable pieces for M2/M3.
- **M2** — frozen ESM-C 300M backbone + **attention-pooling** (vs. M1's mean-pooling) + MLP head. Currently a structural stub in `model.py` (`AttnPooling` raises `NotImplementedError`) — not built.
- **M3** — ESM-C 300M backbone **LoRA-wrapped and trainable** (vs. M1/M2's frozen backbone) + pooling + MLP head. Not built. Note: M1/M2's core efficiency trick (embed each unique protein once, cache, train only the head) does not carry over to M3 — a trainable backbone means embeddings change every optimizer step, so M3 needs a different training loop (backbone forward pass per batch, not a fixed cache). This changes M3's resource estimate materially vs. M1/M2's.
- **D1** — full D-SCRIPT PPI, **all 6 species** (716,517 rows per the Revision 2026-07-09 definition), not just the human subset currently curated in `data/curated/d1_ppi/`. `data_prep.py` needs extending to cover mouse/fly/yeast/worm/ecoli before any D1 run is valid against this spec.
- **D2** — AVIDa, no-COVID (hIL6 + hTNFa), per the Revision 2026-07-09 definition. No curated train/test split exists yet for training purposes (Phase 1's length baseline used an ad hoc 80/20 stratified split, not saved as a reusable artifact).
- **D3** — D1 ∪ D2 per the Revision 2026-07-09 definition. No curated train/test split exists yet.

**Acceptance criteria (revised):** all 9 (model × dataset) combinations trained and evaluated on their own dataset's held-out test split, **plus** all 9 evaluated against D4 (both axes) as a fixed generalization check; each result reported with the length-decile-stratified breakdown (Phase 1 §3.1 requirement) alongside the aggregate metric, and compared against the appropriate length-only baseline per dataset.

This is a substantially larger scope than Revision 2026-07-10's single M1-on-D1 run. See `dax-state/plan-phase2.md` (rewritten) for the build plan, presented to the human for approval before execution per Manifesto §6.

<!--
Spec-writing notes (per `../dax/agent-configs/spec-writer.md` + Legislation §3):

- spec/spec.md is append-only at section granularity. Revisions go as
  "## Revision YYYY-MM-DD — <reason>" sections appended at the bottom.
  Don't rewrite prior content — it's the audit trail of how scope evolved.
- Keep the spec ≤1 page per phase; once it exceeds ~200 lines or 3 phases,
  modularize: spec/master.md becomes a 1-page index; spec/phase{N}.md per-phase files.
- Update the `## Current state` front-matter at the top whenever a revision lands.
-->
