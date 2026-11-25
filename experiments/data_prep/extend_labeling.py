"""extend_labeling.py - append 50 new pilot pairs to the existing labeling files.

Existing rows and ratings are never changed. The same new pairs are appended to
labeling_A1/A2/A3.csv. Originals are backed up first. New rows are chosen at random from
candidates_pilot.csv, skipping anything already in the sheets, peer-review/review records,
and duplicate URLs.
"""
import csv
import random
import re
import shutil
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
SHEET_DIR = DATA_DIR / "labeling" / "pilot"             # where your pilot labeling_A1/A2/A3.csv are
CANDIDATES = DATA_DIR / "retrieval" / "candidates_pilot.csv"
ANNOTATORS = ["A1", "A2", "A3"]
N_NEW_PER_TOPIC = 10                                   # 5 topics x 10 = 50 new pairs
TARGET_WEB = 6                                         # aim for about 6 web sources per topic in total
EXTRA_FOR_FLAGGED = False                              # True = also add one new pair per flagged old pair
SEED = 198

REVIEW_TITLE = re.compile(r"^\s*(?:review for|reply to|correction to|erratum|author response|decision letter)\b", re.I)
REVIEW_URL = re.compile(r"/v\d+/(?:review|decision|response)\d*/?$", re.I)


def nid(x):                                            # PIL01 and PIL1 -> PIL1
    return re.sub(r"^([A-Za-z]+)0*(\d+)$", r"\1\2", str(x).strip().upper())


def url_key(u):
    u = str(u).strip().lower()
    u = re.sub(r"^https?://(dx\.)?doi\.org/", "doi:", u)
    u = re.sub(r"^https?://(www\.)?", "", u)
    return u.rstrip("/")


def title_key(t):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(t).lower())).strip()


def read_sheet(path):
    """Read a labeling sheet; repairs rows where an unquoted comma split the author field."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    hdr = [h.strip() for h in rows[0]]
    n, ai = len(hdr), hdr.index("author")
    fixed = []
    for line_no, r in enumerate(rows[1:], start=2):
        if not any(x.strip() for x in r):
            continue
        extra = len(r) - n
        if extra > 0:
            print(f"  repaired {path.name} line {line_no}: unquoted comma in the author field")
            r = r[:ai] + [", ".join(r[ai:ai + extra + 1])] + r[ai + extra + 1:]
        elif extra < 0:
            raise ValueError(f"{path.name} line {line_no} has too few fields")
        fixed.append(r)
    df = pd.DataFrame(fixed, columns=hdr)
    bad = df[~df["suitability"].str.strip().isin(["", "0", "1", "2", "3"])]
    bad2 = df[~df["could_open"].str.strip().str.lower().isin(["", "yes", "no"])]
    if len(bad) or len(bad2):
        raise ValueError(f"{path.name}: unexpected values in suitability/could_open - check the rows near "
                         f"{bad.index.tolist() + bad2.index.tolist()} (a comma in another column?)")
    return df


def detect_web(c):
    for col in ("record_type", "source_type", "kind", "type"):
        if col in c.columns and c[col].str.strip().str.lower().isin(["web", "webpage", "web page"]).any():
            print(f"web sources detected from column '{col}'")
            return c[col].str.strip().str.lower().isin(["web", "webpage", "web page"])
    print("no record_type column found: treating rows without a venue and without a DOI as web pages (check!)")
    return (c["venue"] == "") & ~c["url"].str.contains("doi.org|arxiv.org", case=False)


# ---- existing sheets ----
sheets = {a: read_sheet(SHEET_DIR / f"labeling_{a}.csv") for a in ANNOTATORS if (SHEET_DIR / f"labeling_{a}.csv").exists()}
base = sheets[next(iter(sheets))]
keyset = lambda d: set(zip(d["query_id"].map(nid), d["source_id"]))
for a, d in sheets.items():
    print(f"{a}: {len(d)} rows, rated {(d['suitability'].str.strip() != '').sum()}")
    if keyset(d) != keyset(base):
        print(f"WARNING: {a} does not contain the same sources as the first sheet")
existing = keyset(base)
qstyle = dict(zip(base["query_id"].map(nid), base["query_id"]))        # keep the ID style used in the files
qtext = dict(zip(base["query_id"].map(nid), base["topic_text"]))

# ---- candidates ----
cand = pd.read_csv(CANDIDATES, dtype=str).fillna("")
cand.columns = cand.columns.str.strip()
if "query_id" not in cand.columns and "topic_id" in cand.columns:
    cand = cand.rename(columns={"topic_id": "query_id"})
for col in ["title", "venue", "url", "pub_date", "author", "work_type"]:
    if col not in cand.columns:
        cand[col] = ""
cand["qkey"] = cand["query_id"].map(nid)
cand = cand[cand["qkey"].isin(qstyle)].drop_duplicates(["qkey", "source_id"]).copy()
cand["is_web"] = detect_web(cand)
cand["is_review"] = (cand["work_type"].str.strip().str.lower().eq("peer-review")
                     | cand["title"].str.contains(REVIEW_TITLE) | cand["url"].str.contains(REVIEW_URL))
cand["ukey"], cand["tkey"] = cand["url"].apply(url_key), cand["title"].apply(title_key)

old = cand[[(q, s) in existing for q, s in zip(cand["qkey"], cand["source_id"])]]
if len(old) < len(existing):
    print(f"WARNING: {len(existing) - len(old)} labeled sources are not in the candidates file (ID mismatch?)")

flagged = old[old["is_review"]].merge(
    base.assign(qkey=base["query_id"].map(nid))[["qkey", "source_id", "suitability"]], on=["qkey", "source_id"])
print(f"\nlabeled pairs that look like peer-review/review records: {len(flagged)}")
if len(flagged):
    print(flagged[["query_id", "source_id", "title", "suitability"]].to_string(index=False, max_colwidth=60))
    flagged[["query_id", "source_id", "title", "suitability"]].to_csv(SHEET_DIR / "pilot_flagged_round1.csv", index=False)

# ---- pool of new candidates ----
used_u, used_t = set(zip(old["qkey"], old["ukey"])), set(zip(old["qkey"], old["tkey"]))
pool = cand[~cand["is_review"] & (cand["title"] != "") & (cand["url"] != "")]
pool = pool[[(q, s) not in existing for q, s in zip(pool["qkey"], pool["source_id"])]]
pool = pool[[(q, u) not in used_u for q, u in zip(pool["qkey"], pool["ukey"])]]
pool = pool[[(q, t) not in used_t for q, t in zip(pool["qkey"], pool["tkey"])]].drop_duplicates(["qkey", "ukey"])

# ---- sample new pairs per topic (random across retrieval ranks) ----
rng, parts = random.Random(SEED), []
for q in sorted(qstyle):
    oq, pq = old[old["qkey"] == q], pool[pool["qkey"] == q]
    need = N_NEW_PER_TOPIC + (int(oq["is_review"].sum()) if EXTRA_FOR_FLAGGED else 0)
    aw, asch = int(pq["is_web"].sum()), int((~pq["is_web"]).sum())
    ww = min(max(TARGET_WEB - int(oq["is_web"].sum()), 0), aw, need)
    ws = min(need - ww, asch)
    ww = min(need - ws, aw)
    if ww + ws < need:
        print(f"WARNING {qstyle[q]}: only {ww + ws} of {need} new pairs available")
    for flag, n in ((True, ww), (False, ws)):
        if n:
            parts.append(pq[pq["is_web"] == flag].sample(n=n, random_state=rng.randint(0, 10**9)))
new = pd.concat(parts)
new["query_id"] = new["qkey"].map(qstyle)
new["topic_text"] = new["qkey"].map(qtext)
cols = list(base.columns)
for c in ("suitability", "could_open", "note"):
    new[c] = ""
new[cols].assign(is_web=new["is_web"].values).to_csv(SHEET_DIR / "pilot_added_sources.csv", index=False)

# ---- append to every annotator's file (back up first) ----
for a, d in sheets.items():
    path = SHEET_DIR / f"labeling_{a}.csv"
    backup = path.with_name(f"labeling_{a}.backup_before_100.csv")
    if not backup.exists():
        shutil.copy(path, backup)
    block = new[cols].sample(frac=1, random_state=SEED + int(a[1]))
    pd.concat([d[cols], block]).to_csv(path, index=False)
    print(f"{a}: now {len(d) + len(block)} rows (backup: {backup.name})")

print("\nper topic: existing + new, web in new")
print(new.groupby("query_id").agg(new=("source_id", "size"), web_new=("is_web", "sum")).to_string())