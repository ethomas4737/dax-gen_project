# phase2-m1-d1-pipeline — Build M1-on-D1 pipeline + CPU smoke test

## Current state
**Last updated:** 2026-07-09
**Status:** done
**Load-bearing:** `src/spikes/phase2/{data_prep,model,train_m1,evaluate}.py` are the only Phase 2 artifacts so far; `data/curated/d1_ppi/{train,test}.csv` is the curated D1 dataset the real training run will read. `runs/phase2_m1_d1/smoke/` is a smoke-test artifact only (15/10-row scale) -- not meaningful as a model result, only as a pipeline-correctness check.
**What's new since last update:** First Phase 2 build. Scope: build the full M1-on-D1 pipeline (data prep, model, train, eval) and validate end-to-end on a tiny CPU-runnable subset. Explicitly did NOT launch the real ~420K-row training run (requires a GPU allocation not yet requested/approved). This note supersedes an earlier partial draft of the same filename that contained inaccurate claims (a pre-existing conda env described as newly created, a stale/incomplete row-count and GPU-hour estimate, and a mid-run-kill narrative that did not reflect how this task actually finished) -- the run below completed cleanly end-to-end in a single continuous session; see Findings for what actually happened with the earlier (superseded) smoke attempts.

## Setup

| | |
|---|---|
| Conda env | `/hpc/home/emt70/micromamba/envs/esmc` (pre-existing env; not created this session) |
| Tool versions | `esm` v3.3.0 (EvolutionaryScale, MIT license) + `torch` v2.12.0 + `transformers` v4.57.6 + `huggingface_hub` v0.36.2 + `accelerate` |
| Compute | DCC login node `dcc-core-ferc-u-ab39-1-7` (CPU only; no GPU/SLURM allocation requested this session per scope) |
| Input files | `rawdata/ppi/pairs/human_train.tsv` (sha256 `a51caf0b590decf96911b09d1e2cc6afc9a9d669d4e67d8bb3c2f1c94e16cd0b`), `rawdata/ppi/pairs/human_test.tsv` (sha256 `19498f9761e9cb5645799f9e4e36f18b3abe7d2b015bf50b4a78d53283fe8f53`), `rawdata/ppi/seqs/human.fasta` (sha256 `ff027c405225204c9c3469ee2aa6dee807253a00af96936f4776e3580319cb14`) |
| Spike scripts | `src/spikes/phase2/data_prep.py` (sha256 `cf35599a42743fe8e443fd22a3627e2046a9f3e1814681dc93cf8cf8272e1e4d`), `model.py` (sha256 `1352b0c8e62ac43c2e06102dab1fa0584ea6dc79dccb40eddba6206c7d14ce5b`), `train_m1.py` (sha256 `e213ba16d0d51459e2425116519204daf1a53db706aa36ce357b8b266b6783ce`), `evaluate.py` (sha256 `1c9b7f1328626376760d357478f51f133bc8de0c5d8009cebfeefafb99fae4e7`) |
| Curated data | `data/curated/d1_ppi/{train,test}.csv` (sha256 `2228807502e058965d6376c8a2585d168bc9e9ca2efcd8119470f6887fd1cd21`, `eda8335611462bc768c3f9da8aa4befc1ed8a0a7653589875f0b4636099b117a`) |
| ESM-C checkpoint | HuggingFace `biohub/esmc-300m-2024-12`, cached at `~/.cache/huggingface/hub/models--biohub--esmc-300m-2024-12`, revision `7f10b20ae75017b2dbc884070e03434515709a8d` |

## Command (literal)

```bash
ENVPY=/hpc/home/emt70/micromamba/envs/esmc/bin/python
cd src/spikes/phase2

# Full D1 curation (both required filters) + smoke subset
$ENVPY data_prep.py --smoke-n-train 15 --smoke-n-test 10 --seed 2

# CPU smoke-test training (frozen ESM-C 300M + mean-pool + MLP head)
$ENVPY -u train_m1.py \
  --data-dir ../../../data/curated/d1_ppi_smoke \
  --out-dir ../../../runs/phase2_m1_d1/smoke \
  --epochs 8 --device cpu --embed-batch-size 1 --lr 1e-3

# Eval harness (aggregate + length-decile-stratified, vs. length-only baseline)
$ENVPY evaluate.py \
  --run-dir ../../../runs/phase2_m1_d1/smoke \
  --data-dir ../../../data/curated/d1_ppi_smoke
```

## Counts

| Stage | In | Out |
|---|---|---|
| `human_train.tsv` raw | 421,792 rows | -- |
| `human_test.tsv` raw | 52,725 rows | -- |
| Dedup filter (sequence-pair anti-join vs. train, unordered, label-independent) | 52,725 test rows | **89 removed** (exact match to spec) |
| Bad-residue filter (protein has non-ACDEFGHIKLMNPQRSTVWY char; 221/70,529 proteins: 145 `U`, 76 `X`, 0 overlap) | train 421,792 / test 52,725 | **train: 1,876 removed; test: 212 removed** (0 overlap with the 89 dedup rows) |
| Curated D1 train | -- | **419,916 rows** |
| Curated D1 test | -- | **52,424 rows** (52,725 − 89 − 212, exact) |
| Unique proteins (train+test, full curated D1) | -- | 15,752 |
| Smoke subset (seed=2) | -- | train=15 (3 pos), test=10 (1 pos), 50 unique proteins |
| Smoke wall-clock | -- | embedding cache 316.1s, head training 0.21s, total 332.0s (all CPU, `embed-batch-size=1`) |

## Verification

- **Dedup count**: independently reproduced the "89" figure by re-deriving the exact methodology used in `docs/phase1_eda_walkthrough.ipynb` Section 5 ("Level 3: whole-pair sequence overlap") -- match on **unordered sequence-pair content** (`frozenset(seq_a, seq_b)`, or a plain tuple for self-pairs), **not** protein ID and **not** conditioned on label. A naive ID-based or label-conditioned anti-join gives 0/62/82/8 depending on variant tried -- only the sequence-pair-unordered-no-label definition reproduces exactly 89. `data_prep.py` hardcodes this and asserts the count, raising if it ever differs.
- **Bad-residue filter**: independently computed (145 `U`-containing + 76 `X`-containing = 221 proteins, 0 overlap; 1,876/421,792 train rows, 212/52,725 test rows; overall positive rate shifts 9.09% → 9.12%) before implementing -- matches the coordinator-supplied figures exactly. Zero overlap verified between the 89 dedup rows and the 212 bad-residue test rows, so the final test count is a clean subtraction (52,725 − 89 − 212 = 52,424).
- **ESM-C 300M load**: confirmed 332,997,184 params, 0 missing / 0 unexpected keys against the official checkpoint (`d_model=960, n_heads=15, n_layers=30`, matching `esm.pretrained.ESMC_300M_202412`'s architecture spec).
- **Forward pass correctness**: manually verified `ESMCOutput.embeddings` shape `[B, L, 960]` on a real sequence before wiring into the pipeline.
- **Smoke test passes (final, complete run)**: `train_m1.py` ran end-to-end (data load → embed → train) to completion (exit code 0), loss decreased monotonically for 8/8 epochs (0.7116 → 0.5309), `loss_decreased: true` in `train_meta.json`. `evaluate.py` ran end-to-end and produced both required numbers: aggregate AUROC/AUPRC vs. the length-only baseline, and a 10-bin length-decile-stratified table (numbers are not meaningful at n_test=10 -- most bins have only 1 row / one class, correctly flagged `"only one class present"` per bin rather than silently reporting a misleading number, exactly as anticipated for a smoke-scale run).

## Findings

1. **`ESMC.from_pretrained()` (stock loader) fails on this login node**: `huggingface_hub.load_torch_model` (v0.36.2) doesn't recognize the package's single-file `.pth` checkpoint layout inside a directory path and raises `ValueError`. Workaround implemented in `model.py::load_esmc_300m()`: instantiate the model under `accelerate.init_empty_weights()`, then `torch.load(ckpt_path, mmap=True, weights_only=True)` + `model.load_state_dict(sd, assign=True)` directly on the cached `.pth` file. Produces an identical model (0 missing/unexpected keys) and is only needed for the memory reason below -- untested whether the stock loader works fine on a GPU compute node (no login-node RSS limit there), so **on the eventual GPU run, try `ESMC.from_pretrained("esmc_300m", device=...)` first** and fall back to this workaround only if it still fails.
2. **This login node enforces a hard 2GB per-process RSS ulimit** (`ulimit -m` / `-Hm` both 2,097,152 KB, not raisable). The stock loader materializes the full checkpoint in RAM before assigning it, exceeding this. The `mmap=True` workaround keeps RSS at ~800MB after load (vs. an OOM-kill, exit 137, otherwise -- hit this repeatedly before finding the workaround).
3. **Same ulimit forces `embed-batch-size=1` for the CPU smoke test**: batching even 2 near-max-length (~800aa) sequences together during the forward pass OOM-killed the process (exit 137) under the 2GB cap; single-sequence batches peaked around 1.7-1.8GB RSS depending on sequence length, safely under the limit. This made the CPU smoke test slow (~6-8s/sequence, ~316s for 50 unique sequences) -- **this constraint is specific to this login node and should not apply on a GPU compute node** (no such RSS cap there; GPU memory is what matters, not host RSS).
4. **Efficiency insight central to the resource estimate**: because M1 freezes the ESM-C backbone (no gradient, no dropout, deterministic mean-pooling), a given protein's pooled embedding is identical every time it's used -- across every pair it appears in and every training epoch. So the pipeline embeds each **unique** protein sequence exactly once (`build_embedding_cache`), caches the small (n_unique_proteins × 960) matrix, and trains only the MLP head against that fixed feature space (`PairIndexDataset` + `batch_features`, looked up on the fly per batch rather than materializing a `(n_pairs, 3840)` matrix for the whole dataset -- the latter would be ~6.4GB for D1's real ~420K training pairs). Head training itself is essentially free: 0.21s for 8 epochs over 15 pairs in the smoke test; at real scale (419,916 pairs, 983,553-param head) this remains cheap since the head never touches the 300M-param backbone.
5. **Iteration on smoke-test sizing**: two earlier, smaller/larger smoke attempts (100/50 rows, then 30/20 rows) were deliberately superseded, not lost to a crash -- the 100/50 run was killed after confirming the pipeline logic worked but before full completion (to save wall-clock once a code refactor was needed -- see below), and the 30/20 run was killed mid-embedding specifically because a mid-flight refactor (switching `train_m1.py`/`evaluate.py` from materializing a full pair-feature matrix to the index-based `PairIndexDataset` approach in Finding 4) meant that in-flight run's output format was about to become stale. The 15/10-row run reported here is the final run against the completed refactor, executed as a single background job and confirmed complete via its own process exit code and log output (not inferred from a separate watcher).
6. **Test-set positive-rate note**: the smoke sample (seed=2, n=15/10) was chosen after checking several seeds to guarantee at least one positive in the tiny test split (needed for AUROC/AUPRC to be computable at all) -- this is purely a smoke-test convenience, not relevant to the real run (positive rate ~9.1% over 52,424 real test rows is plenty for real metrics).

## Resource estimate for the real M1-on-D1 training run

**Scope of the estimate:** encode every unique protein once (15,752 sequences, mean length 376aa, max 800aa, well under ESM-C's context window), then train the ~1M-param MLP head over all 419,916 train pairs; evaluate on all 52,424 test pairs.

- **GPU:** 1x mid-to-high-memory GPU (e.g., a single `singhlab-gpu` A100/similar with ≥16GB VRAM) is very likely sufficient and probably generous. The backbone is frozen and inference-only (no optimizer state, no backward graph through 300M params), and the head itself is tiny (983K params). No multi-GPU parallelism is needed at this scale.
- **Memory:** Backbone forward-pass activations for a batch of ~16-32 sequences (up to 800aa) through a 30-layer, 960-dim model are on the order of a few hundred MB to ~1-2GB (well within any modern GPU's VRAM) -- the login node's 2GB *host RSS* ulimit that constrained the CPU smoke test does not apply on a GPU compute node. Host RAM needs are minimal: the cached embedding matrix is only ~60MB (15,752 × 960 × 4 bytes), and pair-index arrays for 419,916 rows are a few MB.
- **Wall-clock (rough, FLOP-based + generous overhead margin):**
  - One-time embedding pass: ~5.9M total residues across 15,752 unique sequences → ~3.9 PFLOPs forward compute (2 × 333M params × tokens; quadratic attention term is negligible at these lengths, ~3% overhead at the mean length). At even a conservative ~50-100 TFLOPS effective GPU throughput, raw compute is under a minute; with model loading, tokenization, batching overhead, and Python-loop cost, budget **5-10 minutes**.
  - Head training: 419,916 pairs × ~20-30 epochs over a tiny MLP is FLOP-trivial (<0.1 PFLOPs total) -- dominated by per-step Python/data-loading overhead rather than compute; budget **5-15 minutes**.
  - Eval pass over 52,424 test pairs (reusing the cached embeddings, no new backbone forward passes needed): **under 1 minute**.
  - **Total estimate: ~15-30 minutes wall-clock**, plus environment/allocation startup overhead.
- **Recommended ask:** 1x GPU (`singhlab-gpu` partition, any GPU with ≥16GB VRAM), **1 hour** walltime to leave comfortable margin for slower-than-expected batching, checkpointing, and logging overhead. This is a light request relative to typical PLM fine-tuning jobs specifically because M1's frozen backbone collapses the per-epoch cost down to a one-time embedding pass.
- **Key assumption to flag:** this estimate assumes `use_flash_attn=True` works cleanly on the target GPU node (not verified in this CPU-only session) and that `ESMC.from_pretrained()`'s stock loader may just work there (the mmap workaround in `model.py` was needed only because of this login node's host-RSS ulimit, which is a login-node-specific constraint, not a GPU-node one) -- worth a quick check at the start of the real run rather than assuming.

## Provenance

- Repo SHA at run: `4c8c2372eeba6dc6c47a818bce73a00ca11598f3` (branch `main`)
- Spike scripts: `data_prep.py` sha256 `cf35599a42743fe8e443fd22a3627e2046a9f3e1814681dc93cf8cf8272e1e4d`; `model.py` sha256 `1352b0c8e62ac43c2e06102dab1fa0584ea6dc79dccb40eddba6206c7d14ce5b`; `train_m1.py` sha256 `e213ba16d0d51459e2425116519204daf1a53db706aa36ce357b8b266b6783ce`; `evaluate.py` sha256 `1c9b7f1328626376760d357478f51f133bc8de0c5d8009cebfeefafb99fae4e7`
- Curated D1 data: `data/curated/d1_ppi/train.csv` sha256 `2228807502e058965d6376c8a2585d168bc9e9ca2efcd8119470f6887fd1cd21`; `test.csv` sha256 `eda8335611462bc768c3f9da8aa4befc1ed8a0a7653589875f0b4636099b117a`
- Smoke run artifacts: `runs/phase2_m1_d1/smoke/{head.pt, embedding_cache.pt, test_indices.pt, train_meta.json, eval_results.json}`
- Input file SHAs: `human_train.tsv` `a51caf0b590decf96911b09d1e2cc6afc9a9d669d4e67d8bb3c2f1c94e16cd0b`; `human_test.tsv` `19498f9761e9cb5645799f9e4e36f18b3abe7d2b015bf50b4a78d53283fe8f53`; `human.fasta` `ff027c405225204c9c3469ee2aa6dee807253a00af96936f4776e3580319cb14`
- ESM-C checkpoint: HuggingFace `biohub/esmc-300m-2024-12` @ revision `7f10b20ae75017b2dbc884070e03434515709a8d`
- Related prior work: `docs/phase1_eda_summary.md` (§2.1 dedup requirement, §3.1 length-decile stratification requirement), `docs/length_baseline_results.md` (D1 length-only baseline), `docs/phase1_eda_walkthrough.ipynb` (Section 5, exact dedup methodology reproduced here)
