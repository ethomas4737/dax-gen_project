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
  - Backbone trainability (frozen vs LoRA-wrapped, for M3) and pooling strategy
    (mean vs attention, for M2) are kept as separate, swappable pieces on purpose;
    only the M1 frozen + mean-pool path is implemented/exercised right now.

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
# Pooling (swappable: mean-pool for M1, attention-pool stub for M2)
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
    """Attention-pooling stub for M2. Not implemented / not exercised in this pass --
    kept here only so the `pooling` argument has a second concrete class to swap in
    later without restructuring PairClassifier."""

    def __init__(self, d_model: int):
        super().__init__()
        self.d_model = d_model
        raise NotImplementedError(
            "AttnPooling (M2) is a structural stub only -- not implemented in the M1 pass."
        )

    def forward(self, hidden_states: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError


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
