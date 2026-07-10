# Phase 1 EDA Summary — dax-gen_project

**Date:** 2026-07-09
**Scope:** Descriptive EDA of 3 independent, curated datasets (PPI, antibody-antigen, viral antigenic evolution), kept separate per spec. Downstream modeling task not yet decided; this report is meant to inform that decision.
**Sources:** `docs/eda-{ppi,avida,mlaep}.md` (per-dataset detail), `docs/phase1_eda_walkthrough.ipynb` (interactive, includes independent exclusion re-verification + PLM-readiness checks).

---

## TL;DR

1. **PPI's human train/test split is pair-level, not protein-level — worth knowing before making generalization claims.** 100% of `human_test`'s proteins (by ID and by exact sequence) already appear in `human_train`. This is very likely intentional (D-SCRIPT's actual generalization claim is cross-species transfer, tested via the mouse/fly/yeast/worm/ecoli files, not this split) — but it means the human split itself demonstrates generalization to new *pairings* of known proteins, not to novel proteins. Only matters if you plan to claim novel-protein generalization specifically. 89/52,725 test pairs (0.17%) are also exact train-pair duplicates, a plain data-quality note regardless of split design. See §2.
2. **Both PPI's and AVIDa-hIL6's positive fractions are confounded with sequence length** — a real shortcut-learning risk for a length-sensitive model. PPI: length-only AUROC 0.652. AVIDa-hIL6: **stronger**, AUROC 0.803, confirmed genuine (survives a clone-disjoint re-split; not antigen confounding or noise). See §3.
3. **Class balance is engineered, not biological, for two of three datasets.** PPI is fixed at ~9.09% positive across every species (a 1:10 sampling ratio baked into the D-SCRIPT benchmark). AVIDa varies substantially by antigen (1.1%–13.7% for hIL6's 31 variants).
4. **All exclusions hold**, independently re-verified: 0 COVID/coronavirus hits in the PPI dataset (plus only one negligible non-functional pseudogene antibody-gene hit, kept per your call); 0 SARS-CoV-2 rows in either AVIDa file.
5. **No PLM context-window issues** — every sequence across all three datasets is well under the ~1022-residue limit common to ESM-2/ESM-1b/ProtBert (max is 800aa, in PPI).
6. **Data-quality caveats worth carrying forward:** heavy sequence-level duplication in PPI from isoform redundancy (56–78% of sequences — this is what drives the identity leakage in §2); non-standard `U`/`X` residues in ~0.1–0.3% of PPI sequences (AVIDa/MLAEP are fully standard-alphabet); label formatting was inconsistent across PPI's per-species files (normalized in all analysis code).

---

## 1. Per-dataset numbers

| Dataset | Rows | Positive fraction | Notes |
|---|---|---|---|
| PPI (D-SCRIPT), all species | 421,792 (human_train) down to 22,000 (ecoli_test) | **~9.09%**, identical across every species/split | Fixed 1:10 sampling ratio by construction |
| AVIDa-hIL6 | 573,891 | **3.66%** overall, 1.1%–13.7% by antigen (31 antigens) | 38,599 unique VHH clones × up to 31 antigen variants each |
| AVIDa-hTNFa | 5,580 | **12.22%** (single antigen) | ~100x smaller than hIL6, 2 subject alpacas vs. hIL6's 1 |
| MLAEP (`GMM_covid_info_seq.csv`) | 19,132 RBD mutants | **8.05%** ACE2-binding; 4.1%–18.2% per antibody-clone escape (8 clones) | Only one of MLAEP's 7 files with a natural binary label |

The other 6 MLAEP files (`pVNT.csv`, `pVNT_seq.csv`, `sars-cov-2_variants_update.csv`, `site_class.csv`, `Covid19_RBD_seq.txt`, `merged_all.jsonl`) are small reference/lookup tables or generic structural data without an interaction label — see `docs/eda-mlaep.md` for their descriptive stats.

---

## 2. Train/test protein overlap finding (PPI)

The question: does `human_test.tsv` contain proteins a model would already have seen while training on `human_train.tsv`?

**Result: 100% of `human_test`'s 15,525 unique proteins — by protein ID *and* by exact sequence — already appear in `human_train`.** Zero test proteins are genuinely unseen. Additionally, 89/52,725 test pairs (0.17%) are exact duplicates of a train pair (same two sequences, same label) — a plain data-quality note independent of split design.

**Framing — this is very likely by design, not a flaw.** D-SCRIPT's own README states its generalization claim explicitly: *"generalizes well to new species... since structure is more conserved evolutionarily than sequence, improves generalizability across species."* That claim is tested via the mouse/fly/yeast/worm/ecoli files — entirely different organisms, evaluated using the human-trained model without retraining. That's the benchmark's real held-out generalization test. The human `train`/`test` split, by contrast, is best read as a standard *pair-level* (interactome-completion) split: "given a largely-known set of human proteins, can the model correctly predict which additional pairs interact?" Protein sharing between train and test is expected and intentional for that task.

**Why it still matters for you:** a PLM-based model's performance on this human split reflects generalization to new pairings among known human proteins — a real and useful evaluation, just not evidence of generalization to unseen human proteins specifically. If your downstream work needs that narrower, stronger claim (novel human proteins, not just novel pairings or novel species), you'd need to construct your own protein-disjoint split — this benchmark's existing split isn't built to test that particular axis.

This check only applies to human (the only species with both a train and test file).

### 2.1 How to address it (train/test duplicate rows)

Two distinct duplicate-row issues — unrelated to the length confound in §3; deduplication does **not** address that (see §3.1).

1. **Required: drop `human_test`'s 89/52,725 (0.17%) exact train-pair duplicates before scoring.** These rows are identical `(protein_a, protein_b, label)` triples already seen in `human_train` — literal, if small, leakage. Fix: anti-join `human_test` against `human_train` on the full pair+label before evaluating any model.
2. **Required: dedupe `ecoli_test`'s 3,761/22,000 (~17%) within-file duplicate rows before scoring.** Not train/test leakage (ecoli has no train file) — it's redundant rows within the same test file, inflating the apparent sample size (22,000 vs. ~18,239 unique) and potentially skewing aggregate metrics if the duplicated rows lean toward one label. This one matters more than human's case, since `ecoli_test` is the file D-SCRIPT's actual cross-species generalization claim (above) gets evaluated on. Check whether the removed duplicates are label-skewed before trusting a metric computed on the deduplicated file.

Both are load-time filters for the eventual modeling-phase data loader, not edits to `rawdata/ppi/` itself — per project convention, raw data is never modified after the initial download.

---

## 3. The length-confound finding (PPI)

![](figures/plm_ppi_positive_fraction_by_length.png)

Positive fraction is flat at ~9.09% across species (by construction), but **not flat across sequence length**: the shortest-pair decile is 0.165 (~1.8x the dataset-wide baseline) and the longest-pair decile is 0.103, while every middle decile sits around 0.07–0.08.

**Why this matters:** if you train a PLM-based classifier on this data, embeddings correlate with sequence length in ways a model can exploit as a shortcut — i.e. it could partly learn "short-or-long pair → predict positive" instead of real interaction signal, and look like it's performing well while actually just recovering this artifact. Concretely: hold out a length-stratified validation split, and/or benchmark against a length-only baseline (e.g. logistic regression on `(len_a, len_b)` alone) to know how much of any future model's performance the length shortcut alone can explain.

**AVIDa-hIL6 shows a real length effect too — stronger than PPI's, and confirmed genuine, not antigen confounding or noise.** A length-only baseline (`docs/length_baseline_results.md`) scores AUROC 0.803 on hIL6 (vs. PPI's 0.652). This is not an artifact: VHH clones of length 149aa (3,351 distinct clones, not a handful of repeats) are broad binders at 31.8% vs. a 10.1% population-wide rate — a genuine ~3x enrichment, most likely reflecting CDR3-length-linked binding promiscuity (a known antibody-biology phenomenon). It survives a clone-disjoint re-split (AUROC 0.809, unchanged) — ruling out train/test clone leakage as the explanation. Antigen identity (which independently varies 1.1–13.7%) is a separate covariate, not the cause of this length effect.

### 3.1 How to address it

Steps 1–2 are required for any future model on this data; step 3 was tested this phase and found unreliable — step 2 (stratified reporting), not rebalancing, is the primary gate:

1. **Quantify it — build a length-only baseline.** Train the simplest possible classifier using *only* `(len_a, len_b)` (or their sum/product) as features. Whatever AUROC/AUPRC that gets is the floor: if a PLM-based model doesn't clear it by a meaningful margin, it isn't learning much beyond length. Done — see `docs/length_baseline_results.md` (D1 AUROC 0.652; D2-hIL6 0.803; D2-hTNFa 0.762).
2. **Required: report performance stratified by length bin** (the same bins used for the positive-fraction check), for every future model, not as an optional diagnostic. A model that only beats the length-only floor in aggregate but shows no lift *within* each length stratum is not learning past the confound, regardless of its overall AUROC/AUPRC.
3. **Rebalance so length stops correlating with the label** — either resample to match length distributions between positive and negative pairs, or use importance/inverse-propensity weighting during training. *Tested empirically on D1: random 1:1 undersampling and length-decile-matched undersampling both left the length-only AUROC unchanged (0.652 → 0.651 → 0.653).* The confound lives at the level of individual protein identity (positive-associated proteins run longer/higher-degree than negative-only proteins), not aggregate pair length, so simple rebalancing is not a reliable fix — don't rely on this step; use step 2 instead. Separately, for D2-hIL6 the length signal was confirmed to be genuine CDR3-length-linked binding promiscuity (survives a clone-disjoint re-split, AUROC 0.809 vs. 0.803) rather than an artifact — rebalancing it away would delete real biology, not correct a flaw.
4. **Keep the length-only baseline as a permanent reporting companion**, not a one-time check — report it alongside every future model result.
5. **(More involved) Adversarial/invariance training** — add a head that tries to predict length from the embedding and train the main model to make it fail, if the baseline in step 1 turns out to be uncomfortably strong. Usually only needed if steps 1–4 aren't enough.

---

## 4. PLM-readiness (given the planned downstream PLM use)

![](figures/plm_length_vs_context_window.png)

| Check | Result |
|---|---|
| Train/test protein overlap | **PPI: 100% of test proteins already seen in train (§2)** — a pair-level split by design, not a flaw. Affects how novel-protein-generalization claims (specifically) should be interpreted. |
| Label vs. length confound | **PPI: real, §3.** **AVIDa-hIL6: real, and stronger than PPI (AUROC 0.803 vs. 0.652) — confirmed via clone-disjoint re-split, not antigen confounding or noise.** Not applicable to MLAEP's fixed-length mutants. |
| Context window (~1022 residue common limit) | **Clear everywhere** — max is 800aa (PPI), 201aa (MLAEP RBD), 179aa (AVIDa VHH). No truncation strategy needed. |
| Non-standard residues (`X`, `U`, `B`, `Z`, gaps) | AVIDa and MLAEP: **fully standard-alphabet**. PPI: `U`/`X` present in human (221/70,529 seqs), mouse (217/40,606), fly (8/19,310), worm (1/25,930); yeast/ecoli clean. Likely fine with modern PLM tokenizers, but worth confirming against the specific tokenizer used. |

---

## 5. Data-quality notes (not blockers, but relevant to modeling decisions)

- **PPI sequence duplication**: 56–78% of sequences per species are exact duplicates under different protein IDs — reflects transcript-isoform redundancy in the underlying STRING/Ensembl protein set. Related to, though not the sole cause of, the train/test protein overlap in §2 (which mainly reflects the split being pair-level by design).
- **`ecoli_test.tsv` has 3,761 duplicate rows** (exact pair+label duplicates) out of 22,000 — unique to this file; every other PPI file has 0.
- **AVIDa-hIL6's "93% duplicate VHH sequence" figure is expected, not an error**: 38,599 unique VHH clones, each tested against a median of 14 (up to all 31) antigen variants — one row per (VHH, antigen) combination by design.
- **Column-order inconsistency**: `AVIDa-hIL6.csv` and `AVIDa-hTNFa.csv` have `label`/`Ag_label` in swapped column order — always read by name, not position.
- **Label formatting inconsistency in PPI**: human files use int `0`/`1`; other species use float `0.0`/`1.0` — already normalized in all analysis code, but worth knowing if writing new code against these files directly.

---

## 6. Recommendations for scoping the downstream task

1. **If the downstream goal specifically needs a novel-human-protein generalization claim, don't rely on D-SCRIPT's built-in human train/test split as evidence** — it's a pair-level split by design (§2); construct your own protein-disjoint split for that specific claim. If the goal is cross-species generalization or pair-level/interactome-completion evaluation, the existing splits (human train/test + the cross-species test files) already serve that purpose as intended.
2. **Decide the modeling task with the length confound in mind** — plan from the start to check performance against a length-only baseline, not as an afterthought (§3.1).
3. **Consider isoform-aware splitting for PPI** in general, given the high duplicate-sequence rate, if you build your own custom split.
4. **Confirm PLM tokenizer handling of `U`/`X`** before committing to a specific pretrained PLM, since PPI is the dataset affected.
5. **AVIDa's per-antigen positive-fraction variation (1.1–13.7%)** suggests antigen identity is a meaningful covariate — worth deciding whether the downstream task treats antigens jointly (pooled) or separately (per-antigen models/evaluation).
6. Datasets remain intentionally unmerged per spec — nothing above argues for merging them, but the shared PLM-readiness lens (context window, vocabulary, split design) is a useful frame if a future phase builds a shared embedding pipeline across all three.
7. **Dedupe PPI's train/test duplicate rows before any real evaluation** — `human_test`'s 89 exact train-pair duplicates and `ecoli_test`'s 3,761 within-file duplicate rows (§2.1) both need handling at load time; neither is addressed by the length-confound mitigation above.

---

*Full technical detail, independent verification code, and additional figures are in `docs/eda-{ppi,avida,mlaep}.md` and `docs/phase1_eda_walkthrough.ipynb`.*
