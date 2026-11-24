import pandas as pd
from pathlib import Path

CSV_DIR = Path(__file__).resolve().parents[1] / "csv"
labels = pd.read_csv(CSV_DIR / "labels.csv")

g = labels.groupby(["query_id", "source_id"])["suitability"]
agg = g.agg(n="count", n_unique="nunique", final="median")

ready = agg[(agg["n"] == 3) | ((agg["n"] == 2) & (agg["n_unique"] == 1))].copy()
ready["final"] = ready["final"].astype(int)
ready["suitable"] = (ready["final"] >= 2).astype(int)   # cutoff from decisions.md
ready.reset_index().to_csv(CSV_DIR / "final_labels.csv", index=False)

pending = agg[(agg["n"] == 2) & (agg["n_unique"] > 1)]
print("final labels:", len(ready), "| waiting for a tiebreak:", len(pending))