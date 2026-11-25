"""fill_added_fields.py - fill blank author / venue / pub_date on the NEWLY ADDED pilot rows.

Only rows listed in pilot_added_sources.csv are touched, only empty cells are filled, and
ratings (suitability, could_open, note) are never changed. The first 50 rows stay as they were.
"""
import re
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT_DIR / "csv"
SHEET_DIR = CSV_DIR / "labeling" / "pilot"
CANDIDATES = ROOT_DIR / "data" / "retrieval" / "candidates_pilot.csv"
ANNOTATORS = ["A1", "A2", "A3"]
ALIASES = {                      # sheet column -> possible column names in candidates_pilot.csv
    "author": ["author", "authors", "author_names", "creators", "contributors"],
    "venue": ["venue", "container_title", "journal", "source", "publisher"],
    "pub_date": ["pub_date", "publication_date", "date", "published", "year"],
}


def nid(x):
    return re.sub(r"^([A-Za-z]+)0*(\d+)$", r"\1\2", str(x).strip().upper())


cand = pd.read_csv(CANDIDATES, dtype=str).fillna("")
cand.columns = cand.columns.str.strip()
if "query_id" not in cand.columns and "topic_id" in cand.columns:
    cand = cand.rename(columns={"topic_id": "query_id"})
print("candidate columns:", cand.columns.tolist())
cand["qkey"] = cand["query_id"].map(nid)
cand = cand.drop_duplicates(["qkey", "source_id"]).set_index(["qkey", "source_id"])

maps = {}
for target, names in ALIASES.items():
    found = next((n for n in names if n in cand.columns), None)
    print(f"{target:9s} <- {found}")
    maps[target] = cand[found].to_dict() if found else {}

added = pd.read_csv(SHEET_DIR / "pilot_added_sources.csv", dtype=str).fillna("")
new_keys = set(zip(added["query_id"].map(nid), added["source_id"]))

for a in ANNOTATORS:
    path = SHEET_DIR / f"labeling_{a}.csv"
    df = pd.read_csv(path, dtype=str).fillna("")
    keys = list(zip(df["query_id"].map(nid), df["source_id"]))
    is_new = pd.Series([k in new_keys for k in keys], index=df.index)
    for target, m in maps.items():
        vals = pd.Series([m.get(k, "") for k in keys], index=df.index)
        mask = is_new & (df[target] == "") & (vals != "")
        df.loc[mask, target] = vals[mask]
        print(f"{a} {target}: filled {int(mask.sum())}, still blank among new rows: "
              f"{int((is_new & (df[target] == '')).sum())}")
    df.to_csv(path, index=False)