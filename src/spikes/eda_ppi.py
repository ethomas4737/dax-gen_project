"""EDA for the D-SCRIPT PPI dataset (rawdata/ppi/). Writes docs/eda-ppi.md + docs/figures/ppi_*.png."""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

RAWDATA = Path("rawdata/ppi")
DOCS = Path("docs")
FIGS = DOCS / "figures"

PAIR_FILES = {
    "human_train": "pairs/human_train.tsv",
    "human_test": "pairs/human_test.tsv",
    "mouse_test": "pairs/mouse_test.tsv",
    "fly_test": "pairs/fly_test.tsv",
    "yeast_test": "pairs/yeast_test.tsv",
    "worm_test": "pairs/worm_test.tsv",
    "ecoli_test": "pairs/ecoli_test.tsv",
}
SEQ_FILES = {
    "human": "seqs/human.fasta",
    "mouse": "seqs/mouse.fasta",
    "fly": "seqs/fly.fasta",
    "yeast": "seqs/yeast.fasta",
    "worm": "seqs/worm.fasta",
    "ecoli": "seqs/ecoli.fasta",
}


def read_pairs(path):
    df = pd.read_csv(path, sep="\t", header=None, names=["protein_a", "protein_b", "label"])
    df["label"] = df["label"].astype(float).astype(int)  # normalize "0.0"/"1.0" vs "0"/"1"
    return df


def read_fasta_lengths(path):
    lengths = []
    seq = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if seq:
                    lengths.append(len("".join(seq)))
                    seq = []
            else:
                seq.append(line)
        if seq:
            lengths.append(len("".join(seq)))
    return lengths


def main():
    FIGS.mkdir(parents=True, exist_ok=True)

    pair_stats = []
    for name, rel in PAIR_FILES.items():
        df = read_pairs(RAWDATA / rel)
        n_rows = len(df)
        n_dup_rows = df.duplicated().sum()
        n_missing = df.isna().sum().sum()
        pos_frac = df["label"].mean()
        n_unique_proteins = len(set(df["protein_a"]) | set(df["protein_b"]))
        pair_stats.append({
            "dataset": name,
            "n_rows": n_rows,
            "positive_fraction": round(pos_frac, 4),
            "n_unique_proteins": n_unique_proteins,
            "n_duplicate_rows": int(n_dup_rows),
            "n_missing_values": int(n_missing),
        })
    pair_df = pd.DataFrame(pair_stats)

    seq_stats = []
    all_lengths = {}
    for species, rel in SEQ_FILES.items():
        lengths = read_fasta_lengths(RAWDATA / rel)
        all_lengths[species] = lengths
        s = pd.Series(lengths)
        seq_stats.append({
            "species": species,
            "n_sequences": len(lengths),
            "length_min": int(s.min()),
            "length_median": float(s.median()),
            "length_mean": round(float(s.mean()), 1),
            "length_max": int(s.max()),
        })
    seq_df = pd.DataFrame(seq_stats)

    # duplicate sequence check (identical sequence, different ID) per species
    dup_seq_counts = {}
    for species, rel in SEQ_FILES.items():
        seqs = []
        cur = []
        with open(RAWDATA / rel) as f:
            for line in f:
                line = line.strip()
                if line.startswith(">"):
                    if cur:
                        seqs.append("".join(cur))
                        cur = []
                else:
                    cur.append(line)
            if cur:
                seqs.append("".join(cur))
        dup_seq_counts[species] = len(seqs) - len(set(seqs))

    # figure: sequence length distributions per species
    fig, ax = plt.subplots(figsize=(8, 5))
    for species, lengths in all_lengths.items():
        ax.hist(lengths, bins=60, alpha=0.5, label=species, range=(0, 2000))
    ax.set_xlabel("Sequence length (aa)")
    ax.set_ylabel("Count")
    ax.set_title("D-SCRIPT PPI: protein sequence length distribution by species")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGS / "ppi_seq_length_hist.png", dpi=150)
    plt.close(fig)

    # figure: positive fraction per dataset
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(pair_df["dataset"], pair_df["positive_fraction"])
    ax.set_ylabel("Positive fraction")
    ax.set_title("D-SCRIPT PPI: positive (interacting) fraction by species/split")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(FIGS / "ppi_positive_fraction.png", dpi=150)
    plt.close(fig)

    report = []
    report.append("# EDA — PPI (D-SCRIPT)\n")
    report.append(f"**Generated:** 2026-07-09 | **Source:** `rawdata/ppi/` (see `SOURCE.md`)\n")
    report.append("## Positive fraction & row counts by dataset/species\n")
    report.append(pair_df.to_markdown(index=False) + "\n")
    report.append("## Sequence length distribution by species\n")
    report.append(seq_df.to_markdown(index=False) + "\n")
    report.append("## Duplicate sequences (identical seq, different protein ID)\n")
    for species, n in dup_seq_counts.items():
        report.append(f"- {species}: {n} duplicate sequence(s)\n")
    report.append("\n## Figures\n")
    report.append("![](figures/ppi_positive_fraction.png)\n")
    report.append("![](figures/ppi_seq_length_hist.png)\n")
    report.append("\n## Notes\n")
    report.append("- Label column normalized to int (source files mix `0`/`1` and `0.0`/`1.0` formatting across species).\n")
    report.append("- `n_unique_proteins` counts proteins referenced in that species' pair file(s), not the full species fasta (which may include unpaired proteins).\n")
    report.append("- **Positive fraction is exactly ~0.0909 (1/11) for every species and split** — indicates the D-SCRIPT benchmark uses a fixed 1:10 positive:negative sampling ratio by construction, not an incidental class imbalance.\n")
    report.append("- **Sequence lengths are hard-capped in [50, 800] aa** for every species — a deliberate preprocessing filter in the source data, not a natural distribution tail.\n")
    report.append("- **Large fraction of duplicate sequences** (same amino-acid sequence under different protein IDs) — e.g. human: 54,898/70,529 (78%), mouse: 22,689/40,606 (56%). Likely reflects transcript-isoform redundancy in the underlying STRING/Ensembl protein set rather than a data error; worth accounting for if training on this data (isoform duplicates could leak between train/test).\n")
    report.append("- `ecoli_test.tsv` has 3,761 duplicate **rows** (exact pair+label duplicates) out of 22,000 — unlike any other species file (all had 0). Worth flagging if using ecoli as a held-out test set.\n")

    (DOCS / "eda-ppi.md").write_text("\n".join(report))
    print("Wrote docs/eda-ppi.md")
    print(pair_df.to_string(index=False))
    print(seq_df.to_string(index=False))


if __name__ == "__main__":
    main()
