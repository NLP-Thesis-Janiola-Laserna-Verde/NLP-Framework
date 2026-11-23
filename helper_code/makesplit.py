from pathlib import Path
import pandas as pd

CSV_DIR = Path(__file__).resolve().parents[1] / "csv"
df = pd.read_csv(CSV_DIR / "topics.csv", dtype=str)
df.columns = df.columns.str.strip()
df["set"] = df["set"].str.strip().str.lower()

main = df[df["set"] != "pilot"]
counts = main.groupby(["field", "set"]).size().unstack(fill_value=0)
print(counts)

# checks
assert len(df) == 55, f"expected 55 topics, got {len(df)}"
assert df["topic_id"].is_unique, "duplicate topic_id"
assert (df["set"] == "pilot").sum() == 5, "expected 5 pilot topics"
assert (counts["tuning"] == 6).all(), "tuning must be 6 per field"
assert (counts["validation"] == 2).all(), "validation must be 2 per field"
assert (counts["test"] == 2).all(), "test must be 2 per field"
print("split OK")

df[["topic_id", "field", "set", "topic_text"]].to_csv(CSV_DIR / "topic_split.csv", index=False)
df[df["set"] == "test"][["topic_id", "field", "topic_text"]].to_csv(CSV_DIR / "test_topics_FROZEN.csv", index=False)
