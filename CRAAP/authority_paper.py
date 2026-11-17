import re
import pandas as pd

SJR_FILE = "scimagojr 2025.csv"
Q_SCORE = {"Q1": 1.0, "Q2": 0.75, "Q3": 0.5, "Q4": 0.25}
DEFAULT_SCORE = 0.50

def norm_issn(s):
    return re.sub(r"[^0-9Xx]", "", str(s)).upper()

def norm_title(s):
    s = re.sub(r"[^a-z0-9 ]", " ", str(s).lower())
    return re.sub(r"\s+", " ", s).strip()

# ---- load SCImago (journals, conference proceedings, book series, ...) ----
sjr = pd.read_csv(SJR_FILE, sep=";", dtype=str)
sjr.columns = sjr.columns.str.strip()
sjr = sjr[sjr["SJR Best Quartile"].isin(Q_SCORE)]
sjr["q_rank"] = sjr["SJR Best Quartile"].str[1].astype(int)

rows = []
for _, r in sjr.iterrows():
    for issn in str(r["Issn"]).split(","):
        i = norm_issn(issn)
        if len(i) == 8:
            rows.append((i, r["SJR Best Quartile"], r["q_rank"]))
issn_map = (pd.DataFrame(rows, columns=["issn", "quartile", "q_rank"])
              .sort_values("q_rank").drop_duplicates("issn")
              .set_index("issn")["quartile"].to_dict())

sjr["title_norm"] = sjr["Title"].apply(norm_title)
title_map = (sjr.sort_values("q_rank").drop_duplicates("title_norm")
                .set_index("title_norm")["SJR Best Quartile"].to_dict())

def lookup(row):
    for issn in re.split(r"[;,|]", str(row.get("issn", ""))):
        q = issn_map.get(norm_issn(issn))
        if q:
            return q, "sjr_issn"
    q = title_map.get(norm_title(row.get("venue", "")))
    if q:
        return q, "sjr_title"
    return None, None

# ---- apply ----
df = pd.read_csv("sources_papers.csv", dtype=str)
df.columns = df.columns.str.strip()

res = df.apply(lookup, axis=1, result_type="expand")
df["sjr_quartile"], df["authority_basis"] = res[0], res[1]
df["authority_score"] = df["sjr_quartile"].map(Q_SCORE)

is_paper = df["record_type"].str.strip().str.lower() == "paper"
unmatched = df["authority_score"].isna()

df.loc[is_paper & unmatched, "authority_score"] = DEFAULT_SCORE
df.loc[is_paper & unmatched, "authority_basis"] = "default"
df.loc[~is_paper & unmatched, "authority_basis"] = "n/a (web page)"

df.to_csv("authority_paper_pilot.csv", index=False)
print(df[["venue", "record_type", "sjr_quartile", "authority_basis", "authority_score"]])
print(df[is_paper]["authority_basis"].value_counts())