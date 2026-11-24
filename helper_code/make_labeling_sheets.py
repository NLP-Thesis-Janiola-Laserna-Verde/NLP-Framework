"""Build one blind labeling sheet per annotator.

Usage (from anywhere):
    python make_labeling_sheets.py pilot     # label rows whose `set` column == "pilot"
    python make_labeling_sheets.py test      # label another set (any value in the `set` column)
    python make_labeling_sheets.py all       # label everything in the file

Output goes to csv/labeling/<set>/ so pilot and main sheets never overwrite each other.
"""
import random
import sys
import pandas as pd
from pathlib import Path

CSV_DIR = Path(__file__).resolve().parents[1] / "csv"
RETRIEVAL_DIR = Path(__file__).resolve().parents[1] / "data" / "retrieval"
LABEL_SET = sys.argv[1] if len(sys.argv) > 1 else "pilot"
OUT_DIR = CSV_DIR / "labeling" / LABEL_SET
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODE = "pairs"          # "pairs" (thesis 3.6.1.2), "all" (everyone rates everything), or "overlap"
OVERLAP_FRAC = 0.20     # only used in "overlap" mode
ANNOTATORS = ["A1", "A2", "A3"]
PAIRS = [("A1", "A2"), ("A1", "A3"), ("A2", "A3")]
SEED = 198              # record this in your methods; do not change after the first run

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
# FIX 1: the candidates file uses "authors"; the sheets use "author"
if "author" not in cand.columns and "authors" in cand.columns:
    cand = cand.rename(columns={"authors": "author"})
for col in ["title", "venue", "url", "pub_date", "author"]:
    if col not in cand.columns:
        cand[col] = ""

cand = cand.dropna(subset=["query_id", "source_id"])

# FIX 2: choose which topics to label instead of always dropping the pilot ones
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
        cand = cand[is_pilot] if LABEL_SET.lower() == "pilot" else cand[~is_pilot]
if cand.empty:
    sys.exit(f"No rows for set '{LABEL_SET}' in {CANDIDATES_FILE}. "
             f"Values in the `set` column: {available_sets}")

cand = cand.drop_duplicates(["query_id", "source_id"])
print(f"set={LABEL_SET}:", cand["query_id"].nunique(), "topics,", len(cand), "sources")

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