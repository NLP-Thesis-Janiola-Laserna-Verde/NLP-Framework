# Evaluation decisions (recorded before pilot analysis)
Date: 2026-11-24

- "Suitable" = suitability_S >= 2 (binary relevance for Precision@k and Recall@k)
- Final label per source = median of the three annotators' S (integer, no ties with 3 raters)
- Graded gain for NDCG@k = that median S (0-3)
- Secondary, exploratory analysis only: P@k/R@k with S >= 3
- Agreement target on S before full annotation: pairwise quadratic-weighted kappa >= 0.60
  and Krippendorff's alpha (ordinal) >= 0.667; below that, revise guidelines and re-label a fresh small set

S ≥ 2 as "suitable"	A design choice
Median of three annotators	Also a design choice.