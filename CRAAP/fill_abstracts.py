import pandas as pd
import trafilatura

MAX_CHARS = 1000

def get_snippet(url):
    html = trafilatura.fetch_url(url)
    if not html:
        raise RuntimeError("download failed")
    meta = trafilatura.extract_metadata(html)
    if meta and meta.description:
        return meta.description.strip()[:MAX_CHARS]
    text = trafilatura.extract(html)
    return (text or "").strip()[:MAX_CHARS]

df = pd.read_csv("sources.csv", dtype=str)   # read everything as text
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
df.to_csv("sources_with_abstracts.csv", index=False)