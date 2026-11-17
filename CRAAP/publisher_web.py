import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = PROJECT_ROOT / "csv"
sys.path.append(str(PROJECT_ROOT))
from retrieval.publisher import publisher_from_url

df = pd.read_csv(CSV_DIR / "sources_web.csv", dtype=str)
df.columns = df.columns.str.strip()

is_web = df["record_type"].str.strip().str.lower() == "web"
df["publisher"] = None
df["publisher_basis"] = "n/a (paper)"

res = df.loc[is_web, "url"].apply(publisher_from_url)
df.loc[is_web, "publisher"] = res.apply(lambda r: r[0])
df.loc[is_web, "publisher_basis"] = res.apply(lambda r: r[1])

df.to_csv(CSV_DIR / "publisher_web_pilot.csv", index=False)
print(df[["source_id", "url", "publisher", "publisher_basis"]])