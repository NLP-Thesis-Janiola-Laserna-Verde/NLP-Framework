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
The final label is the agreed rating, or the median after a third rater breaks a disagreement

- Unranked-venue threshold: if more than 33% of scholarly papers with venue information
  (pilot and tuning candidates) receive the default score, or more than 50% within any
  single field, a manual venue table based on a published ranking (edition cited) is added
  and fixed before test topics are evaluated. Otherwise the default is kept and the
  proportions are reported as a limitation.
- Counted: authority_basis == "default_unranked" over scholarly rows excluding "no_venue_info".
  Preprints are also reported separately.