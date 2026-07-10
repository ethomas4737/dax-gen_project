# Autonomous decisions

## Current state
**Last updated:** 2026-07-10
**Load-bearing as of this date:** The ESM-C checkpoint loader workaround (2026-07-09, below) is load-bearing for Phase 2 — anyone rerunning `src/spikes/phase2/model.py` needs to know the stock loader doesn't work on this login node.
**What's new since last update:** Backfilled the ESM-C loader workaround as the first real autonomous-decision entry, during Phase 2's retroactive formalization.

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
