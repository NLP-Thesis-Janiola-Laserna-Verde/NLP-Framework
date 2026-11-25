from pathlib import Path

import pandas as pd
from sentence_transformers import SentenceTransformer, util

MODEL_NAME = "all-MiniLM-L6-v2"
DATA_DIR = Path(__file__).resolve().parents[3] / "data"

topics = pd.read_csv(DATA_DIR / "topics" / "topics.csv")
sources = pd.read_csv(DATA_DIR / "sources" / "sources_with_abstracts.csv")

# build the text to embed for each source
sources["title"] = sources["title"].fillna("")
if "abstract" not in sources.columns:
    sources["abstract"] = ""
sources["abstract"] = sources["abstract"].fillna("")
sources["text"] = (sources["title"] + ". " + sources["abstract"]).str.strip(". ")

# attach each source's topic text
df = sources.merge(topics[["topic_id", "topic_text"]], on="topic_id", how="left")
bad = df[df["topic_text"].isna()]
print(len(bad), "rows with no topic match")
print(bad[["source_id", "topic_id"]])

model = SentenceTransformer(MODEL_NAME)

topic_emb = model.encode(df["topic_text"].tolist(),
                         convert_to_tensor=True, normalize_embeddings=True,
                         show_progress_bar=True)
source_emb = model.encode(df["text"].tolist(),
                          convert_to_tensor=True, normalize_embeddings=True,
                          show_progress_bar=True)

# row-by-row cosine similarity (topic i vs source i)
df["relevance_raw"] = util.cos_sim(topic_emb, source_emb).diagonal().cpu().numpy()
df["relevance"] = df["relevance_raw"].clip(0, 1)
# no title/abstract text or no topic match -> null, not a made-up similarity
df.loc[df["text"].eq("") | df["topic_text"].isna(), ["relevance_raw", "relevance"]] = float("nan")

df.to_csv(DATA_DIR / "signals" / "relevance_pilot.csv", index=False)
print(df[["topic_id", "title", "relevance"]].sort_values("relevance", ascending=False))