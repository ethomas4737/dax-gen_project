"""Follow-up checks on the length confound found by length_baseline.py.

Answers two questions raised in human review of docs/length_baseline_results.md:
1. D1 (PPI): WHY does length correlate with label? Tests the ascertainment-bias
   hypothesis (positive-associated proteins are systematically longer/higher-degree
   than negative-only proteins) and whether rebalancing (random or length-matched
   undersampling) removes the length-only signal.
2. D2 (AVIDa-hIL6): IS the length signal real, or an artifact of the random 80/20
   split (most VHH clones repeat across ~14/31 antigen variants, and clones are
   ~98% binary broad-binder/non-binder)? Tests via a clone-disjoint re-split.

Prints results; does not write any file (purely diagnostic, feeds
docs/phase1_eda_summary.md §2.1/§3/§3.1 narrative).
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import train_test_split

RAWDATA = "rawdata"
FEATURES = ["len_a", "len_b", "len_sum", "len_diff", "len_prod"]


def read_fasta(path):
    seqs, cur_id, cur_seq = {}, None, []
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


def add_length_features(df):
    df = df.copy()
    df["len_sum"] = df["len_a"] + df["len_b"]
    df["len_diff"] = (df["len_a"] - df["len_b"]).abs()
    df["len_prod"] = df["len_a"] * df["len_b"]
    return df


def fit_eval(train_df, test_df, tag):
    clf = GradientBoostingClassifier(random_state=0)
    clf.fit(train_df[FEATURES], train_df["label"])
    p = clf.predict_proba(test_df[FEATURES])[:, 1]
    print(f"{tag}: n_train={len(train_df)} pos_rate_train={train_df.label.mean():.3f} "
          f"| AUROC={roc_auc_score(test_df.label, p):.4f} "
          f"AUPRC={average_precision_score(test_df.label, p):.4f} "
          f"floor={test_df.label.mean():.4f}")


def d1_ascertainment_bias_check():
    print("\n=== D1 (PPI): ascertainment-bias check ===")
    seqs = read_fasta(f"{RAWDATA}/ppi/seqs/human.fasta")
    train = pd.read_csv(f"{RAWDATA}/ppi/pairs/human_train.tsv", sep="\t", header=None,
                         names=["a", "b", "label"])
    train["label"] = train["label"].astype(float).astype(int)

    pos = train[train.label == 1]
    pos_proteins = set(pos["a"]) | set(pos["b"])
    all_proteins = set(train["a"]) | set(train["b"])
    negonly_proteins = all_proteins - pos_proteins

    len_pos = pd.Series({p: len(seqs[p]) for p in pos_proteins if p in seqs})
    len_negonly = pd.Series({p: len(seqs[p]) for p in negonly_proteins if p in seqs})
    print(f"proteins in >=1 positive pair: {len(pos_proteins)} (median len {len_pos.median():.0f}) "
          f"| negative-only proteins: {len(negonly_proteins)} (median len {len_negonly.median():.0f})")

    deg = pd.concat([train["a"], train["b"]]).value_counts()
    pos_deg = deg[deg.index.isin(pos_proteins)]
    negonly_deg = deg[deg.index.isin(negonly_proteins)]
    print(f"mean degree -- positive-associated: {pos_deg.mean():.1f} | negative-only: {negonly_deg.mean():.1f}")

    deg_df = deg.rename("degree").to_frame()
    deg_df["length"] = deg_df.index.map(lambda p: seqs.get(p, "")).str.len()
    print(f"correlation(protein length, train-degree): {deg_df[['length','degree']].corr().iloc[0,1]:.4f}"
          " (near-zero -> length is not a hub-degree proxy)")


def d1_rebalancing_test():
    print("\n=== D1 (PPI): does rebalancing remove the length-only signal? ===")
    seqs = read_fasta(f"{RAWDATA}/ppi/seqs/human.fasta")
    train = pd.read_csv(f"{RAWDATA}/ppi/pairs/human_train.tsv", sep="\t", header=None,
                         names=["a", "b", "label"])
    test = pd.read_csv(f"{RAWDATA}/ppi/pairs/human_test.tsv", sep="\t", header=None,
                        names=["a", "b", "label"])
    for df in (train, test):
        df["label"] = df["label"].astype(float).astype(int)
        df["len_a"] = df["a"].map(seqs).str.len()
        df["len_b"] = df["b"].map(seqs).str.len()
    train, test = add_length_features(train), add_length_features(test)

    fit_eval(train, test, "Original (10:1)")

    pos = train[train.label == 1]
    neg_random = train[train.label == 0].sample(n=len(pos), random_state=0)
    fit_eval(pd.concat([pos, neg_random]), test, "Random-undersampled to 1:1")

    train["len_bin"] = pd.qcut(train["len_sum"], 10, labels=False, duplicates="drop")
    neg_pool = train[train.label == 0]
    matched = [neg_pool[neg_pool.len_bin == b].sample(n=min(len(neg_pool[neg_pool.len_bin == b]), len(g)), random_state=0)
               for b, g in pos.groupby(pd.qcut(pos["len_sum"], 10, labels=False, duplicates="drop"))]
    matched = pd.concat(matched)
    fit_eval(pd.concat([pos.iloc[:len(matched)], matched]), test, "Length-matched undersample to ~1:1")


def d2_clone_disjoint_check():
    print("\n=== D2 (AVIDa-hIL6): is the length signal real, or clone-repeat leakage? ===")
    pairs = pd.read_csv(f"{RAWDATA}/avida/AVIDa-hIL6.csv")
    antigens = pd.read_csv(f"{RAWDATA}/avida/hIL6_antigen_sequences.csv")
    pairs = pairs.merge(antigens, on="Ag_label", how="left")
    pairs["len_a"] = pairs["VHH_sequence"].str.len()
    pairs["len_b"] = pairs["Ag_sequence"].str.len()
    pairs = add_length_features(pairs)

    print(f"unique clones: {pairs.VHH_sequence.nunique()} | unique antigens: {pairs.Ag_label.nunique()} "
          f"| unique VHH lengths: {pairs.len_a.nunique()}")

    by_len = pairs.groupby("len_a").agg(n=("label", "size"), posrate=("label", "mean"))
    hot = by_len.loc[149]
    print(f"length=149 bucket: n={hot.n:.0f}, posrate={hot.posrate:.3f} vs overall {pairs.label.mean():.3f}")
    sub149 = pairs[pairs.len_a == 149]
    clone_posrate = sub149.groupby("VHH_sequence")["label"].mean()
    print(f"length=149: {sub149.VHH_sequence.nunique()} distinct clones, "
          f"{(clone_posrate > 0.5).mean():.1%} are broad binders (vs "
          f"{(pairs.groupby('VHH_sequence').label.mean() > 0.5).mean():.1%} population-wide)")

    tr, te = train_test_split(pairs, test_size=0.2, stratify=pairs["label"], random_state=0)
    fit_eval(tr, te, "Row-random split (97.8% clone overlap)")

    clone_tbl = pairs.groupby("VHH_sequence")["label"].mean().reset_index()
    clone_tbl["is_broad"] = (clone_tbl["label"] > 0.5).astype(int)
    tr_c, te_c = train_test_split(clone_tbl["VHH_sequence"], test_size=0.2,
                                   stratify=clone_tbl["is_broad"], random_state=0)
    train_df = pairs[pairs.VHH_sequence.isin(set(tr_c))]
    test_df = pairs[pairs.VHH_sequence.isin(set(te_c))]
    assert len(set(train_df.VHH_sequence) & set(test_df.VHH_sequence)) == 0
    fit_eval(train_df, test_df, "Clone-disjoint split (0% clone overlap)")


if __name__ == "__main__":
    d1_ascertainment_bias_check()
    d1_rebalancing_test()
    d2_clone_disjoint_check()
