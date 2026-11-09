"""Dedupe candidates by DOI/URL and save them to CSV (one file per topic)."""
import csv
import re
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

COLUMNS = [
    "topic_id", "source_type", "title", "abstract", "year", "venue",
    "doi", "url", "citations", "retrieved_from",
]
OUT_DIR = Path("data/candidates")  # not data/raw (gitignored)


def norm_doi(doi):
    doi = (doi or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)


def norm_url(url):
    url = (url or "").strip()
    if not url:
        return ""
    p = urlparse(url.lower())
    host = p.netloc.removeprefix("www.")
    query = urlencode(
        [(k, v) for k, v in parse_qsl(p.query) if not k.startswith("utm_")]
    )
    return urlunparse((p.scheme, host, p.path.rstrip("/"), "", query, ""))


def norm_title(title):
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def _filled(rec):
    return sum(1 for c in COLUMNS if rec.get(c) not in (None, "", 0))


def dedupe(records):
    """Keep one record per DOI, URL, or title. Prefer the most complete one."""
    best = {}      # key -> record
    key_of = {}    # every known key -> canonical key
    for rec in records:
        rec = dict(rec)
        rec["doi"] = norm_doi(rec.get("doi"))
        keys = [k for k in (
            f"doi:{rec['doi']}" if rec["doi"] else "",
            f"url:{norm_url(rec.get('url'))}" if rec.get("url") else "",
            f"title:{norm_title(rec.get('title'))}" if rec.get("title") else "",
        ) if k]
        if not keys:
            continue
        canon = next((key_of[k] for k in keys if k in key_of), keys[0])
        if canon not in best or _filled(rec) > _filled(best[canon]):
            best[canon] = rec
        for k in keys:
            key_of[k] = canon
    return list(best.values())


def save_csv(records, topic_id, out_dir=OUT_DIR):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{topic_id}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(records)
    return path


if __name__ == "__main__":
    import pandas as pd
    from retrieval import crossref, semantic_scholar, tavily_search

    topics = pd.read_csv("docs/topics.csv")
    topics = topics.head(2)  # test on 2 topics first, then remove this line
    for _, t in topics.iterrows():
        records = (
            crossref.search(t["topic_text"], topic_id=t["topic_id"])
            + semantic_scholar.search(t["topic_text"], topic_id=t["topic_id"])
            + tavily_search.search(t["topic_text"], topic_id=t["topic_id"])
        )
        unique = dedupe(records)
        path = save_csv(unique, t["topic_id"])
        print(f"{t['topic_id']}: {len(records)} -> {len(unique)} saved to {path}")