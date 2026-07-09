"""EDA for the AVIDa antibody-antigen datasets (rawdata/avida/). Writes docs/eda-avida.md + docs/figures/avida_*.png."""
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

RAWDATA = Path("rawdata/avida")
DOCS = Path("docs")
FIGS = DOCS / "figures"

DATASETS = {
    "hIL6": "AVIDa-hIL6.csv",
    "hTNFa": "AVIDa-hTNFa.csv",
}


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    report = ["# EDA — Antibody-antigen (AVIDa)\n",
              "**Generated:** 2026-07-09 | **Source:** `rawdata/avida/` (see `SOURCE.md`)\n"]

    overall_stats = []
    for name, fname in DATASETS.items():
        df = pd.read_csv(RAWDATA / fname)  # read by column name — column order differs between hIL6/hTNFa
        n_rows = len(df)
        n_dup_rows = df.duplicated().sum()
        n_dup_seqs = df["VHH_sequence"].duplicated().sum()
        n_missing = df.isna().sum().sum()
        pos_frac = df["label"].mean()
        lengths = df["VHH_sequence"].str.len()

        overall_stats.append({
            "dataset": name,
            "n_rows": n_rows,
            "n_antigens": df["Ag_label"].nunique(),
            "positive_fraction": round(pos_frac, 4),
            "n_duplicate_rows": int(n_dup_rows),
            "n_duplicate_vhh_seqs": int(n_dup_seqs),
            "n_missing_values": int(n_missing),
            "vhh_length_min": int(lengths.min()),
            "vhh_length_median": float(lengths.median()),
            "vhh_length_max": int(lengths.max()),
        })

        # positive fraction by antigen
        by_ag = df.groupby("Ag_label")["label"].agg(["mean", "count"]).rename(
            columns={"mean": "positive_fraction", "count": "n_rows"}
        ).sort_values("positive_fraction", ascending=False)

        report.append(f"## {name}: positive fraction by antigen ({df['Ag_label'].nunique()} antigens)\n")
        report.append(by_ag.reset_index().to_markdown(index=False) + "\n")

        # figure: positive fraction by antigen
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.bar(by_ag.index.astype(str), by_ag["positive_fraction"])
        ax.set_ylabel("Positive fraction")
        ax.set_title(f"AVIDa-{name}: positive fraction by antigen")
        ax.tick_params(axis="x", rotation=90, labelsize=6)
        fig.tight_layout()
        fig.savefig(FIGS / f"avida_{name}_positive_fraction_by_antigen.png", dpi=150)
        plt.close(fig)

        # figure: VHH sequence length histogram
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(lengths, bins=40)
        ax.set_xlabel("VHH sequence length (aa)")
        ax.set_ylabel("Count")
        ax.set_title(f"AVIDa-{name}: VHH sequence length distribution")
        fig.tight_layout()
        fig.savefig(FIGS / f"avida_{name}_vhh_length_hist.png", dpi=150)
        plt.close(fig)

    overall_df = pd.DataFrame(overall_stats)
    report.insert(2, "## Overview\n" + overall_df.to_markdown(index=False) + "\n")

    report.append("## Subject metadata\n")
    report.append("- **hIL6**: 1 subject alpaca (`wizzy`, male) — all 573,891 rows from a single immunized animal.\n")
    report.append("- **hTNFa**: 2 subject alpacas (1 male, 1 female) — 5,580 rows split across both.\n")

    report.append("\n## Figures\n")
    for name in DATASETS:
        report.append(f"![](figures/avida_{name}_positive_fraction_by_antigen.png)\n")
        report.append(f"![](figures/avida_{name}_vhh_length_hist.png)\n")

    il6_unique_vhh = pd.read_csv(RAWDATA / "AVIDa-hIL6.csv")["VHH_sequence"].nunique()
    report.append("\n## Notes\n")
    report.append("- Column order differs between the two CSVs (`label`/`Ag_label` swapped) — read by column name, not position.\n")
    report.append("- hTNFa has only 1 antigen (`TNFa-WT-beads`), so its \"by antigen\" breakdown is a single row — included for consistency with hIL6, not because it's informative on its own.\n")
    report.append("- hTNFa is ~100x smaller than hIL6 (5,580 vs 573,891 pairs) and comes from 2 subjects vs 1 — direct comparison of statistics between the two datasets should account for this scale difference.\n")
    report.append(f"- **hIL6's high VHH-sequence \"duplicate\" count (535,292/573,891) is expected, not a data-quality issue**: only {il6_unique_vhh:,} VHH sequences are unique, each tested against a median of 14 (up to all 31) antigen variants — one row per (VHH, antigen) combination, by design.\n")

    (DOCS / "eda-avida.md").write_text("\n".join(report))
    print("Wrote docs/eda-avida.md")
    print(overall_df.to_string(index=False))


if __name__ == "__main__":
    main()
