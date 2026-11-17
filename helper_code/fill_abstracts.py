import sys
from pathlib import Path

import pandas as pd
import trafilatura

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = PROJECT_ROOT / "csv"
sys.path.append(str(PROJECT_ROOT))
from retrieval.clean_text import clean_text

MAX_CHARS = 1000

def get_snippet(url):
    html = trafilatura.fetch_url(url)
    if not html:
        raise RuntimeError("download failed")
    meta = trafilatura.extract_metadata(html)
    if meta and meta.description:
        return clean_text(meta.description, single_line=True)[:MAX_CHARS]
    text = trafilatura.extract(html)
    return clean_text(text, single_line=True)[:MAX_CHARS]

df = pd.read_csv(CSV_DIR / "sources.csv", dtype=str)   # read everything as text
df.columns = df.columns.str.strip()
print("columns:", df.columns.tolist())

if "abstract" not in df.columns:
    df["abstract"] = ""
df["abstract"] = df["abstract"].fillna("").astype(str)

for i, row in df.iterrows():
    if row["abstract"].strip():
        continue                      # keep real abstracts from the APIs
    try:
        snippet = get_snippet(row["url"])
        df.at[i, "abstract"] = snippet
        print("OK  ", row["url"], "->", len(snippet), "chars")
    except Exception as e:
        print("FAIL", row["url"], "->", e)

df["abstract_found"] = df["abstract"].str.strip() != ""
df.to_csv(CSV_DIR / "sources_with_abstracts.csv", index=False)