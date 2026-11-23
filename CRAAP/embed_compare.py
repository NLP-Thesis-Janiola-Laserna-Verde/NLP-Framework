"""Rank each topic's candidate sources by semantic similarity with several encoders.

Run from the repository root:
    python CRAAP/embed_compare.py
    python CRAAP/embed_compare.py --sets validation --models all-MiniLM-L6-v2 allenai-specter

Output: csv/embed_rankings_<sets>.csv (model, query_id, source_id, score, rank)
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "retrieval" / "candidates_pilot_tuning_validation_test_enriched.csv"
OUT_DIR = ROOT / "csv"
MODELS = ["all-MiniLM-L6-v2", "all-mpnet-base-v2", "allenai-specter"]


def source_text(df, sep):
    title = df["title"].fillna("").str.strip()
    abstract = df["abstract"].fillna("").str.strip()
    return (title + sep + abstract).where(abstract.ne(""), title).str.strip()


def rank_with_model(name, topics, sources, batch_size):
    model = SentenceTransformer(name)
    # SPECTER expects "title [SEP] abstract"
    sep = f" {model.tokenizer.sep_token} " if "specter" in name.lower() else ". "
    texts = source_text(sources, sep)

    src_emb = model.encode(texts.tolist(), batch_size=batch_size,
                           normalize_embeddings=True, show_progress_bar=True)
    top_emb = model.encode(topics["topic"].tolist(), batch_size=batch_size,
                           normalize_embeddings=True)
    top_idx = {q: i for i, q in enumerate(topics["query_id"])}

    out = sources[["query_id", "source_id"]].copy()
    out["score"] = [float(src_emb[i] @ top_emb[top_idx[q]]) for i, q in enumerate(out["query_id"])]
    out.loc[texts.eq("").to_numpy(), "score"] = np.nan
    out["rank"] = (out.groupby("query_id")["score"]
                      .rank(ascending=False, method="first").astype("Int64"))
    out.insert(0, "model", name)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(INPUT))
    ap.add_argument("--sets", nargs="+", default=["validation"])
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--out", default=None, help="default: csv/embed_rankings_<sets>.csv")
    a = ap.parse_args()

    df = pd.read_csv(a.input)
    df = df[df["set"].isin(a.sets)].reset_index(drop=True)
    if df.empty:
        raise SystemExit(f"no rows for sets {a.sets}")
    topics = df[["query_id", "topic"]].drop_duplicates("query_id").reset_index(drop=True)
    print(f"{len(topics)} topics, {len(df)} sources, "
          f"{int(df['abstract'].isna().sum())} without abstract (title only)")

    parts = []
    for name in a.models:
        print(f"\n== {name}")
        parts.append(rank_with_model(name, topics, df, a.batch_size))
    res = pd.concat(parts, ignore_index=True)

    out = Path(a.out) if a.out else OUT_DIR / f"embed_rankings_{'_'.join(a.sets)}.csv"
    res.to_csv(out, index=False)
    print(f"\nSaved {len(res)} rows to {out}")


if __name__ == "__main__":
    main()