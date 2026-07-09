"""EDA for the MLAEP viral-antigenic-evolution data (rawdata/mlaep/). Writes docs/eda-mlaep.md + docs/figures/mlaep_*.png.

MLAEP bundles 7 heterogeneous files (not one homogeneous interaction table like PPI/AVIDa), so
"positive fraction" applies specifically to the binary columns in GMM_covid_info_seq.csv
(ace2_bind + 8 per-antibody escape indicators); the other files get descriptive stats appropriate
to their shape.
"""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

RAWDATA = Path("rawdata/mlaep")
DOCS = Path("docs")
FIGS = DOCS / "figures"


def eda_gmm(report):
    df = pd.read_csv(RAWDATA / "GMM_covid_info_seq.csv", index_col=0)
    binary_cols = ["ace2_bind"] + [c for c in df.columns if c.startswith("COV2-")]

    pos_frac = df[binary_cols].mean().round(4).rename("positive_fraction")
    n_missing = df.isna().sum().sum()
    n_dup_seq = df["seq"].duplicated().sum()
    lengths = df["seq"].str.len()

    report.append("## GMM_covid_info_seq.csv — deep mutational scan (19,132 RBD mutants)\n")
    report.append(f"- Rows: {len(df):,} | Missing values: {int(n_missing)} | Duplicate `seq` rows: {int(n_dup_seq)}\n")
    report.append(f"- `seq` length: all {lengths.nunique()} unique value(s) — min {int(lengths.min())}, max {int(lengths.max())} (RBD mutants are all point/double substitutions of a fixed-length reference)\n")
    report.append(f"- `avg_bind` (continuous binding score): mean={df['avg_bind'].mean():.3f}, std={df['avg_bind'].std():.3f}, min={df['avg_bind'].min():.3f}, max={df['avg_bind'].max():.3f}\n")
    report.append("\n**Positive fraction — binary columns** (`ace2_bind` = binds ACE2; `COV2-*_400` = escapes that antibody clone at 1:400 dilution):\n")
    report.append(pos_frac.reset_index().rename(columns={"index": "column"}).to_markdown(index=False) + "\n")

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(pos_frac.index, pos_frac.values)
    ax.set_ylabel("Positive fraction")
    ax.set_title("MLAEP: positive fraction — ACE2 binding + antibody escape (per clone)")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(FIGS / "mlaep_gmm_positive_fraction.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(df["avg_bind"], bins=50)
    ax.set_xlabel("avg_bind (continuous ACE2-binding score)")
    ax.set_ylabel("Count")
    ax.set_title("MLAEP: avg_bind distribution (19,132 RBD mutants)")
    fig.tight_layout()
    fig.savefig(FIGS / "mlaep_gmm_avgbind_hist.png", dpi=150)
    plt.close(fig)

    report.append("\n![](figures/mlaep_gmm_positive_fraction.png)\n")
    report.append("![](figures/mlaep_gmm_avgbind_hist.png)\n")


def eda_variants(report):
    pvnt = pd.read_csv(RAWDATA / "pVNT.csv")
    pvnt_seq = pd.read_csv(RAWDATA / "pVNT_seq.csv", index_col=0)
    variants = pd.read_csv(RAWDATA / "sars-cov-2_variants_update.csv", index_col=0)

    report.append("\n## pVNT.csv + pVNT_seq.csv — named high-risk-variant neutralization data\n")
    report.append(f"- {len(pvnt)} named variant/mutation combinations, {len(pvnt_seq)} matching RBD sequences.\n")
    report.append(f"- `Reduction` (fold-reduction in neutralization titer vs wild-type): min={pvnt['Reduction'].min():.2f}, median={pvnt['Reduction'].median():.2f}, max={pvnt['Reduction'].max():.2f}\n")
    report.append(f"- {(pvnt['Reduction'] < 0).sum()} entries have **negative** reduction (i.e. enhanced neutralization vs WT) — not an error, just means those mutants are neutralized more effectively.\n")
    report.append(f"- Missing `WHO ` (variant Greek-letter name) for {pvnt['WHO '].isna().sum()}/{len(pvnt)} rows (unnamed/minor lineages).\n")

    report.append(f"\n## sars-cov-2_variants_update.csv — named variant panel\n")
    report.append(f"- {len(variants)} entries: {', '.join(variants['name'].tolist())}\n")
    report.append(f"- Note: 2 rows both named `Omicron` (lineages `B.1.1.529` and `BA.2`) — sub-lineage distinction, not a duplicate.\n")


def eda_site_class(report):
    site = pd.read_csv(RAWDATA / "site_class.csv", index_col=0)
    report.append("\n## site_class.csv — RBD site structural/epitope classification\n")
    report.append(f"- {len(site)} sites classified.\n")
    vc = site["class"].value_counts()
    report.append(vc.reset_index().rename(columns={"index": "class", "count": "n_sites"}).to_markdown(index=False) + "\n")
    n_ace2 = site["ACE2"].notna().sum()
    report.append(f"- ACE2-contact flag set (non-null) for {n_ace2}/{len(site)} sites ({n_ace2/len(site):.1%}).\n")


def eda_reference_and_structures(report):
    ref = (RAWDATA / "Covid19_RBD_seq.txt").read_text().strip()
    report.append("\n## Covid19_RBD_seq.txt — reference RBD sequence\n")
    report.append(f"- Single reference sequence (Wuhan-Hu-1 RBD), length {len(ref)} aa.\n")

    lengths = []
    with open(RAWDATA / "merged_all.jsonl") as f:
        for line in f:
            d = json.loads(line)
            lengths.append(len(d["seq"]))
    s = pd.Series(lengths)
    report.append("\n## merged_all.jsonl — generic protein structures (not SARS-CoV-2-specific)\n")
    report.append(f"- {len(lengths)} structures (seq + backbone coordinates). Sequence length: min={int(s.min())}, median={s.median():.0f}, max={int(s.max())}.\n")
    report.append("- Likely the structural-model training/reference set (per MLAEP's multi-task architecture), distinct in kind from the other 6 COVID-specific files — no interaction/binding label, so \"positive fraction\" doesn't apply here.\n")


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    report = ["# EDA — Viral antigenic evolution (MLAEP)\n",
              "**Generated:** 2026-07-09 | **Source:** `rawdata/mlaep/` (see `SOURCE.md`)\n",
              "MLAEP bundles 7 heterogeneous files rather than one interaction table. \"Positive fraction\" is reported where a natural binary label exists (`GMM_covid_info_seq.csv`); other files get descriptive stats matching their shape.\n"]

    eda_gmm(report)
    eda_variants(report)
    eda_site_class(report)
    eda_reference_and_structures(report)

    (DOCS / "eda-mlaep.md").write_text("\n".join(report))
    print("Wrote docs/eda-mlaep.md")


if __name__ == "__main__":
    main()
