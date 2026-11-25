import pandas as pd
from pathlib import Path

SIGNALS = Path("data/signals")   # run from the project root
Q = {"Q1": 1.0, "Q2": 0.75, "Q3": 0.5, "Q4": 0.25}

def blank(s):
    return s.fillna("").astype(str).str.strip().eq("")

# ---- journals ----
j = pd.read_csv(SIGNALS / "authority_journal_pilot.csv", dtype=str)
j["sjr_score"] = pd.to_numeric(j["authority_score"])
has_info = ~(blank(j["venue"]) & blank(j["issn"]))
found = j["sjr_quartile"].notna()

assert (j.loc[found, "sjr_score"] == j.loc[found, "sjr_quartile"].map(Q)).all(), "ranked rows wrong"
assert (j.loc[has_info & ~found, "sjr_score"] == 0.0).all(), "unranked should be 0.0"
assert j.loc[~has_info, "sjr_score"].isna().all(), "no-info should be NaN"
print("journals OK:", len(j), "rows |", int((has_info & ~found).sum()), "unranked,",
      int((~has_info).sum()), "no-info")

# ---- papers ----
p = pd.read_csv(SIGNALS / "authority_paper_pilot.csv", dtype=str)
p["authority_score"] = pd.to_numeric(p["authority_score"])
paper = p["record_type"].str.strip().str.lower().eq("paper")
has_j = ~(blank(p["venue"]) & blank(p["issn"]))
sjr_ranked = p["authority_basis"].fillna("").str.startswith("sjr_") & ~p["authority_basis"].eq("sjr_unranked")

assert (p.loc[paper & has_j & ~sjr_ranked, "authority_score"] == 0.0).all(), "unranked papers should be 0.0"
assert p.loc[paper & ~has_j, "authority_score"].isna().all(), "no-journal papers should be NaN"
assert p.loc[~paper, "authority_basis"].eq("n/a (web page)").all(), "web rows mislabeled"
print("papers OK:", p["authority_basis"].value_counts(dropna=False).to_dict())

# ---- combined ----
s = pd.read_csv(SIGNALS / "signals_pilot.csv", index_col="source_id")
for sid in p.loc[paper & has_j & ~sjr_ranked, "source_id"] if "source_id" in p else []:
    assert s.loc[sid, "s_auth"] == 0.0, f"{sid} lost its 0.0 in combine"
print("signals OK: s_auth zeros =", int((s["s_auth"] == 0).sum()),
      "| NaN =", int(s["s_auth"].isna().sum()))