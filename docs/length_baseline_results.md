# Length-only baseline results

**Generated:** 2026-07-09 | **Script:** `src/spikes/length_baseline.py`

Question: how much of the label signal in D1/D2 can a model explain using **only** sequence length features (`len_a, len_b, len_a+len_b, |len_a-len_b|, len_a*len_b`) — no sequence content at all? Model: GradientBoostingClassifier (captures the non-monotonic/U-shaped length-vs-positive-fraction relationship found in the Phase 1 EDA; plain linear logistic regression on raw length would underestimate it).

D1 evaluated on the existing `human_train` -> `human_test` split (same split a real model would use). D2 has no official split, so a stratified 80/20 random split is used instead.

| dataset                               |   n_train |   n_test |   positive_rate_test |   AUROC |   AUPRC |   AUPRC_random_floor |
|:--------------------------------------|----------:|---------:|---------------------:|--------:|--------:|---------------------:|
| D1 - PPI (human_train -> human_test)  |    421792 |    52725 |               0.0909 |  0.6522 |  0.1826 |               0.0909 |
| D2 - AVIDa-hIL6 (random 80/20 split)  |    459112 |   114779 |               0.0366 |  0.803  |  0.1436 |               0.0366 |
| D2 - AVIDa-hTNFa (random 80/20 split) |      4464 |     1116 |               0.1219 |  0.7619 |  0.3989 |               0.1219 |

## Interpretation

- **AUPRC_random_floor** = the positive rate itself, i.e. what a *content-blind, constant-score* predictor would score on average precision. Any AUPRC meaningfully above that floor means length alone carries real, exploitable signal.

**Headline result: length alone is a meaningfully strong predictor in all three cases, not just PPI.**

- **D1 (PPI):** AUROC 0.652 (vs. 0.5 random), AUPRC 0.183 vs. a 0.091 floor — **exactly 2x** the random-floor AUPRC. Confirms the length confound found in the Phase 1 EDA is real and quantifiable: a model with zero sequence understanding can meaningfully outperform random using length alone.
- **D2 (AVIDa-hIL6):** AUROC **0.803** — stronger than PPI's. AUPRC 0.144 vs. a 0.037 floor (~3.9x). This is a bigger length signal than we expected going in.
- **D2 (AVIDa-hTNFa):** AUROC 0.762, AUPRC 0.399 vs. 0.122 floor (~3.3x) — but from a much smaller train/test set (4,464/1,116 rows), so treat with more caution (higher variance, more overfitting risk for a boosted-tree model on this little data).

**On hIL6's surprisingly strong result — checked whether it's really "antigen identity via length":** grouped by antigen, mean VHH length only varies from 150.8–151.2aa across all 31 antigens (a tiny range) with a moderate negative correlation to antigen positive-rate (r=−0.39) — not enough by itself to explain an AUROC of 0.80. The more likely explanation is length variation *within* individual VHH clones: nanobody CDR3 length is known in the antibody literature to correlate with binding promiscuity (shorter/longer CDR3 loops → more or less polyreactive binding behavior), so length may be picking up a crude but real biophysical property of the antibody itself, not purely an artifact of the assay design. Either way, the practical implication is the same: **a model that leans on this signal is using surface-level composition rather than learning specific epitope recognition**, which is exactly the shortcut-learning risk this baseline exists to catch.

**Bottom line:** any future PLM-based model on D1 or D2 needs to clear these numbers by a real margin to demonstrate it's learning sequence-specific interaction signal rather than recovering length/composition shortcuts. Report both the model's metric and this baseline's metric side by side, always.
