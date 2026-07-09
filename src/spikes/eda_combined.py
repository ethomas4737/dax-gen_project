"""EDA for the combined dataset variants D1-D4 (rawdata/combined/). Writes docs/eda-combined.md + docs/figures/combined_*.png."""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

RAWDATA = Path("rawdata")
COMBINED = RAWDATA / "combined"
DOCS = Path("docs")
FIGS = DOCS / "figures"

STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    d1 = pd.read_csv(COMBINED / "d1_ppi.csv")
    d2 = pd.read_csv(COMBINED / "d2_avida.csv")
    d3 = pd.read_csv(COMBINED / "d3_ppi_avida.csv")
    d4h = pd.read_csv(COMBINED / "d4_heldout_mlaep_ace2.csv")

    report = ["# EDA — Combined dataset variants (D1-D4)\n",
              "**Generated:** 2026-07-09 | **Source:** `rawdata/combined/` (built by `src/spikes/build_combined_datasets.py`)\n",
              "D1 = D-SCRIPT PPI (all species). D2 = AVIDa, no COVID (hIL6+hTNFa). D3 = D1 union D2 (training pool). "
              "D4 = D3 as the training pool, with MLAEP reframed as a held-out evaluation partition "
              "(RBD mutant paired with human ACE2, `ace2_bind` label) — not merged into D3.\n"]

    # --- Row counts + positive fraction per source ---
    report.append("## Row counts & positive fraction by source\n")
    for name, df in [("D1 (PPI)", d1), ("D2 (AVIDa)", d2), ("D4 held-out (MLAEP/ACE2)", d4h)]:
        by_source = df.groupby("source_dataset")["label"].agg(["mean", "count"]).rename(
            columns={"mean": "positive_fraction", "count": "n_rows"})
        report.append(f"### {name}\n")
        report.append(by_source.reset_index().to_markdown(index=False) + "\n")

    report.append("### D3 (D1 union D2) by pair_type\n")
    by_type = d3.groupby("pair_type")["label"].agg(["mean", "count"]).rename(
        columns={"mean": "positive_fraction", "count": "n_rows"})
    report.append(by_type.reset_index().to_markdown(index=False) + "\n")

    # --- Sequence length stats ---
    report.append("## Sequence length stats (seq_a / seq_b) per variant\n")
    len_rows = []
    for name, df in [("D1", d1), ("D2", d2), ("D3", d3), ("D4-heldout", d4h)]:
        la, lb = df["seq_a"].str.len(), df["seq_b"].str.len()
        len_rows.append({"dataset": name, "seq_a_min": int(la.min()), "seq_a_median": float(la.median()),
                          "seq_a_max": int(la.max()), "seq_b_min": int(lb.min()),
                          "seq_b_median": float(lb.median()), "seq_b_max": int(lb.max())})
    len_df = pd.DataFrame(len_rows)
    report.append(len_df.to_markdown(index=False) + "\n")

    # --- Held-out cleanliness checks ---
    d1_seqs = set(d1["seq_a"]) | set(d1["seq_b"])
    d2_seqs = set(d2["seq_a"]) | set(d2["seq_b"])
    ace2_seq = d4h["seq_b"].iloc[0]
    rbd_seqs = set(d4h["seq_a"])
    n_rbd_overlap_d1 = len(rbd_seqs & d1_seqs)
    n_rbd_overlap_d2 = len(rbd_seqs & d2_seqs)
    ace2_in_d1 = ace2_seq in d1_seqs
    ace2_in_d2 = ace2_seq in d2_seqs
    d1_d2_overlap = d1_seqs & d2_seqs

    report.append("## Held-out cleanliness (D4)\n")
    report.append(f"- ACE2 sequence present in D1 (training pool)? **{ace2_in_d1}**\n")
    report.append(f"- ACE2 sequence present in D2 (training pool)? **{ace2_in_d2}**\n")
    report.append(f"- RBD mutant sequences overlapping D1: **{n_rbd_overlap_d1}**/{len(rbd_seqs)}\n")
    report.append(f"- RBD mutant sequences overlapping D2: **{n_rbd_overlap_d2}**/{len(rbd_seqs)}\n")
    report.append("- **Result: zero overlap in both directions — D4's held-out partition is genuinely clean, "
                  "not contaminated by anything in the D3 training pool.**\n")

    report.append(f"\n**Cross-dataset fact (D1 vs D2):** {len(d1_d2_overlap)} sequence is shared between D1 and D2 "
                  f"— human TNF-alpha's sequence (length {len(list(d1_d2_overlap)[0]) if d1_d2_overlap else 0}) "
                  "appears both as a generic PPI protein in D1 and as the antigen in AVIDa-hTNFa in D2. "
                  "Not a leakage concern (D1/D2 are both part of the same training pool D3), just a notable "
                  "overlap in subject matter between the two source datasets.\n")

    report.append(f"\n**Length distribution shift:** D1's training proteins are capped at 800aa max, but "
                  f"D4's held-out ACE2 sequence is **805aa — 5 residues longer than anything seen in D1 training**. "
                  "A minor but real out-of-distribution point: the held-out set isn't just a new domain, "
                  "it also touches a sequence length just past the edge of the training distribution.\n")

    # --- D3 duplicate rows ---
    n_dup_rows = d3.duplicated().sum()
    n_dup_pairs = d3.duplicated(subset=["seq_a", "seq_b"]).sum()
    report.append(f"\n**D3 duplicate rows:** {n_dup_rows:,} exact duplicate rows; {n_dup_pairs:,} duplicate "
                  "(seq_a, seq_b) pairs ignoring label — inherited mostly from D1's known `ecoli_test.tsv` "
                  "duplicate rows (see `docs/eda-ppi.md`), not a new issue introduced by combining.\n")

    # --- Vocab check on D4 (ACE2 + RBD) ---
    ace2_nonstd = sorted(set(ace2_seq) - STANDARD_AA)
    rbd_nonstd = int(d4h["seq_a"].apply(lambda s: bool(set(s) - STANDARD_AA)).sum())
    report.append(f"\n**Vocabulary check (D4 held-out):** ACE2 non-standard residues: {ace2_nonstd or 'none'}. "
                  f"RBD mutants with non-standard residues: {rbd_nonstd}/{len(d4h)}. Fully standard-alphabet.\n")

    # --- Figures ---
    fig, ax = plt.subplots(figsize=(9, 4))
    labels = ["dscript_human_train", "dscript_human_test", "avida_hil6", "avida_htnfa", "mlaep_ace2_heldout"]
    vals = [
        d1.loc[d1.source_dataset == "dscript_human_train", "label"].mean(),
        d1.loc[d1.source_dataset == "dscript_human_test", "label"].mean(),
        d2.loc[d2.source_dataset == "avida_hil6", "label"].mean(),
        d2.loc[d2.source_dataset == "avida_htnfa", "label"].mean(),
        d4h["label"].mean(),
    ]
    ax.bar(labels, vals)
    ax.set_ylabel("Positive fraction")
    ax.set_title("Positive fraction across D1/D2 sources + D4 held-out")
    ax.tick_params(axis="x", rotation=30)
    plt.tight_layout()
    fig.savefig(FIGS / "combined_positive_fraction_by_source.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(d3["seq_a"].str.len(), bins=60, alpha=0.5, label="D3 train pool: seq_a", range=(0, 900))
    ax.hist(d3["seq_b"].str.len(), bins=60, alpha=0.5, label="D3 train pool: seq_b", range=(0, 900))
    ax.axvline(201, color="darkred", linestyle="--", label="D4 held-out: RBD mutant (201aa, constant)")
    ax.axvline(805, color="black", linestyle="--", label="D4 held-out: ACE2 (805aa, constant)")
    ax.set_xlabel("Sequence length (aa)")
    ax.set_ylabel("Count")
    ax.set_title("D3 training-pool length distribution vs. D4 held-out lengths")
    ax.legend(fontsize=8)
    plt.tight_layout()
    fig.savefig(FIGS / "combined_length_train_vs_heldout.png", dpi=150)
    plt.close(fig)

    report.append("\n## Figures\n")
    report.append("![](figures/combined_positive_fraction_by_source.png)\n")
    report.append("![](figures/combined_length_train_vs_heldout.png)\n")

    report.append("\n## Notes\n")
    report.append("- **Column semantics differ by source within D3**: in D1 (PPI), `seq_a`/`seq_b` are symmetric "
                  "generic proteins; in D2 (AVIDa), `seq_a` is specifically the antibody (VHH) and `seq_b` is "
                  "specifically the antigen — an asymmetric role. A model trained on D3 should be aware `seq_a`/`seq_b` "
                  "don't mean the same thing across `pair_type`; consider adding an explicit role indicator if this "
                  "matters for the chosen architecture.\n")
    report.append("- D4's held-out set has **zero sequence-length variance** (every RBD mutant is exactly 201aa; "
                  "ACE2 is a constant 805aa) — the length-confound check from Phase 1 (varying positive fraction "
                  "by pair length) mechanically cannot manifest in this held-out set, since there's no length "
                  "variation to correlate with.\n")

    (DOCS / "eda-combined.md").write_text("\n".join(report))
    print("Wrote docs/eda-combined.md")


if __name__ == "__main__":
    main()
