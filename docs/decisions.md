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

## Encoder selection (recorded before validation labels are scored)
Date: 2026-11-24

- Rule (Table 3.7, section 3.4.2): choose the most effective encoder by NDCG@10 on the
  validation topics among those that meet the efficiency and reproducibility criteria.
- Similar performance: models within 0.02 NDCG@10 of the best are treated as similar,
  and the smallest of them (fewest parameters) is chosen.
- Efficiency: processing time per query (about 30 candidates) must stay under 2 s (NFR1),
  and peak memory must fit the 8 GB minimum in Table 3.2.
- Reproducibility: open weights, with the model revision pinned.
- Benchmark on laptop1 (4 cores, 16 GB, CPU only):
  MiniLM 64 ms/doc median, 753 MB peak; mpnet 480 ms/doc, 1961 MB;
  SPECTER 1106 ms/doc, 1482 MB. Laptop2 and laptop3 results to be added.