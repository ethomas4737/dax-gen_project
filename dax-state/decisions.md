# Autonomous decisions

## Current state
**Last updated:** 2026-07-10
**Load-bearing as of this date:** The ESM-C checkpoint loader workaround (2026-07-09) remains load-bearing for Phase 2. The 2026-07-10 val-split/D4-objective entry is now also load-bearing — it reopens steps 1 and 6 in `plan-phase2.md` and sets D4 as the headline eval metric. Steps 1c and 6 are now closed (done) per this session's work; the val split is 90/10 (confirmed, not 85/15).
**What's new since last update:** Added the val-split-source / cross-species-scope / D4-as-objective decision (2026-07-10). Added the sbatch-vs-interactive-session memory-constraint decision (2026-07-10, same day) made while implementing step 1c.

Append-only. Log material decisions made without human consultation: architectural choices, tradeoffs, deviations from plan. If a prior decision is later reversed, append a new entry — do not edit.

Format per entry: date, context, decision, rationale, reversibility (easy / medium / hard).

---

<!-- First decision entry goes here. Template:

### YYYY-MM-DD — <short title>

**Context.** <what triggered the decision>

**Decision.** <what was decided>

**Rationale.** <why this option, what alternatives considered>

**Reversibility:** easy | medium | hard. <one-line explanation>

**Surface to human.** <where this is being surfaced (next session, in PR, in a follow-up message)>

-->

### 2026-07-09 — ESM-C checkpoint loader workaround

**Context.** Building the M1-on-D1 pipeline (`src/spikes/phase2/model.py`), `ESMC.from_pretrained()`'s stock loader (via `huggingface_hub.load_torch_model`, v0.36.2) raised `ValueError` on this DCC login node — it doesn't recognize the package's single-file `.pth` checkpoint layout, and separately the node enforces a hard, non-raisable 2GB per-process RSS ulimit that the stock loader's full-materialization-in-RAM approach exceeds regardless.

**Decision.** Load the checkpoint manually: instantiate the model under `accelerate.init_empty_weights()`, then `torch.load(ckpt_path, mmap=True, weights_only=True)` + `model.load_state_dict(sd, assign=True)` directly against the cached `.pth` file.

**Rationale.** Verified to produce an identical model (0 missing / 0 unexpected keys against the official `ESMC_300M_202412` architecture spec) while keeping RSS at ~800MB post-load, vs. an OOM-kill (exit 137) via the stock path. No alternative loader was available in `esm` v3.3.0 that both fixes the format issue and respects the RSS cap.

**Reversibility:** easy — isolated to `model.py::load_esmc_300m()`. On the eventual GPU compute node (no host-RSS ulimit), try `ESMC.from_pretrained("esmc_300m", device=...)` first per the run-note's flagged assumption, falling back to this workaround only if it still fails.

**Surface to human.** This entry (backfilled 2026-07-10 during Phase 2 formalization); also documented in `dax-state/runs/phase2-m1-d1-pipeline.md` Finding #1.

### 2026-07-10 — Val-split source, cross-species scope, and D4-as-objective framing

**Context.** Following up on the cross-species-eval discussion, human clarified three things: (1) cross-species PPI (mouse/fly/yeast/worm/ecoli) should be used as an internal held-out test set, never for training — confirms step 1b's existing framing; (2) per-epoch validation monitoring during training should come from a dedicated split, not `human_test` — presented the two concrete options (carve a fresh val split from `human_train` vs. reuse `human_test` directly), human chose carving a fresh split; (3) the real downstream objective is for the trained model to predict RBD PPI — i.e. D4's RBD-ACE2 + antibody-escape axis is the primary/headline success criterion, not a secondary generalization footnote; D1 training and the cross-species eval exist in service of that goal.

**Decision.** (a) Cross-species PPI (step 1b) stays a held-out internal eval axis, never trained on. (b) Carve a dedicated validation split out of `human_train` (proposed default: 85/15 stratified by label, fixed seed) for per-epoch monitoring in `train_frozen.py`/`train_lora.py`; `human_test` stays untouched until final reporting — this reopens step 1 (new val-split sub-step) and step 6 (needs real per-epoch validation-loop code, previously absent by design). (c) D4 is the headline metric for Phase 2's eval report and any model-selection call; D1 test AUROC and cross-species results are supporting evidence, not the primary yardstick.

**Rationale.** Keeps `human_test` single-use (avoids monitoring-induced test leakage — the same class of concern already raised for the ecoli/human dedup work). Aligns eval design and reporting emphasis with the human's actual stated objective (RBD-PPI prediction) rather than treating the D1/D2/D3 model-comparison matrix as an end in itself.

**Reversibility:** easy — isolated to `data_prep.py`'s split logic, the training scripts' validation loop, and `evaluate.py`'s reporting emphasis; no downstream code depends on this framing yet.

**Surface to human.** This entry; also reflected in `spec/spec.md` and `dax-state/plan-phase2.md` updates the same session.

### 2026-07-10 — Run non-trivial Phase 2 CPU work via `sbatch`, not the interactive session

**Context.** Implementing step 1c's val split, a small addition to `data_prep.py::curate()` (a memory-lean overlap check + a stratified split) repeatedly OOM-killed (exit 137) in this session's interactive OnDemand Jupyter node, even though the *unmodified* `curate()` had run clean before. Root-caused: the interactive job enforces a **job-wide** (not per-process) ~2GB cgroup v2 memory cap shared across every resident process in that SLURM job — Jupyter server, this agent's own harness process(es), and any new subprocess — and baseline usage from those resident processes alone (~800-840MB) already left very little headroom; the original `curate()` was already running within ~40MB of the ceiling.

**Decision.** (1) Made the val-split overlap check memory-lean (`pd.util.hash_pandas_object` + `np.intersect1d` instead of Python sets of tuples/frozensets). (2) For the actual production runs (full `data_prep.py` curation, and the 6-combination train+eval smoke test), submitted them as separate `sbatch` jobs (partition `common`, `--mem=8G`, ~10-20 min walltime) rather than running directly in the interactive session.

**Rationale.** A modest CPU-only batch submission is a normal, low-risk executor action — distinct from the GPU allocation steps (8a) that require human approval per `CLAUDE.md`. It sidesteps a structural memory constraint of the interactive session (shared across unrelated processes I don't control) rather than trying to shrink an already-lean pipeline further. Both jobs completed cleanly with several GB of headroom to spare.

**Reversibility:** easy — isolated to how this session invoked the scripts; the scripts themselves are unchanged in their expected calling convention (`python data_prep.py`, `python train_frozen.py ...`) and would run identically under `srun`/`sbatch`/direct-python on a less memory-constrained node.

**Surface to human.** This entry; also documented in `dax-state/runs/phase2-1c-6-validation-split.md` Finding #1 and `dax-state/journal.md`'s 2026-07-10 "Memory-constraint finding" note.
