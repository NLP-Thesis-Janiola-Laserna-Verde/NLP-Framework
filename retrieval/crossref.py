"""Crossref retrieval. No API key needed, only CROSSREF_MAILTO in .env."""

import os
import re
import time

import requests
from dotenv import load_dotenv

load_dotenv()
MAILTO = os.getenv("CROSSREF_MAILTO")
URL = "https://api.crossref.org/works"
FIELDS = "DOI,title,abstract,issued,container-title,URL,is-referenced-by-count,type"


def _clean_abstract(raw):
    """Crossref abstracts come as JATS XML. Strip the tags."""
    if not raw:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)).strip()


def _first(value):
    """title and container-title are lists."""
    return value[0] if value else ""


def _year(item):
    parts = item.get("issued", {}).get("date-parts", [[None]])
    return parts[0][0] if parts and parts[0] else None


def search(query, topic_id="", rows=50, from_year=2020, until_year=2026):
    """Return a list of candidate records for one topic."""
    if not MAILTO:
        raise RuntimeError("Set CROSSREF_MAILTO in .env")

    params = {
        "query.bibliographic": query,
        "filter": f"from-pub-date:{from_year},until-pub-date:{until_year}",
        "rows": rows,
        "select": FIELDS,
        "mailto": MAILTO,
    }

    for attempt in range(3):
        resp = requests.get(URL, params=params, timeout=30)
        if resp.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        break
    else:
        return []

    records = []
    for item in resp.json()["message"]["items"]:
        records.append({
            "topic_id": topic_id,
            "source_type": "journal",
            "title": _first(item.get("title")),
            "abstract": _clean_abstract(item.get("abstract")),
            "year": _year(item),
            "venue": _first(item.get("container-title")),
            "doi": (item.get("DOI") or "").lower(),
            "url": item.get("URL", ""),
            "citations": item.get("is-referenced-by-count", 0),
            "retrieved_from": "crossref",
        })
    return records


if __name__ == "__main__":
    results = search(
        "Software defect prediction using machine learning", topic_id="COMP04", rows=5
    )
    for r in results:
        print(r["year"], "|", r["title"][:80], "|", r["doi"])
    print(f"{len(results)} results")