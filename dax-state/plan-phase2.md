# Phase 2 plan — PLM baseline modeling (M1 on D1)

## Current state
**Last updated:** 2026-07-10
**Load-bearing as of this date:** Step 1 (pipeline build + CPU smoke test) done. Step 2 (real GPU training run) blocked on human approval to request a GPU allocation.
**What's new since last update:** Phase opened this session (retroactive formalization of a prior session's pipeline build); plan created for the first time.

Active execution plan for Phase 2. Status defaults to `not started`; update on step start/complete per the operational protocol in `CLAUDE.md`.

| Step ID | Status | Description | Inputs | Outputs | Role | Deps | Notes (plan-time, ≤200 chars) | Outcome (≤80 chars) |
|---|---|---|---|---|---|---|---|---|
| 1 | done | Build M1-on-D1 pipeline (data prep w/ dedup + bad-residue filters, frozen ESM-C 300M + MLP head model, train/eval scripts) + validate via CPU smoke test | `rawdata/ppi/pairs/human_{train,test}.tsv`, `rawdata/ppi/seqs/human.fasta` | `src/spikes/phase2/{data_prep,model,train_m1,evaluate}.py`; `data/curated/d1_ppi/{train,test}.csv`; smoke artifacts in `runs/phase2_m1_d1/smoke/` | executor | — | CPU-only, login-node RSS-limited (2GB); real run needs GPU. | done — see runs/phase2-m1-d1-pipeline.md |
| 1-qa | partial | Independent QA-executor pass on the pipeline (dedup/bad-residue counts, checkpoint load correctness) | pipeline outputs above | qa note | qa-executor | 1 | Run-note's own "Verification" section re-derived key counts independently, but no separate qa-executor dispatch has run yet. | partial — self-verified in run-note; independent QA pass outstanding |
| 2 | in progress | Request GPU allocation (`singhlab-gpu`, 1x A6000, ~1hr walltime) and run real M1-on-D1 training on full curated D1 (419,916 train / 52,424 test rows) | curated D1 data, pipeline scripts | trained head checkpoint, embedding cache, `eval_results.json` | executor | 1, 1-qa | Human approved 2026-07-10; submitted via `sbatch`. | in progress — see journal for jobid |
| 2-qa | not started | QA: confirm training converged (loss curve), no config drift vs. the smoke run | step 2 outputs | qa note | qa-executor | 2 | | not started |
| 3 | not started | Evaluation report: aggregate AUROC/AUPRC + length-decile-stratified table vs. the length-only baseline (0.652 AUROC, `docs/length_baseline_results.md`) | step 2 outputs | `docs/m1_d1_eval.md` or similar | executor | 2-qa | Per `phase1_eda_summary.md` §3.1 stratified-reporting requirement. | not started |

After all step-QA passes: promote spike scripts from `src/spikes/phase2/` to `src/` per `../dax/agent-configs/promotion-rules.md`, append journal rows, update `session-handoff.md`, commit per `[<step-id>] <short action>`.
