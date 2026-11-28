"""make_rankings.py - turn pilot combined signals into rankings_pilot.csv.

Reads  csv/signals_pilot.csv : source_id, s_sem, s_cur, s_auth, s_purp
       data/labeling/pilot/assignments.csv : query_id, source_id
Writes csv/rankings_pilot.csv : system, query_id, source_id, rank, score
Score = sum(w_i * s_i) / sum(w_i) over the available signals (thesis 3.4.4); ties broken by s_sem.
"""
import re
from pathlib import Path

import numpy as np
import pandas as pd

CSV_DIR = Path(__file__).resolve().parents[1] / "csv"
SIGNALS = CSV_DIR / "signals_pilot.csv"
ASSIGNMENTS = Path(__file__).resolve().parents[1] / "data" / "labeling" / "pilot" / "assignments.csv"
COLS = ["s_sem", "s_cur", "s_auth", "s_purp"]

# order: (w_sem, w_cur, w_auth, w_purp). The full-system weights are PROVISIONAL: fix them in decisions.md
# before looking at any evaluation numbers.
SYSTEMS = {
    "semantic_only":  (1.00, 0.00, 0.00, 0.00),
    "full":           (0.40, 0.20, 0.20, 0.20),
    "no_currency":    (0.40, 0.00, 0.20, 0.20),
    "no_authority":   (0.40, 0.20, 0.00, 0.20),
    "no_purpose":     (0.40, 0.20, 0.20, 0.00),
}


def nid(x):
    return re.sub(r"^([A-Za-z]+)0*(\d+)$", r"\1\2", str(x).strip().upper())


sig = pd.read_csv(SIGNALS, dtype={"source_id": str})
sig.columns = sig.columns.str.strip()

assignments = pd.read_csv(ASSIGNMENTS, dtype={"query_id": str, "source_id": str})
assignments["query_id"] = assignments["query_id"].map(nid)
source_topics = assignments[["query_id", "source_id"]].drop_duplicates("source_id")
sig = sig.merge(source_topics, on="source_id", how="inner")
missing = assignments["source_id"].loc[
    ~assignments["source_id"].isin(sig["source_id"])
].nunique()
if missing:
    print(f"assigned pilot sources missing from signals_pilot.csv: {missing}")
if sig.empty:
    raise ValueError(
        "No assigned pilot sources have rows in csv/signals_pilot.csv. "
        "Generate the pilot CRAAP signals before making rankings."
    )
for c in COLS:
    sig[c] = pd.to_numeric(sig[c], errors="coerce")
S = sig[COLS].to_numpy(dtype=float)

out = []
for name, w in SYSTEMS.items():
    w = np.array(w, dtype=float)
    avail = ~np.isnan(S)
    num = np.where(avail, S, 0.0) @ w
    den = avail.astype(float) @ w
    score = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
    d = sig[["query_id", "source_id", "s_sem"]].copy()
    d["score"] = score
    d["system"] = name
    d = d.dropna(subset=["score"])
    d = d.sort_values(["query_id", "score", "s_sem", "source_id"], ascending=[True, False, False, True])
    d["rank"] = d.groupby("query_id").cumcount() + 1
    out.append(d[["system", "query_id", "source_id", "rank", "score"]])

pd.concat(out).to_csv(CSV_DIR / "rankings_pilot.csv", index=False)
print("systems:", list(SYSTEMS), "| rows:", sum(len(o) for o in out))