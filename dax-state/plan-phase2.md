# Phase 2 plan — PLM baseline modeling (3 models × 3 datasets, D4 held-out)

## Current state
**Last updated:** 2026-07-10
**Load-bearing as of this date:** Real scope is 9 training runs (M1/M2/M3 × D1/D2/D3) + a D4 held-out eval pass on all 9 — see `spec/spec.md` Revision 2026-07-10b. This rewrite supersedes the single-run (M1-on-D1-only) version of this file. Nothing beyond step 0 has executed yet under the corrected scope.
**What's new since last update:** Human clarified the 9-run matrix (2026-07-10). Surfaced that the existing M1 pipeline only curates D1's human-species subset, not the full 6-species D1 — job 49561386 (which also failed independently, on the dirty-repo guard) needs redoing after D1 curation is extended. All 5 open decisions below are now **resolved** (2026-07-10) — plan is ready to execute pending final go-ahead.

Status defaults to `not started`; update on step start/complete per the operational protocol in `CLAUDE.md`.

| Step ID | Status | Description | Inputs | Outputs | Role | Deps | Notes (plan-time, ≤200 chars) | Outcome (≤80 chars) |
|---|---|---|---|---|---|---|---|---|
| 0 | done | Build M1 pipeline scaffold (data prep, model, train, eval) + CPU smoke test, on D1's human-species subset only | `rawdata/ppi/pairs/human_*.tsv`, `seqs/human.fasta` | `src/spikes/phase2/{data_prep,model,train_m1,evaluate}.py` | executor | — | Scope now known to be too narrow for "D1" per spec — see step 1. | done — see runs/phase2-m1-d1-pipeline.md (superseded by step 1 for real D1 scope) |
| 1 | not started | Extend D1 curation to all 6 species (add mouse/fly/yeast/worm/ecoli to `data_prep.py`'s dedup + bad-residue filtering, currently human-only); **decided:** concatenate each species' existing train/test split into one D1 train/test | `rawdata/ppi/pairs/{human,mouse,fly,yeast,worm,ecoli}_{train,test}.tsv` + `seqs/*.fasta` | `data/curated/d1_ppi/{train,test}.csv` (full, ~716K rows pre-filter) | executor | 0 | Concatenation approach confirmed 2026-07-10 — no fresh split needed. | not started |
| 1-qa | not started | QA: verify dedup/bad-residue counts per species, zero cross-species leakage introduced by concatenation | step 1 outputs | qa note | qa-executor | 1 | | not started |
| 2 | not started | Build D2 curated train/test split (AVIDa hIL6+hTNFa, no official split exists); **decided:** fresh stratified 80/20 by label, saved as a reusable artifact | `rawdata/combined/d2_avida.csv` | `data/curated/d2_avida/{train,test}.csv` | executor | — | Split scheme confirmed 2026-07-10 — same shape as Phase 1's ad hoc baseline split, but now saved for reuse. | not started |
| 3 | not started | Build D3 curated train/test split (D1 ∪ D2); **decided:** concatenation of D1's + D2's respective splits | step 1 + step 2 outputs | `data/curated/d3_combined/{train,test}.csv` | executor | 1, 2 | Confirmed 2026-07-10 — not a fresh joint split. | not started |
| 4 | not started | Implement M2: attention-pooling variant (`model.py`'s `AttnPooling` is currently a stub, raises `NotImplementedError`) | `model.py` | working `AttnPooling` + head | executor | — | Independent of steps 1-3; can build in parallel. | not started |
| 5 | not started | Implement M3: LoRA-wrapped trainable backbone; **decided:** HuggingFace `peft`, low rank (r=8-16) targeting attention q/k/v/o projections | `model.py` | new loader/training path for M3 | architect, executor | — | Verify `peft` targets ESM-C's module names cleanly before committing to this path; fall back to a custom LoRA layer only if it doesn't. M1/M2's embed-once-cache trick does NOT carry over — M3 needs its own training loop (per-batch backbone forward) and its own GPU resource estimate. | not started |
| 6 | not started | Build `train_lora.py` (M3) separate from a generalized `train_frozen.py` (M1/M2, `--pooling mean\|attn`); **decided:** keep the two training loops separate, not one unified script | steps 0, 4, 5 | `train_frozen.py`, `train_lora.py`, shared `evaluate.py` | architect, executor | 0, 4, 5 | Confirmed 2026-07-10 — avoids branching one script around two fundamentally different training loops for a script only run 9 times total. | not started |
| 7 | not started | Build a reusable D4 held-out eval harness (both axes: ACE2 + 8-antibody panel) that scores any of the 9 trained models | `rawdata/combined/d4_heldout_*.csv`, any trained checkpoint | `docs/d4_heldout_eval.py` or similar + per-model results | executor | 6 | Reuses Phase 1's D4 build logic; new part is scoring an arbitrary checkpoint against it. | not started |
| 8 | not started | Run all 9 training jobs on GPU (`singhlab-gpu`) | steps 1-3, 6 outputs | 9 trained checkpoints | executor | 1-qa, 2, 3, 6 | **Requires human approval before each GPU allocation request** (no autonomous GPU start). M3's 3 runs likely need a separate, larger resource ask than M1/M2's 6. | not started |
| 9 | not started | Run D4 held-out eval (both axes) against all 9 trained checkpoints | step 7, 8 outputs | per-model D4 results | executor | 7, 8 | | not started |
| 10 | not started | Consolidated evaluation report: all 9 own-dataset results + all 9 D4 generalization results, each with length-decile-stratified breakdown vs. the relevant length-only baseline | steps 8, 9 | `docs/phase2_eval_report.md` | executor, reviewer | 9 | Per `phase1_eda_summary.md` §3.1 stratified-reporting requirement. | not started |

## Decisions (resolved 2026-07-10)

1. **Step 1:** concatenate each species' existing D-SCRIPT train/test split into one D1 train/test (not a fresh combined split).
2. **Step 2:** fresh stratified 80/20-by-label split for D2, saved as a reusable artifact under `data/curated/d2_avida/`.
3. **Step 3:** D3 = concatenation of D1's + D2's splits (not a fresh joint split).
4. **Step 5:** M3 uses HuggingFace `peft`, low rank (r=8-16), targeting attention q/k/v/o projections — pending a quick check that `peft` cleanly targets ESM-C's module names; custom LoRA is the fallback only if it doesn't.
5. **Step 6:** separate `train_frozen.py` (M1/M2) and `train_lora.py` (M3) rather than one unified script.

After all step-QA passes: promote spike scripts from `src/spikes/phase2/` to `src/` per `../dax/agent-configs/promotion-rules.md`, append journal rows, update `session-handoff.md`, commit per `[<step-id>] <short action>`.
