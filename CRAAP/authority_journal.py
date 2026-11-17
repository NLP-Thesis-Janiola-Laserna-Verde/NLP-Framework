import re
from pathlib import Path

import pandas as pd

CSV_DIR = Path(__file__).resolve().parents[1] / "csv"
SJR_FILE = CSV_DIR / "scimagojr 2025.csv"
Q_SCORE = {"Q1": 1.0, "Q2": 0.75, "Q3": 0.5, "Q4": 0.25}   # tunable

def norm_issn(s):
    return re.sub(r"[^0-9Xx]", "", str(s)).upper()

def norm_title(s):
    s = re.sub(r"[^a-z0-9 ]", " ", str(s).lower())
    return re.sub(r"\s+", " ", s).strip()

# ---- load SCImago ----
sjr = pd.read_csv(SJR_FILE, sep=";", dtype=str)
sjr.columns = sjr.columns.str.strip()
sjr = sjr[sjr["SJR Best Quartile"].isin(Q_SCORE)]          # drops "-" rows
sjr["q_rank"] = sjr["SJR Best Quartile"].str[1].astype(int)

# one row per ISSN
rows = []
for _, r in sjr.iterrows():
    for issn in str(r["Issn"]).split(","):
        i = norm_issn(issn)
        if len(i) == 8:
            rows.append((i, r["SJR Best Quartile"], r["q_rank"]))
issn_map = (pd.DataFrame(rows, columns=["issn", "quartile", "q_rank"])
              .sort_values("q_rank").drop_duplicates("issn")
              .set_index("issn")["quartile"].to_dict())

# one row per normalized title (keep the best quartile on ties)
sjr["title_norm"] = sjr["Title"].apply(norm_title)
title_map = (sjr.sort_values("q_rank").drop_duplicates("title_norm")
                .set_index("title_norm")["SJR Best Quartile"].to_dict())

# ---- look up each source ----
def lookup(row):
    for issn in re.split(r"[;,|]", str(row.get("issn", ""))):
        q = issn_map.get(norm_issn(issn))
        if q:
            return q, "issn"
    q = title_map.get(norm_title(row.get("journal", "")))
    if q:
        return q, "title"
    return None, None

df = pd.read_csv(CSV_DIR / "sources_journals.csv", dtype=str)
df.columns = df.columns.str.strip()
res = df.apply(lookup, axis=1, result_type="expand")
df["sjr_quartile"], df["sjr_match"] = res[0], res[1]
df["sjr_found"] = df["sjr_quartile"].notna()
df["sjr_score"] = df["sjr_quartile"].map(Q_SCORE)

df.to_csv(CSV_DIR / "authority_journal_pilot.csv", index=False)
print(df[["journal", "issn", "sjr_quartile", "sjr_match", "sjr_score"]])
print("match rate:", df["sjr_found"].mean())