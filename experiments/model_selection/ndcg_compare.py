"""Compare the encoders by NDCG@10 of the semantic-only ranking on the validation topics.

Run from the repository root, after the validation labels are collected:
    python experiments/model_selection/ndcg_compare.py --labels data/labeling/validation/labeling_A*.csv

Inputs
  data/benchmarks/embed_rankings_validation.csv   (from experiments/model_selection/embed_compare.py): model, query_id, source_id, score, rank
  labeling files, one per annotator   (columns query_id, source_id, suitability)

Decisions (docs/decisions.md): the final label of a source is the median of the annotators'
suitability S (0-3), and the graded gain for NDCG@k is that median S.
DCG@k = sum over ranks i=1..k of gain_i / log2(i + 1); NDCG@k = DCG@k / ideal DCG@k.
A topic whose sources are all S = 0 has an undefined NDCG and is left out of the mean.
Sources without a label are counted as unjudged and given gain 0 (reported, not hidden).

Output: data/benchmarks/ndcg_validation.csv (per topic and model) and a summary table on screen.
"""
import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RANKINGS = ROOT / "data" / "benchmarks" / "embed_rankings_validation.csv"
OUT = ROOT / "data" / "benchmarks" / "ndcg_validation.csv"


def load_labels(patterns):
    files = sorted({f for p in patterns for f in glob.glob(p)})
    if not files:
        raise SystemExit(f"no labeling files match {patterns}")
    parts = []
    for f in files:
        d = pd.read_csv(f, usecols=["query_id", "source_id", "suitability"])
        d["suitability"] = pd.to_numeric(d["suitability"], errors="coerce")
        d["annotator"] = Path(f).stem
        parts.append(d)
    raw = pd.concat(parts, ignore_index=True).dropna(subset=["suitability"])
    bad = raw[~raw["suitability"].isin([0, 1, 2, 3])]
    if not bad.empty:
        raise SystemExit(f"suitability outside 0-3 in {bad['annotator'].unique().tolist()}")
    g = raw.groupby(["query_id", "source_id"])["suitability"]
    labels = g.median().rename("gain").reset_index()
    labels["n_raters"] = g.count().to_numpy()
    print(f"{len(files)} labeling files, {len(labels)} labeled sources, "
          f"raters per source: {labels['n_raters'].value_counts().sort_index().to_dict()}")
    return labels


def ndcg_at_k(gains_in_rank_order, all_gains, k):
    disc = 1.0 / np.log2(np.arange(2, k + 2))
    g = np.asarray(gains_in_rank_order, float)[:k]
    ideal = np.sort(np.asarray(all_gains, float))[::-1][:k]
    idcg = float((ideal * disc[:len(ideal)]).sum())
    if idcg == 0:
        return np.nan
    return float((g * disc[:len(g)]).sum()) / idcg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", nargs="+", required=True, help="labeling csv files or globs")
    ap.add_argument("--rankings", default=str(RANKINGS))
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    labels = load_labels(a.labels)
    rk = pd.read_csv(a.rankings)
    rk = rk.merge(labels[["query_id", "source_id", "gain"]], on=["query_id", "source_id"], how="left")
    rk["unjudged"] = rk["gain"].isna()
    rk["gain"] = rk["gain"].fillna(0.0)
    # sources with no text have no score/rank: put them last so they cannot help
    rk["rank"] = rk["rank"].fillna(10**6)

    rows = []
    for (model, q), d in rk.groupby(["model", "query_id"]):
        d = d.sort_values("rank")
        rows.append({"model": model, "query_id": q, "n_sources": len(d),
                     "n_unjudged": int(d["unjudged"].sum()),
                     f"ndcg@{a.k}": ndcg_at_k(d["gain"], d["gain"], a.k)})
    per_topic = pd.DataFrame(rows)
    per_topic.to_csv(a.out, index=False)

    col = f"ndcg@{a.k}"
    summary = (per_topic.groupby("model")
               .agg(mean_ndcg=(col, "mean"), topics_scored=(col, "count"),
                    topics_undefined=(col, lambda s: int(s.isna().sum())),
                    unjudged=("n_unjudged", "sum"))
               .sort_values("mean_ndcg", ascending=False))
    print(f"\nNDCG@{a.k} on validation topics (higher is better)")
    print(summary.round(4).to_string())
    if int(per_topic["n_unjudged"].sum()):
        print("\nNote: some ranked sources have no label and were counted as gain 0.")
    print(f"\nPer-topic results saved to {a.out}")


if __name__ == "__main__":
    main()