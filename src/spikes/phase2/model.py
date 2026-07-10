"""Phase 2 / D1 model: ESM-C 300M Siamese pair-encoder + swappable pooling + MLP head.

Study code (src/spikes/phase2/) -- not yet promoted.

Architecture (per spec):
  - Backbone: ESM-C 300M (EvolutionaryScale `esm` package), same weights applied to
    seq_a and seq_b separately (Siamese-style, shared backbone).
  - Pooling: mean-pooling over per-residue embeddings (M1). Structured as a swappable
    `Pooling` module so an attention-pooling variant (M2) can be dropped in later
    without touching the rest of the pipeline.
  - Combination: [pooled_a, pooled_b, |pooled_a - pooled_b|, pooled_a * pooled_b]
    (4 * d_model input to the head).
  - Head: one hidden layer MLP (hidden_dim=256, ReLU, dropout=0.1) -> 1 logit.
    BCEWithLogitsLoss.
  - M1: backbone fully frozen (requires_grad=False on all backbone params, forward
    pass wrapped in torch.no_grad()). Only the head is trained -- pooling is
    non-parametric mean-pooling, so there is nothing to train there.
  - M3: backbone LoRA-wrapped via HuggingFace `peft` (see `apply_lora()` below) --
    base weights frozen, small rank-r adapter matrices trainable on the attention
    projections. `PairClassifier(backbone_trainable=True)` does NOT blanket-freeze
    the backbone (unlike M1/M2); it trusts peft's own requires_grad wiring (base
    frozen, lora_A/lora_B trainable), and encode()/forward() skip the no_grad()/
    detach() calls so gradients flow through the adapters during training.
  - Backbone trainability (frozen vs LoRA-wrapped, for M3) and pooling strategy
    (mean vs attention, for M2) are kept as separate, swappable pieces on purpose.
    All three variants are now implemented: M1 (frozen + mean-pool), M2 (frozen +
    attention-pool, AttnPooling), M3 (LoRA-wrapped + either pooling).
    Note: M2's attention-pooling is trainable, so M1's embed-once-cache-forever
    trick (build_embedding_cache / cache_to_matrix, below) does not carry over to
    M2 as-is -- see AttnPooling's docstring. It does not apply to M3 at all, since
    a trainable backbone means per-protein embeddings change every step.

Known environment workaround: this DCC login node enforces a 2GB per-process RSS
ulimit. `esm`'s stock `ESMC.from_pretrained(...)` loader (via
huggingface_hub.load_torch_model) materializes the full checkpoint into RAM before
assigning it, which exceeds that limit even though the model itself only needs
~1.3GB. Loading the same checkpoint file with `torch.load(..., mmap=True)` and
`model.load_state_dict(sd, assign=True)` keeps resident memory low (~800MB after
load) by mapping the weights from disk instead of copying them, and produces an
identical model (0 missing / 0 unexpected keys). See `load_esmc_300m()` below.
This workaround is only needed on memory-constrained CPU nodes; on a GPU node
`ESMC.from_pretrained("esmc_300m", device=...)` should be tried first and this
fallback used only if it still fails.
"""
from pathlib import Path

import torch
import torch.nn as nn

ESMC_300M_HF_REPO = "biohub/esmc-300m-2024-12"
D_MODEL_300M = 960


def _find_cached_esmc_300m_checkpoint():
    """Locate the esmc_300m_2024_12_v0.pth file in the local HF cache (already
    downloaded via `ESMC.from_pretrained` once, see run-note for provenance)."""
    from huggingface_hub import scan_cache_dir

    cache = scan_cache_dir()
    for repo in cache.repos:
        if repo.repo_id == ESMC_300M_HF_REPO:
            for rev in repo.revisions:
                for f in rev.files:
                    if f.file_path.name.endswith(".pth"):
                        return f.file_path
    raise FileNotFoundError(
        f"No cached checkpoint found for {ESMC_300M_HF_REPO}. Run "
        "`ESMC.from_pretrained('esmc_300m')` once (with internet access) to populate "
        "the HuggingFace cache, then retry."
    )


def load_esmc_300m(device="cpu", use_flash_attn=False):
    """Load ESM-C 300M, working around the mmap-vs-ulimit issue described above.

    Returns (model, tokenizer). Model is in eval() mode; caller is responsible for
    freezing params / wrapping calls in no_grad() as appropriate for the variant
    (M1 always freezes; M3 will wrap with LoRA on top of this loader's output).
    """
    from accelerate import init_empty_weights
    from esm.models.esmc import ESMC
    from esm.tokenization import get_esmc_model_tokenizers

    tokenizer = get_esmc_model_tokenizers()
    ckpt_path = _find_cached_esmc_300m_checkpoint()

    with init_empty_weights():
        model = ESMC(
            d_model=D_MODEL_300M,
            n_heads=15,
            n_layers=30,
            tokenizer=tokenizer,
            use_flash_attn=use_flash_attn,
        ).eval()

    state_dict = torch.load(ckpt_path, map_location="cpu", mmap=True, weights_only=True)
    result = model.load_state_dict(state_dict, assign=True, strict=False)
    if result.missing_keys or result.unexpected_keys:
        raise RuntimeError(
            f"ESM-C 300M checkpoint did not load cleanly: "
            f"missing={result.missing_keys}, unexpected={result.unexpected_keys}"
        )
    model = model.to(torch.float32).to(device)
    return model, tokenizer


# --------------------------------------------------------------------------
# LoRA wrapping (M3): frozen base backbone + small trainable rank-r adapters.
# --------------------------------------------------------------------------

LORA_TARGET_MODULES = ("layernorm_qkv.1", "out_proj")
"""ESM-C's attention uses a *fused* QKV projection (one Linear producing q/k/v
together, named `attn.layernorm_qkv.1` -- index .1 of a [LayerNorm, Linear]
Sequential) plus a separate `attn.out_proj`, not the separate q_proj/k_proj/
v_proj/o_proj names common in some other transformer implementations. Verified
(2026-07-10, CPU) these two suffixes match exactly the 60 attention-projection
Linears across all 30 blocks and nothing else (checked against the model's other
non-block Linears, `sequence_head.{0,3}`, which don't match either suffix) --
`peft.LoraConfig(target_modules=LORA_TARGET_MODULES)` attaches 120 LoRA tensors
(2 per target module: lora_A + lora_B), e.g. 1,382,400 trainable params at r=8
out of 334,379,584 total. Forward+backward verified end-to-end: LoRA params
receive gradients, base backbone params do not.
"""


def apply_lora(backbone, r: int = 8, lora_alpha: int = 16, lora_dropout: float = 0.0):
    """Wrap a loaded ESM-C backbone with LoRA adapters on the attention projections
    (M3). Returns the peft-wrapped model: base weights frozen, only lora_A/lora_B
    matrices trainable. Caller should pass this to PairClassifier(..., backbone_trainable=True)
    so the base-freeze/no_grad logic there is skipped in favor of peft's own wiring.
    """
    from peft import LoraConfig, get_peft_model

    lora_cfg = LoraConfig(
        r=r, lora_alpha=lora_alpha, lora_dropout=lora_dropout, bias="none",
        target_modules=list(LORA_TARGET_MODULES),
    )
    return get_peft_model(backbone, lora_cfg)


# --------------------------------------------------------------------------
# Pooling (swappable: mean-pool for M1, attention-pool for M2)
# --------------------------------------------------------------------------

class MeanPooling(nn.Module):
    """Non-parametric mean-pooling over valid (non-pad) residue positions.
    This is M1's pooling strategy -- no learned parameters."""

    def forward(self, hidden_states: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        # hidden_states: [B, L, D], mask: [B, L] boolean, True = valid residue
        mask = mask.unsqueeze(-1).to(hidden_states.dtype)  # [B, L, 1]
        summed = (hidden_states * mask).sum(dim=1)  # [B, D]
        counts = mask.sum(dim=1).clamp(min=1e-6)  # [B, 1]
        return summed / counts


class AttnPooling(nn.Module):
    """Learned single-query attention-pooling over valid (non-pad) residue positions (M2).

    A single Linear(d_model, 1) scores each residue position; padding positions are
    masked to -inf before softmax so they contribute zero weight. Unlike M1's
    MeanPooling, this has trainable parameters (`self.score`) -- callers must include
    `pooling.parameters()` in the optimizer alongside the head's, and M1's
    embed-once-cache-forever trick (build_embedding_cache / cache_to_matrix) does NOT
    apply as-is to M2: since pooling itself is trained, a cached *pooled* vector goes
    stale as soon as `self.score`'s weights update. M2's cache should instead hold
    each unique protein's per-residue backbone hidden states (the frozen backbone's
    output, before pooling) and apply this module fresh every step -- see
    dax-state/plan-phase2.md step 6.
    """

    def __init__(self, d_model: int):
        super().__init__()
        self.score = nn.Linear(d_model, 1)

    def forward(self, hidden_states: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        # hidden_states: [B, L, D], mask: [B, L] boolean, True = valid residue
        scores = self.score(hidden_states).squeeze(-1)  # [B, L]
        scores = scores.masked_fill(~mask, float("-inf"))
        weights = torch.softmax(scores, dim=1).unsqueeze(-1)  # [B, L, 1]
        return (hidden_states * weights).sum(dim=1)  # [B, D]


def get_pooling(name: str, d_model: int = D_MODEL_300M) -> nn.Module:
    if name == "mean":
        return MeanPooling()
    if name == "attn":
        return AttnPooling(d_model)
    raise ValueError(f"Unknown pooling strategy: {name}")


# --------------------------------------------------------------------------
# Head
# --------------------------------------------------------------------------

class PairHead(nn.Module):
    """MLP head over the 4-way combination of pooled_a / pooled_b.
    Input dim = 4 * d_model (pooled_a, pooled_b, |pooled_a - pooled_b|, pooled_a * pooled_b)."""

    def __init__(self, d_model: int = D_MODEL_300M, hidden_dim: int = 256, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(4 * d_model, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, combined: torch.Tensor) -> torch.Tensor:
        return self.net(combined).squeeze(-1)  # [B] logits


def combine_pair(pooled_a: torch.Tensor, pooled_b: torch.Tensor) -> torch.Tensor:
    return torch.cat(
        [pooled_a, pooled_b, (pooled_a - pooled_b).abs(), pooled_a * pooled_b], dim=-1
    )


# --------------------------------------------------------------------------
# Full Siamese pair classifier (backbone + pooling + head)
# --------------------------------------------------------------------------

class PairClassifier(nn.Module):
    """Siamese pair classifier: same ESM-C backbone applied to seq_a and seq_b,
    pooled (swappable strategy), combined, and scored by an MLP head.

    `backbone_trainable` controls M1 (False, frozen) vs future M3 (True, LoRA-wrapped
    backbone). Only `backbone_trainable=False` (M1) is exercised right now.
    """

    def __init__(self, backbone, tokenizer, pooling: nn.Module, head: nn.Module,
                 backbone_trainable: bool = False):
        super().__init__()
        self.backbone = backbone
        self.tokenizer = tokenizer
        self.pooling = pooling
        self.head = head
        self.backbone_trainable = backbone_trainable
        if not backbone_trainable:
            for p in self.backbone.parameters():
                p.requires_grad_(False)
            self.backbone.eval()

    def encode(self, token_ids: torch.Tensor) -> torch.Tensor:
        """Run the backbone + pooling on one batch of tokenized sequences.
        token_ids: [B, L] padded token ids. Returns pooled embeddings [B, D]."""
        mask = token_ids != self.tokenizer.pad_token_id
        if self.backbone_trainable:
            out = self.backbone(sequence_tokens=token_ids)
        else:
            with torch.no_grad():
                out = self.backbone(sequence_tokens=token_ids)
        return self.pooling(out.embeddings, mask)

    def forward(self, ids_a: torch.Tensor, ids_b: torch.Tensor) -> torch.Tensor:
        pooled_a = self.encode(ids_a)
        pooled_b = self.encode(ids_b)
        if not self.backbone_trainable:
            pooled_a = pooled_a.detach()
            pooled_b = pooled_b.detach()
        combined = combine_pair(pooled_a, pooled_b)
        return self.head(combined)  # [B] logits


# --------------------------------------------------------------------------
# Embedding cache (M1-specific efficiency: frozen backbone => embed each unique
# protein sequence exactly once, reuse across every pair and every epoch, instead
# of recomputing seq_a/seq_b embeddings per pair per epoch. Mathematically
# identical to running PairClassifier end-to-end every step, since the backbone
# and mean-pooling are both fixed (no dropout, no gradient) for M1.
# --------------------------------------------------------------------------

def build_embedding_cache(backbone, tokenizer, pooling, seqs: dict, device="cpu",
                           batch_size: int = 8, verbose: bool = True) -> dict:
    """seqs: {protein_id: sequence_str}. Returns {protein_id: torch.Tensor [D]} (CPU tensors)."""
    ids = list(seqs.keys())
    cache = {}
    backbone.eval()
    pad_id = tokenizer.pad_token_id
    with torch.no_grad():
        for start in range(0, len(ids), batch_size):
            batch_ids = ids[start:start + batch_size]
            batch_seqs = [seqs[i] for i in batch_ids]
            token_lists = [tokenizer.encode(s) for s in batch_seqs]
            max_len = max(len(t) for t in token_lists)
            padded = torch.full((len(token_lists), max_len), pad_id, dtype=torch.long)
            for i, t in enumerate(token_lists):
                padded[i, :len(t)] = torch.tensor(t, dtype=torch.long)
            padded = padded.to(device)
            mask = padded != pad_id
            out = backbone(sequence_tokens=padded)
            pooled = pooling(out.embeddings, mask)  # [B, D]
            for i, pid in enumerate(batch_ids):
                cache[pid] = pooled[i].detach().cpu()
            if verbose and (start // batch_size) % 10 == 0:
                print(f"  embedded {min(start + batch_size, len(ids))}/{len(ids)} unique sequences")
    return cache


def cache_to_matrix(cache: dict):
    """Convert a {protein_id: [D] tensor} cache into a single stacked matrix + an
    id->row-index map. This is the form the real (~420K-row) training run should use:
    a (n_unique_proteins, D) matrix (~15.7K x 960 x 4 bytes ~= 60MB for D1) rather than
    a Python dict of tensors, so pair lookups are cheap tensor indexing operations."""
    ids = list(cache.keys())
    id_to_idx = {pid: i for i, pid in enumerate(ids)}
    matrix = torch.stack([cache[pid] for pid in ids])  # [n_unique, D]
    return matrix, id_to_idx


class PairIndexDataset(torch.utils.data.Dataset):
    """Index-only dataset over (protein_a, protein_b, label) pairs -- does NOT
    materialize per-pair combined feature vectors. At D1's real scale (~420K train
    pairs), precomputing the full (n_pairs, 4*d_model) combined-feature matrix would
    be ~6.4GB (420K * 3840 * 4 bytes); this dataset instead stores two int64 index
    arrays + a label array (a few MB total) and looks up rows from the shared
    (n_unique_proteins, D) embedding matrix on the fly per batch (see `collate` /
    `combine_pair` -- called once per batch, not precomputed for the whole dataset).
    """

    def __init__(self, protein_a_ids, protein_b_ids, labels, id_to_idx):
        self.idx_a = torch.tensor([id_to_idx[p] for p in protein_a_ids], dtype=torch.long)
        self.idx_b = torch.tensor([id_to_idx[p] for p in protein_b_ids], dtype=torch.long)
        self.labels = torch.tensor(list(labels), dtype=torch.float32)

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, i):
        return self.idx_a[i], self.idx_b[i], self.labels[i]


def batch_features(idx_a: torch.Tensor, idx_b: torch.Tensor, embedding_matrix: torch.Tensor) -> torch.Tensor:
    """Look up + combine embeddings for one batch of pair indices. embedding_matrix:
    [n_unique, D] (shared, not copied). Returns [B, 4*D] combined features for this
    batch only -- the memory-efficient counterpart to precomputing combine_pair for
    every pair up front."""
    pooled_a = embedding_matrix[idx_a]
    pooled_b = embedding_matrix[idx_b]
    return combine_pair(pooled_a, pooled_b)
