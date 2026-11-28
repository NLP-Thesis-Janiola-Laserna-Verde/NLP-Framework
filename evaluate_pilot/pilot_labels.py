"""pilot_labels.py - check the three pilot labeling files, compute agreement, build final labels.

Reads  data/labeling/pilot/labeling_A1/A2/A3.csv,
       data/labeling/pilot/pilot_flagged_round1.csv (optional)
Writes csv/final_labels_pilot.csv (query_id, source_id, final, suitable),
       data/labeling/pilot/pilot_disagreements.csv
"""
import itertools
import re
from pathlib import Path

import krippendorff
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

CSV_DIR = Path(__file__).resolve().parents[1] / "csv"
SHEET_DIR = Path(__file__).resolve().parents[1] / "data" / "labeling" / "pilot"
ANN = ["A1", "A2", "A3"]
CUTOFF = 2                      # must match decisions.md


def nid(x):                     # PIL01 and PIL1 -> PIL1
    return re.sub(r"^([A-Za-z]+)0*(\d+)$", r"\1\2", str(x).strip().upper())


frames = []
for a in ANN:
    d = pd.read_csv(SHEET_DIR / f"labeling_{a}.csv", dtype=str).fillna("")
    d["annotator_id"] = a
    frames.append(d)
raw = pd.concat(frames)
raw["query_id"] = raw["query_id"].map(nid)
print("rows per annotator:", raw.groupby("annotator_id").size().to_dict())

# ---- completeness ----
blank = raw[raw["suitability"].str.strip() == ""]
no_open = raw[raw["could_open"].str.strip().str.lower() == "no"]
print("unrated rows:", len(blank), "| could_open = no:", len(no_open))
if len(blank):
    print(blank.groupby("annotator_id").size().to_dict(), "<- finish these before continuing")

rated = raw[raw["suitability"].str.strip() != ""].copy()
rated["suitability"] = rated["suitability"].astype(int)
assert rated["suitability"].isin([0, 1, 2, 3]).all(), "suitability must be 0-3"

# ---- exclusions: flagged peer-review pairs ----
flag_path = SHEET_DIR / "pilot_flagged_round1.csv"
if flag_path.exists():
    fl = pd.read_csv(flag_path, dtype=str)
    flagged = set(zip(fl["query_id"].map(nid), fl["source_id"]))
    rated = rated[[(q, s) not in flagged for q, s in zip(rated["query_id"], rated["source_id"])]]
    print("excluded flagged pairs:", len(flagged))

# ---- drop pairs that any rater could not open ----
cant = raw[raw["could_open"].str.strip().str.lower() == "no"][["query_id", "source_id"]].drop_duplicates()
cant_set = set(zip(cant["query_id"], cant["source_id"]))
rated = rated[[(q, s) not in cant_set for q, s in zip(rated["query_id"], rated["source_id"])]]
print("dropped pairs (someone could not open):", len(cant_set))

# ---- keep only pairs rated by all three ----
w = rated.pivot_table(index=["query_id", "source_id"], columns="annotator_id",
                      values="suitability", aggfunc="first")
incomplete = w[w.isna().any(axis=1)]
print("pairs without all three ratings (dropped):", len(incomplete))
w = w.dropna().astype(int)
print("pairs used:", len(w), "| per topic:", w.groupby(level=0).size().to_dict())

# ---- agreement ----
ks = [cohen_kappa_score(w[a], w[b], weights="quadratic", labels=[0, 1, 2, 3])
      for a, b in itertools.combinations(ANN, 2)]
alpha = krippendorff.alpha(reliability_data=w.T.values.astype(float), level_of_measurement="ordinal")
bw = (w >= CUTOFF).astype(int)
bk = [cohen_kappa_score(bw[a], bw[b]) for a, b in itertools.combinations(ANN, 2)]
print(f"\nweighted kappa per pair: {np.round(ks, 2).tolist()} (mean {np.mean(ks):.2f})")
print(f"Krippendorff alpha (ordinal): {alpha:.2f}")
print(f"binary kappa at >= {CUTOFF}: {np.round(bk, 2).tolist()} (mean {np.mean(bk):.2f})")
print(f"exact agreement: {(w.nunique(axis=1) == 1).mean():.2f} | within 1 point: {((w.max(axis=1) - w.min(axis=1)) <= 1).mean():.2f}")
print("rating distribution:", w.stack().value_counts().sort_index().to_dict())

# ---- extra diagnostics ----
print("mean rating per annotator:", w.mean().round(2).to_dict())
added = pd.read_csv(SHEET_DIR / "pilot_added_sources.csv", dtype=str)
is_r2 = w.index.get_level_values("source_id").isin(set(added["source_id"]))
for name, sub in (("round 1", w[~is_r2]), ("round 2", w[is_r2])):
    k = [cohen_kappa_score(sub[a], sub[b], weights="quadratic", labels=[0, 1, 2, 3])
         for a, b in itertools.combinations(ANN, 2)]
    al = krippendorff.alpha(reliability_data=sub.T.values.astype(float), level_of_measurement="ordinal")
    print(f"{name}: n={len(sub)} kappa={np.mean(k):.2f} alpha={al:.2f} exact={(sub.nunique(axis=1) == 1).mean():.2f}")
split = ((w.min(axis=1) < CUTOFF) & (w.max(axis=1) >= CUTOFF)).mean()
print(f"pairs where raters split across the cutoff ({CUTOFF}): {split:.2f}")

# ---- disagreements to discuss ----
info = raw.drop_duplicates(["query_id", "source_id"]).set_index(["query_id", "source_id"])[["title", "url"]]
dis = w[(w.max(axis=1) - w.min(axis=1)) >= 2].join(info)
dis.to_csv(SHEET_DIR / "pilot_disagreements.csv")
print("large disagreements (range >= 2):", len(dis), "-> pilot_disagreements.csv")

# ---- final labels: median of the three raters ----
final = pd.DataFrame({"final": w.median(axis=1).astype(int)})
final["suitable"] = (final["final"] >= CUTOFF).astype(int)
final = final.reset_index()
final.to_csv(CSV_DIR / "final_labels_pilot.csv", index=False)
g = final.groupby("query_id")["suitable"].agg(["sum", "count"])
g["unsuitable"] = g["count"] - g["sum"]
print("\nper topic (suitable / total):\n", g.to_string())
print("topics without a suitable or an unsuitable pair:", g[(g["sum"] == 0) | (g["unsuitable"] == 0)].index.tolist() or "none")