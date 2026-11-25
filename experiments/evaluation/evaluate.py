"""evaluate.py - NDCG@k, Precision@k, Recall@k and MAP (thesis Section 3.2.3 / 3.6.2.3).

python experiments/evaluation/evaluate.py --test
python experiments/evaluation/evaluate.py --split tuning

Inputs
  labels   data/labeling/final_labels.csv : query_id, source_id, final   (final = 0-3 human rating)
  rankings data/evaluation/rankings.csv     : system, query_id, source_id, rank   (rank 1 = best)
                                  (or a `score` column instead of `rank`; higher = better)

Conventions (record them in decisions.md)
  - suitable = final >= CUTOFF (binary, for P@k, R@k, MAP)
  - NDCG uses graded gain 2^rel - 1 and log2(i + 1) discount, IDCG over ALL labeled candidates
  - Recall and AP use all suitable sources in the candidate set as the denominator, so a
    suitable source removed by the genre filter (absent from the ranking) counts as missed
  - Precision@k always divides by k
  - Topics with no suitable source are skipped for every system (same topics for all)
  - Ranked sources with no final label are ignored (removed for all systems)
"""
import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

CUTOFF = 2          # must match decisions.md
KS = (5, 10)


# ---------------------------------------------------------------- metrics
def dcg(rels, k):
    return sum((2 ** r - 1) / math.log2(i + 2) for i, r in enumerate(rels[:k]))


def ndcg_at_k(ranked_rels, all_rels, k):
    idcg = dcg(sorted(all_rels, reverse=True), k)
    return dcg(ranked_rels, k) / idcg if idcg > 0 else np.nan


def precision_at_k(ranked_rels, k):
    return sum(r >= CUTOFF for r in ranked_rels[:k]) / k


def recall_at_k(ranked_rels, n_suitable, k):
    if n_suitable == 0:
        return np.nan
    return sum(r >= CUTOFF for r in ranked_rels[:k]) / n_suitable


def average_precision(ranked_rels, n_suitable):
    if n_suitable == 0:
        return np.nan
    hits, total = 0, 0.0
    for i, r in enumerate(ranked_rels, start=1):
        if r >= CUTOFF:
            hits += 1
            total += hits / i
    return total / n_suitable


# ---------------------------------------------------------------- evaluation
def load_labels(path):
    d = pd.read_csv(path, dtype={"query_id": str, "source_id": str})
    d.columns = d.columns.str.strip()
    col = "final" if "final" in d.columns else "suitability"
    d["rel"] = d[col].astype(int)
    return d[["query_id", "source_id", "rel"]]


def load_runs(path):
    r = pd.read_csv(path, dtype={"system": str, "query_id": str, "source_id": str})
    r.columns = r.columns.str.strip()
    if "rank" not in r.columns:
        if "score" not in r.columns:
            raise ValueError("rankings file needs a 'rank' or a 'score' column")
        r = r.sort_values(["system", "query_id", "score", "source_id"],
                          ascending=[True, True, False, True])
        r["rank"] = r.groupby(["system", "query_id"]).cumcount() + 1
    return r


def evaluate(labels, runs, ks=KS):
    lab = {q: dict(zip(g["source_id"], g["rel"])) for q, g in labels.groupby("query_id")}
    rows, unlabeled = [], 0
    for (system, qid), g in runs.groupby(["system", "query_id"]):
        if qid not in lab:
            continue
        assert not g["source_id"].duplicated().any(), f"duplicate source in {system}/{qid}"
        cands = lab[qid]
        ids = g.sort_values("rank")["source_id"].tolist()
        unlabeled += sum(s not in cands for s in ids)
        ranked = [cands[s] for s in ids if s in cands]
        all_rels = list(cands.values())
        n_suit = sum(r >= CUTOFF for r in all_rels)
        row = {"system": system, "query_id": qid, "n_suitable": n_suit}
        for k in ks:
            row[f"ndcg@{k}"] = ndcg_at_k(ranked, all_rels, k)
            row[f"p@{k}"] = precision_at_k(ranked, k)
            row[f"r@{k}"] = recall_at_k(ranked, n_suit, k)
        row["map"] = average_precision(ranked, n_suit)
        rows.append(row)

    per_topic = pd.DataFrame(rows)
    skipped = sorted(per_topic.loc[per_topic["n_suitable"] == 0, "query_id"].unique())
    per_topic = per_topic[per_topic["n_suitable"] > 0].reset_index(drop=True)

    metric_cols = [c for c in per_topic.columns if c not in ("system", "query_id", "n_suitable")]
    summary = per_topic.groupby("system")[metric_cols].agg(["mean", "std"])
    summary.columns = [f"{m}_{s}" for m, s in summary.columns]
    return per_topic, summary.reset_index(), skipped, unlabeled


# ---------------------------------------------------------------- tests
def close(a, b, tol=1e-9):
    return abs(a - b) < tol


def run_tests():
    all_rels = [3, 2, 1, 0, 2]            # a=3 b=2 c=1 d=0 e=2 -> 3 suitable
    x = [3, 0, 2, 2, 1]                   # ranking a, d, b, e, c
    assert close(precision_at_k(x, 3), 2 / 3)
    assert close(recall_at_k(x, 3, 3), 2 / 3)
    assert close(average_precision(x, 3), (1 + 2 / 3 + 3 / 4) / 3)
    assert close(ndcg_at_k(x, all_rels, 3), (7 + 3 / 2) / (7 + 3 / math.log2(3) + 3 / 2))

    y = [3, 0, 2, 1]                      # e (suitable) removed by the genre filter
    assert close(recall_at_k(y, 3, 4), 2 / 3)
    assert close(average_precision(y, 3), (1 + 2 / 3) / 3)

    perfect = sorted(all_rels, reverse=True)
    assert close(ndcg_at_k(perfect, all_rels, 5), 1.0)
    assert close(average_precision(perfect, 3), 1.0)
    assert close(precision_at_k([3], 5), 1 / 5)            # always divides by k

    assert math.isnan(ndcg_at_k([0, 0], [0, 0], 2))
    assert math.isnan(recall_at_k([0, 1], 0, 2))
    assert math.isnan(average_precision([0, 1], 0))

    # full pipeline on a toy example, including an unlabeled source and a skipped topic
    labels = pd.DataFrame({
        "query_id": ["q1"] * 5 + ["q2"] * 2,
        "source_id": list("abcde") + ["f", "g"],
        "rel": [3, 2, 1, 0, 2, 0, 1]})
    runs = pd.DataFrame({
        "system": ["S"] * 6 + ["S"] * 2,
        "query_id": ["q1"] * 6 + ["q2"] * 2,
        "source_id": list("adbec") + ["zzz"] + ["f", "g"],
        "rank": [1, 2, 3, 4, 5, 6, 1, 2]})
    per_topic, summary, skipped, unlabeled = evaluate(labels, runs, ks=(3,))
    assert skipped == ["q2"] and unlabeled == 1
    assert len(per_topic) == 1
    assert close(per_topic.loc[0, "p@3"], 2 / 3)
    assert close(per_topic.loc[0, "map"], (1 + 2 / 3 + 3 / 4) / 3)
    print("all tests passed")


# ---------------------------------------------------------------- command line
if __name__ == "__main__":
    data_dir = Path(__file__).resolve().parents[2] / "data"
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="run the built-in tests and exit")
    ap.add_argument("--labels", default=str(data_dir / "labeling" / "final_labels.csv"))
    ap.add_argument("--runs", default=str(data_dir / "evaluation" / "rankings.csv"))
    ap.add_argument("--split", choices=["pilot", "tuning", "validation", "test"],
                    help="only evaluate topics in this split (uses data/topics/topic_split.csv)")
    ap.add_argument("--confirm-test", action="store_true",
                    help="required to evaluate the locked test topics")
    ap.add_argument("--out", default=str(data_dir / "evaluation" / "eval"))
    args = ap.parse_args()

    if args.test:
        run_tests()
        raise SystemExit

    labels, runs = load_labels(args.labels), load_runs(args.runs)
    if args.split:
        if args.split == "test" and not args.confirm_test:
            raise SystemExit("Test topics are locked. Add --confirm-test only for the final run.")
        split = pd.read_csv(data_dir / "topics" / "topic_split.csv", dtype=str)
        keep = set(split.loc[split["set"].str.strip().str.lower() == args.split, "topic_id"])
        labels = labels[labels["query_id"].isin(keep)]
        runs = runs[runs["query_id"].isin(keep)]

    per_topic, summary, skipped, unlabeled = evaluate(labels, runs)
    print("topics per system:\n", per_topic.groupby("system")["query_id"].nunique().to_string())
    print("topics skipped (no suitable source):", skipped or "none")
    print("ranked sources without a final label (ignored):", unlabeled)
    print(summary.round(3).to_string(index=False))

    out = Path(args.out)
    out.mkdir(exist_ok=True)
    per_topic.to_csv(out / "eval_per_topic.csv", index=False)
    summary.to_csv(out / "eval_summary.csv", index=False)