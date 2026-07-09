"""Length-only baseline: how much of D1 (PPI) / D2 (AVIDa) label signal can be
explained by sequence length alone, with no biological content?

Features: len_a, len_b, len_a+len_b, |len_a-len_b|, len_a*len_b.
Model: GradientBoostingClassifier (captures the non-monotonic/U-shaped length
        relationship found in the Phase 1 EDA; plain linear logistic regression
        would underestimate it).
Split: D1 uses the existing human_train/human_test split (same split a real
       model would be evaluated on). D2 has no official split, so a stratified
       80/20 random split is used (fixed seed for reproducibility).
Metrics: AUROC + AUPRC (average precision), since raw accuracy is meaningless
         under ~9% / ~4% positive rates.

Writes docs/length_baseline_results.md.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import train_test_split

RAWDATA = Path("rawdata")
DOCS = Path("docs")

FEATURES = ["len_a", "len_b", "len_sum", "len_diff", "len_prod"]


def add_length_features(df):
    df = df.copy()
    df["len_a"] = df["seq_a"].str.len()
    df["len_b"] = df["seq_b"].str.len()
    df["len_sum"] = df["len_a"] + df["len_b"]
    df["len_diff"] = (df["len_a"] - df["len_b"]).abs()
    df["len_prod"] = df["len_a"] * df["len_b"]
    return df


def fit_eval(train_df, test_df, label_name):
    train_df = add_length_features(train_df)
    test_df = add_length_features(test_df)

    clf = GradientBoostingClassifier(random_state=0)
    clf.fit(train_df[FEATURES], train_df["label"])
    probs = clf.predict_proba(test_df[FEATURES])[:, 1]

    auroc = roc_auc_score(test_df["label"], probs)
    auprc = average_precision_score(test_df["label"], probs)
    base_rate = test_df["label"].mean()

    return {
        "dataset": label_name,
        "n_train": len(train_df),
        "n_test": len(test_df),
        "positive_rate_test": round(base_rate, 4),
        "AUROC": round(auroc, 4),
        "AUPRC": round(auprc, 4),
        "AUPRC_random_floor": round(base_rate, 4),  # AUPRC of a random/constant predictor equals base rate
    }


def read_pairs(path):
    df = pd.read_csv(path, sep="\t", header=None, names=["protein_a", "protein_b", "label"])
    df["label"] = df["label"].astype(float).astype(int)
    return df


def read_fasta(path):
    seqs = {}
    cur_id, cur_seq = None, []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if cur_id:
                    seqs[cur_id] = "".join(cur_seq)
                cur_id, cur_seq = line[1:], []
            else:
                cur_seq.append(line)
        if cur_id:
            seqs[cur_id] = "".join(cur_seq)
    return seqs


def main():
    results = []

    # --- D1 (PPI): use the existing human_train/human_test split ---
    seqs = read_fasta(RAWDATA / "ppi" / "seqs" / "human.fasta")
    train = read_pairs(RAWDATA / "ppi" / "pairs" / "human_train.tsv")
    test = read_pairs(RAWDATA / "ppi" / "pairs" / "human_test.tsv")
    for df in (train, test):
        df["seq_a"] = df["protein_a"].map(seqs)
        df["seq_b"] = df["protein_b"].map(seqs)
    results.append(fit_eval(train, test, "D1 - PPI (human_train -> human_test)"))

    # --- D2 (AVIDa): no official split, stratified 80/20 random split ---
    for name, pairs_file, antigen_file in [
        ("hIL6", "AVIDa-hIL6.csv", "hIL6_antigen_sequences.csv"),
        ("hTNFa", "AVIDa-hTNFa.csv", "hTNFa_antigen_sequences.csv"),
    ]:
        pairs = pd.read_csv(RAWDATA / "avida" / pairs_file)
        antigens = pd.read_csv(RAWDATA / "avida" / antigen_file)
        merged = pairs.merge(antigens, on="Ag_label", how="left")
        merged = merged.rename(columns={"VHH_sequence": "seq_a", "Ag_sequence": "seq_b"})
        tr, te = train_test_split(merged, test_size=0.2, stratify=merged["label"], random_state=0)
        results.append(fit_eval(tr, te, f"D2 - AVIDa-{name} (random 80/20 split)"))

    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))

    report = ["# Length-only baseline results\n",
              "**Generated:** 2026-07-09 | **Script:** `src/spikes/length_baseline.py`\n",
              "Question: how much of the label signal in D1/D2 can a model explain using **only** sequence "
              "length features (`len_a, len_b, len_a+len_b, |len_a-len_b|, len_a*len_b`) — no sequence content "
              "at all? Model: GradientBoostingClassifier (captures the non-monotonic/U-shaped length-vs-positive-fraction "
              "relationship found in the Phase 1 EDA; plain linear logistic regression on raw length would underestimate it).\n",
              "D1 evaluated on the existing `human_train` -> `human_test` split (same split a real model would use). "
              "D2 has no official split, so a stratified 80/20 random split is used instead.\n",
              results_df.to_markdown(index=False) + "\n",
              "## Interpretation\n",
              "- **AUPRC_random_floor** = the positive rate itself, i.e. what a *content-blind, constant-score* "
              "predictor would score on average precision. Any AUPRC meaningfully above that floor means length "
              "alone carries real, exploitable signal.\n"]

    (DOCS / "length_baseline_results.md").write_text("\n".join(report))
    print("\nWrote docs/length_baseline_results.md")


if __name__ == "__main__":
    main()
