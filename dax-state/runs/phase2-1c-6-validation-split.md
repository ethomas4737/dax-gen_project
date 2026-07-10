# phase2-1c-6-validation-split — Val split (1c) + per-epoch validation loop (6, reopened)

## Current state
**Last updated:** 2026-07-10
**Status:** done
**Load-bearing:** `data/curated/d1_ppi/{train,val,test}.csv` (377,924 / 41,992 / 52,424 rows) are now the real curated D1 splits any future training run should use. `train_frozen.py`/`train_lora.py` now require a `val.csv` alongside `train.csv`/`test.csv` in `--data-dir` (both the full and smoke data dirs have it).
**What's new since last update:** First implementation of step 1c (val split) and closure of the step 6 reopen (per-epoch validation monitoring in both training scripts).

## Setup

| | |
|---|---|
| Conda env | `/hpc/home/emt70/micromamba/envs/esmc` |
| Tool versions | `esm` v3.3.0 + `torch` v2.12.0 + `peft` v0.19.1 + `pandas`/`numpy`/`scikit-learn` |
| Compute | DCC, via `sbatch` (partition `common`, account `singhlab`) — **not** run directly in the interactive OnDemand Jupyter session node (see Findings #1) |
| Input file | `data/curated/d1_ppi/train.csv` (pre-split, 419,916 rows) |
| Repo SHA at run | `bd882effa26af037a7ab77cdd4c155ae406c7c23` (parent of this work; this run-note's commit is built on top) |

## Command (literal)

```bash
ENVPY=/hpc/home/emt70/micromamba/envs/esmc/bin/python
REPO=/hpc/group/singhlab/user/emt70/rp1_project/dax-gen_project
cd $REPO/src/spikes/phase2

# Step 1c: full curation + val split + smoke subset (submitted via sbatch, see Finding #1)
sbatch --partition=common --account=singhlab --cpus-per-task=2 --mem=8G --time=00:20:00 \
  --wrap="cd $REPO/src/spikes/phase2 && $ENVPY -u data_prep.py \
    --smoke-n-train 15 --smoke-n-test 10 --smoke-n-val 10 --seed 2"

# M3 smoke needs short synthetic sequences (known OOM workaround, see Findings #2)
$ENVPY make_synthetic_short_seqs.py --n-train 15 --n-val 10 --n-test 10 --seed 3

# Step 6: all 6 combinations smoke-tested (train x {mean,attn,lora} + eval x {mean,attn,lora}),
# submitted as one sbatch job (--mem=8G, --time=00:30:00, partition=common)
$ENVPY -u train_frozen.py --pooling mean --data-dir $REPO/data/curated/d1_ppi_smoke \
  --out-dir $REPO/runs/phase2_m1_d1/smoke_val --epochs 5 --device cpu --embed-batch-size 4
$ENVPY -u train_frozen.py --pooling attn --data-dir $REPO/data/curated/d1_ppi_smoke \
  --out-dir $REPO/runs/phase2_m2_d1/smoke_val --epochs 5 --device cpu --embed-batch-size 4
$ENVPY -u train_lora.py --data-dir $REPO/data/intermediate/d1_ppi_smoke_lora_short \
  --out-dir $REPO/runs/phase2_m3_d1/smoke_val --epochs 5 --device cpu --batch-size 4
$ENVPY -u evaluate.py --run-dir $REPO/runs/phase2_m1_d1/smoke_val --data-dir $REPO/data/curated/d1_ppi_smoke --variant mean
$ENVPY -u evaluate.py --run-dir $REPO/runs/phase2_m2_d1/smoke_val --data-dir $REPO/data/curated/d1_ppi_smoke --variant attn
$ENVPY -u evaluate.py --run-dir $REPO/runs/phase2_m3_d1/smoke_val --data-dir $REPO/data/intermediate/d1_ppi_smoke_lora_short --variant lora
```

## Counts

| Split | Rows | Positive rate |
|---|---|---|
| `data/curated/d1_ppi/train.csv` (new, post-split) | 377,924 | 0.0912 |
| `data/curated/d1_ppi/val.csv` (new) | 41,992 | 0.0912 |
| `data/curated/d1_ppi/test.csv` (untouched) | 52,424 | 0.0912 |
| Sum train+val | 419,916 | matches pre-split clean train count exactly |
| Smoke: train / val / test | 15 / 10 / 10 | n/a at this scale |
| M3 synthetic-short smoke: train / val / test | 15 / 10 / 10 | n/a (synthetic, 20-35aa seqs) |

Sbatch job wall clock: `data_prep.py` full run — 14s (8GB mem job, 2 CPUs). 6-combination smoke job — 11m00s (mostly ESM-C load + embedding-cache build time on 2 CPUs; training itself <1s per variant at this row count).

## Verification

Split invariants (from `split_train_val()`/`verify_split()`, `--label=full`, printed at run time):
```
--- verify_split (full) ---
  rows: train=377924, val=41992, test=52424
  positive rate: train=0.0912, val=0.0912, test=0.0912 (train/val diff=0.0000)
  overlap: train/val=0, val/test=0, train/test=0
```
- Row-count sum: 377,924 + 41,992 = 419,916 = the pre-split clean train count (`EXPECTED_TRAIN_ROWS_CLEAN`) — exact.
- Label balance: train/val positive-rate diff = 0.0000 (well within the 0.01 tolerance asserted in code); test's rate (0.0912) also matches, consistent with test never being touched by any split logic.
- Overlap: zero pairwise row overlap (train/val, val/test, train/test), computed via `pd.util.hash_pandas_object` row hashes over `(protein_a, protein_b, label)` rather than a Python set of tuples/frozensets (memory-lean choice, see Finding #1).
- `data/curated/d1_ppi/test.csv` byte-for-byte unchanged: sha256 `eda8335611462bc768c3f9da8aa4befc1ed8a0a7653589875f0b4636099b117a` — identical to the hash recorded in `runs/phase2-m1-d1-pipeline.md` before this session's edits.
- All 6 train x {mean, attn, lora} + eval combinations: exit 0. Per-epoch `train_loss=...  val_loss=...  val_auroc=...` printed every epoch for mean/attn/lora. `train_loss` and `val_loss` both monotonically decreased across all 5 epochs for mean and attn (0.72→0.52 train / 0.68→0.54 val for mean; 0.68→0.46 train / 0.64→0.50 val for attn). `val_auroc` was flat (0.2222) for mean/attn — expected artifact of the 10-row smoke val set having only ~2 positives, not a real generalization signal (same caveat `evaluate.py` already applies to its own smoke-scale outputs). LoRA's val_auroc fluctuated (0.42→0.25→0.29→0.42→0.58) on the tiny 15/10-row synthetic set — also not meaningful at this scale, just confirms the loop executes and returns finite numbers.

## Findings

1. **This node's compute allocation is far tighter than assumed, and it's job-wide, not per-process.** `model.py`'s existing docstring described a "hard, non-raisable ~2GB per-process RSS ulimit" (discovered while building M1). Investigating a same-day OOM (exit 137) on plain-pandas code (no model, no torch) that had previously run clean, found: it's actually a **cgroup v2 memory limit on the entire interactive OnDemand Jupyter SLURM job** (`--mem=2G` at submission), shared across every process resident in that job — including this agent's own harness process(es), the Jupyter server, and any new subprocess I spawn. Baseline usage from resident processes was already ~800-840MB, leaving very little headroom for new work; the *original* (pre-val-split) `curate()` also came within ~40MB of the ceiling on a lucky run. Rather than fight this by shrinking every allocation in `data_prep.py`/training scripts, the correct and much simpler fix (Article 4 — KISS) was to submit the actual work as a separate `sbatch` job (`--mem=8G`, partition `common`, ~10-20 min walltime) — decoupled from the interactive session's shared cgroup. This is a normal, low-risk CPU batch submission (no GPU, no human-approval gate per `CLAUDE.md` — that's specific to GPU steps like 8a), not a scope change. All real work in this run-note (`data_prep.py`'s full run, all 6 smoke combinations) was executed this way and completed cleanly with several GB of headroom to spare (peak RSS 150MB for data_prep, 4.3GB for the 6-combination training/eval job). **Flag for future sessions:** don't run non-trivial Phase 2 CPU work directly in the interactive node — submit via `sbatch` first.
2. Also switched `verify_split()`'s row-overlap check from a Python `set` of `(protein_a, protein_b, label)` tuples/frozensets to `pd.util.hash_pandas_object(...).to_numpy()` + `np.intersect1d` — much lower peak memory at D1's ~420K-row scale (numpy arrays of hashes vs. Python object sets), motivated directly by Finding #1. Row hashes are not literally collision-proof, but this is a diagnostic invariant check on top of already-exact dedup logic, not the dedup itself.
3. M3 (LoRA) smoke-testing still hits the same OOM-on-full-length-sequences limitation flagged in the prior step-6 run (`dax-state/journal.md` 2026-07-10 "M3 CPU-smoke finding") — confirmed again, not a new issue. Built a small reusable helper, `src/spikes/phase2/make_synthetic_short_seqs.py`, to generate a tiny synthetic 20-35aa train/val/test set (`data/intermediate/d1_ppi_smoke_lora_short/`) so `train_lora.py`'s logic (including the new validation loop) can be smoke-tested on CPU without hitting that ceiling. This is a **known, accepted limitation** — full-scale/full-length M3 validation only happens on the eventual GPU node (step 8a).
4. Factored `safe_auroc_auprc()` out of `evaluate.py` into `model.py` (shared module already imported by all 3 scripts) so the new per-epoch validation loops in `train_frozen.py`/`train_lora.py` reuse the same AUROC/AUPRC helper `evaluate.py` uses for final held-out reporting, rather than re-deriving it 3 times.
5. M1/M2's val forward pass reuses the same one-time cache as training (embedding_matrix for mean, hidden_list + `batch_pooled_attn` for attn) — cheap, since the backbone is frozen either way and val's unique proteins are already included in the cache (built over train+val+test combined, not train+test as before). M3 has no cache; its val pass (`evaluate_lora`) is structurally identical to its train pass but wrapped in `@torch.no_grad()` with `clf.eval()`/`clf.train()` toggled around it.

## Provenance

- Repo SHA before this work: `bd882effa26af037a7ab77cdd4c155ae406c7c23`.
- Changed files (sha256 at time of this run): `src/spikes/phase2/data_prep.py` `90d404ef526f13b5c6ffae8db161165afcc35be9874f24487df4a9c9aede54f3`; `model.py` `6f1c3d19add2b34430cdba9a650947b8ea66d8b56e9147c8710aeded2dfc23aa`; `train_frozen.py` `a6c0f340bcf4c32165f562dbe16b3aa7b6d3ec38da649db03fec9f03671fd902`; `train_lora.py` `b2db2cbf2fff68b9f6e3df00c7499770f471580c541b625ed9549570deda353b`; `evaluate.py` `c0baa3a30c7a2074e46b86998fe66c3bf5a0d48bf6323e94ddf99bc006b4790a`; `make_synthetic_short_seqs.py` (new) `9ded4d9cdd336862d3af77cbb7e0d35452a0428d84f0bceb039bfdfecfbfe158`.
- Output data (sha256): `data/curated/d1_ppi/train.csv` `f61364d427649aecbbff31767f1b63ccc973c66f5e1449e4877339d2a627ecdb`; `val.csv` `adb7cd15a74084aca10fe7cc8676b01128253129c3cdf9bc2a2068f28ff9e4e5`; `test.csv` `eda8335611462bc768c3f9da8aa4befc1ed8a0a7653589875f0b4636099b117a` (unchanged from prior).
- Relevant journal rows: 2026-07-10 (this session, appended after this note). Relevant decision: `dax-state/decisions.md` 2026-07-10 "Val-split source, cross-species scope, and D4-as-objective framing" entry (90/10 split ratio confirmed there, superseding the plan's earlier "proposed 85/15" placeholder).
