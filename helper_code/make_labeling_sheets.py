"""Build one blind labeling sheet per annotator.

Usage (from anywhere):
    python make_labeling_sheets.py pilot     # 10 sources per topic, all 3 annotators rate all of them
    python make_labeling_sheets.py test      # any other value in the `set` column: pairs mode, no cap
    python make_labeling_sheets.py all       # label everything in the file

Defaults per set (override with the flags):
    pilot -> --mode all   --max-per-topic 10
    other -> --mode pairs --max-per-topic (none)

    python make_labeling_sheets.py pilot --max-per-topic 10 --mode all
    python make_labeling_sheets.py test  --mode pairs

Output goes to csv/labeling/<set>/ so pilot and main sheets never overwrite each other.
"""
import argparse
import random
import sys
import pandas as pd
from pathlib import Path

CSV_DIR = Path(__file__).resolve().parents[1] / "csv"
RETRIEVAL_DIR = Path(__file__).resolve().parents[1] / "data" / "retrieval"
OVERLAP_FRAC = 0.20     # only used in "overlap" mode
ANNOTATORS = ["A1", "A2", "A3"]
PAIRS = [("A1", "A2"), ("A1", "A3"), ("A2", "A3")]
SEED = 198              # record this in your methods; do not change after the first run

ap = argparse.ArgumentParser()
ap.add_argument("label_set", nargs="?", default="pilot", help='value of the `set` column, or "all"')
ap.add_argument("--mode", choices=["pairs", "all", "overlap"], default=None)
ap.add_argument("--max-per-topic", type=int, default=None, help="keep only this many sources per topic")
args = ap.parse_args()

LABEL_SET = args.label_set
is_pilot_run = LABEL_SET.lower() == "pilot"
MODE = args.mode or ("all" if is_pilot_run else "pairs")                    # "pairs" (thesis 3.6.1.2), "all", or "overlap"
MAX_PER_TOPIC = args.max_per_topic if args.max_per_topic is not None else (10 if is_pilot_run else None)

OUT_DIR = CSV_DIR / "labeling" / LABEL_SET
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---- load candidates ----
if LABEL_SET.lower() == "all":
    candidate_files = [
        RETRIEVAL_DIR / "candidates_pilot_tuning_validation_test_enriched.csv",
        RETRIEVAL_DIR / "candidates_pilot_tuning_validation_test.csv",
    ]
else:
    candidate_files = [
        RETRIEVAL_DIR / f"candidates_{LABEL_SET.lower()}.csv",
        RETRIEVAL_DIR / "candidates_pilot_tuning_validation_test_enriched.csv",
        RETRIEVAL_DIR / "candidates_pilot_tuning_validation_test.csv",
    ]

CANDIDATES_FILE = next((path for path in candidate_files if path.exists()), None)
if CANDIDATES_FILE is None:
    sys.exit(
        f"No candidate file found for set '{LABEL_SET}'. "
        f"Looked in: {', '.join(str(path) for path in candidate_files)}"
    )

cand = pd.read_csv(CANDIDATES_FILE, dtype=str)
cand.columns = cand.columns.str.strip()
if "query_id" not in cand.columns and "topic_id" in cand.columns:
    cand = cand.rename(columns={"topic_id": "query_id"})
# the candidates file uses "authors"; the sheets use "author"
if "author" not in cand.columns and "authors" in cand.columns:
    cand = cand.rename(columns={"authors": "author"})
for col in ["title", "venue", "url", "pub_date", "author"]:
    if col not in cand.columns:
        cand[col] = ""

cand = cand.dropna(subset=["query_id", "source_id"])

# choose which topics to label instead of always dropping the pilot ones
available_sets = (
    sorted(cand["set"].dropna().str.strip().str.lower().unique())
    if "set" in cand.columns
    else []
)
if LABEL_SET.lower() != "all":
    if "set" in cand.columns:
        cand = cand[cand["set"].fillna("").str.strip().str.lower() == LABEL_SET.lower()]
    else:   # no `set` column: fall back to the PIL prefix
        is_pilot = cand["query_id"].str.upper().str.startswith("PIL")
        cand = cand[is_pilot] if is_pilot_run else cand[~is_pilot]
if cand.empty:
    sys.exit(f"No rows for set '{LABEL_SET}' in {CANDIDATES_FILE}. "
             f"Values in the `set` column: {available_sets}")

cand = cand.drop_duplicates(["query_id", "source_id"])

# ---- optional cap per topic, keeping the scholarly / web mix, chosen at random (not by retrieval rank) ----
if MAX_PER_TOPIC:
    sel_rng = random.Random(SEED + 1)        # separate RNG so the assignments below do not change
    kept = []
    for qid, g in cand.groupby("query_id"):
        g = g.sort_values("source_id")
        if len(g) <= MAX_PER_TOPIC:
            print(f"NOTE: {qid} has only {len(g)} sources (cap {MAX_PER_TOPIC}); keeping all")
            kept.append(g)
            continue
        if "kind" in g.columns and g["kind"].notna().any():
            groups = {k: sub for k, sub in g.groupby(g["kind"].fillna("other"))}
            raw = {k: MAX_PER_TOPIC * len(sub) / len(g) for k, sub in groups.items()}   # proportional quota per kind
            quota = {k: int(v) for k, v in raw.items()}
            for k in sorted(raw, key=lambda k: raw[k] - quota[k], reverse=True)[: MAX_PER_TOPIC - sum(quota.values())]:
                quota[k] += 1
            picks = []
            for k, sub in groups.items():
                ids = sorted(sub["source_id"])
                picks += sel_rng.sample(ids, min(quota[k], len(ids)))
        else:
            picks = sel_rng.sample(sorted(g["source_id"]), MAX_PER_TOPIC)
        kept.append(g[g["source_id"].isin(picks)])
    cand = pd.concat(kept)

print(f"set={LABEL_SET} mode={MODE} max_per_topic={MAX_PER_TOPIC} file={CANDIDATES_FILE.name}: "
      f"{cand['query_id'].nunique()} topics, {len(cand)} sources")
if "kind" in cand.columns:
    print(cand.groupby(["query_id", "kind"]).size().unstack(fill_value=0))

topics = (pd.read_csv(CSV_DIR / "topics.csv", dtype=str)
            .rename(columns={"topic_id": "query_id"})[["query_id", "topic_text"]])
missing_topics = set(cand["query_id"]) - set(topics["query_id"])
if missing_topics:
    print("WARNING: no topic_text in topics.csv for:", sorted(missing_topics))

# ---- assign sources to annotators, balanced within each topic ----
rng = random.Random(SEED)
rows = []
for t, (qid, g) in enumerate(cand.groupby("query_id")):
    ids = sorted(g["source_id"].tolist())
    rng.shuffle(ids)
    if MODE == "pairs":
        for i, sid in enumerate(ids):
            for a in PAIRS[(i + t) % 3]:          # offset by topic so the load stays balanced
                rows.append((qid, sid, a, "pair"))
    elif MODE == "all":
        for sid in ids:
            for a in ANNOTATORS:
                rows.append((qid, sid, a, "all"))
    elif MODE == "overlap":
        n_shared = round(len(ids) * OVERLAP_FRAC)
        shared, rest = ids[:n_shared], ids[n_shared:]
        for sid in shared:
            for a in ANNOTATORS:
                rows.append((qid, sid, a, "shared"))
        for i, sid in enumerate(rest):
            rows.append((qid, sid, ANNOTATORS[(i + t) % 3], "single"))
    else:
        raise ValueError(f"unknown MODE: {MODE}")

assign = pd.DataFrame(rows, columns=["query_id", "source_id", "annotator_id", "role"])

# ---- sanity check ----
per_source = assign.groupby(["query_id", "source_id"])["annotator_id"].nunique()
expected = {"pairs": 2, "all": 3}.get(MODE)
if expected:
    assert (per_source == expected).all(), "some sources have the wrong number of raters"

assign.to_csv(OUT_DIR / "assignments.csv", index=False)
print(assign.groupby("annotator_id").size().rename("ratings per annotator"))

# ---- one sheet per annotator, random order, no system signals ----
cols = ["query_id", "topic_text", "source_id", "title", "venue", "url",
        "pub_date", "author", "suitability", "could_open", "note"]
for a in ANNOTATORS:
    s = (assign[assign["annotator_id"] == a]
         .merge(cand[["query_id", "source_id", "title", "venue", "url", "pub_date", "author"]],
                on=["query_id", "source_id"])
         .merge(topics, on="query_id", how="left"))
    if "topic" in cand.columns:
        topic_fallback = cand[["query_id", "topic"]].drop_duplicates("query_id")
        s = s.merge(topic_fallback, on="query_id", how="left")
        s["topic_text"] = s["topic_text"].fillna(s["topic"])
        s = s.drop(columns=["topic"])
    s = s.sample(frac=1, random_state=SEED + int(a[1]))      # random order per annotator
    s["suitability"] = ""
    s["could_open"] = ""
    s["note"] = ""
    s[cols].to_csv(OUT_DIR / f"labeling_{a}.csv", index=False)
    print(f"labeling_{a}.csv:", len(s), "rows")