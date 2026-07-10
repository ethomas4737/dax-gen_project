# length-baseline-review-2026-07-09 — length confound follow-up (human review of length_baseline_results.md)

## Current state
**Last updated:** 2026-07-09
**Status:** done
**Load-bearing:** `docs/phase1_eda_summary.md` §2.1/§3/§3.1/§4/§6/TL;DR now reflect these findings; `src/spikes/length_confound_followup.py` reproduces all numbers below.
**What's new since last update:** n/a (first note for this task)

## Setup

| | |
|---|---|
| Conda env | `/hpc/home/emt70/micromamba/envs/eda` |
| Tool versions | pandas 2.3.3, scikit-learn (existing `eda` env) |
| Input file(s) | `rawdata/ppi/{seqs/human.fasta,pairs/human_{train,test}.tsv}`, `rawdata/avida/{AVIDa-hIL6.csv,hIL6_antigen_sequences.csv}` |
| Spike script | `src/spikes/length_confound_followup.py` |
| Compute | DCC on-node (`dcc-core-ferc-u-ab39-1-7`, OnDemand dashboard session, no GPU needed) |

## Command (literal)

```
cd /hpc/group/singhlab/user/emt70/rp1_project/dax-gen_project
python3 src/spikes/length_confound_followup.py
```

## Counts

| Check | n |
|---|---|
| D1 ascertainment-bias check | 15,816 human proteins (`human_train`) |
| D1 rebalancing test | 421,792 train rows -> {421792, 76688, 76688} across 3 variants; scored on 52,725-row `human_test` |
| D2 clone-disjoint check | 573,891 hIL6 rows, 38,599 clones, 31 antigens |

## Verification

Re-ran the consolidated script end-to-end; all 3 checks reproduced the exact numbers found via ad hoc analysis during the review conversation (AUROC/AUPRC/posrate figures match to 4 decimal places). No QA-executor dispatch — this is exploratory follow-up analysis feeding a doc update, not a new pipeline deliverable; collapsed lifecycle per Manifesto §6.

## Findings

- **D1's length confound is an ascertainment-bias artifact, not biology.** Positive-associated proteins run longer (median 390aa vs 336aa) and higher-degree (58.4 vs 48.7) than negative-only proteins; length itself is not a hub-degree proxy (r=-0.066), so the length-only AUROC (0.652) reflects a real but non-causal correlate.
- **Rebalancing does not fix D1's confound.** Random 1:1 undersampling (AUROC 0.651) and length-decile-matched undersampling (0.653) both left the signal unchanged vs. the original 10:1 training set (0.652) — the confound lives at the protein-identity level, not the pair-length-sum level.
- **D2-hIL6's length signal is real, not split leakage.** VHH length 149aa is a genuine hotspot (3,351 distinct clones, 31.8% broad-binders vs. 10.1% population-wide) that survives a fully clone-disjoint re-split (AUROC 0.809 vs. 0.803 original, unchanged) — rules out the otherwise-plausible clone-repeat-across-split leakage mechanism (97.8% of row-random test clones also appear in train).
- Drove 5 edits to `docs/phase1_eda_summary.md`: §3.1 required stratified-reporting + rebalancing-doesn't-work caveat; new §2.1 dedup requirement (`human_test` 89 dupes, `ecoli_test` 3,761 dupes); §6 rec #7; §3/§4/TL;DR AVIDa-hIL6 correction (was stale — "noisy/lower-confidence" → confirmed real & stronger than PPI).
- No QA/promotion pass run — this is a doc-clarity follow-up on already-QA'd Phase 1 EDA outputs, not a new deliverable requiring independent QA.

## Provenance

- Project repo: committed alongside the doc changes — see journal row / commit for this task.
- Input files: `rawdata/ppi/`, `rawdata/avida/` — unchanged since Phase 1 ingestion (commits `23cbb0f` / HF-pinned revisions, per `plan-phase1.md`).
- Relevant journal rows: this session's entries dated 2026-07-09 (length-confound follow-up + doc update).
- Relevant decisions: none new — followed existing Phase 1 EDA methodology; no autonomous scope decisions made.
