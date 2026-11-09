"""Semantic Scholar retrieval. Key is optional but avoids tight rate limits."""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,year,venue,externalIds,url,citationCount"


def search(query, topic_id="", limit=50, from_year=2020, until_year=2026):
    """Return a list of candidate records for one topic."""
    headers = {"x-api-key": API_KEY} if API_KEY else {}
    params = {
        "query": query,
        "year": f"{from_year}-{until_year}",
        "limit": limit,
        "fields": FIELDS,
    }

    for attempt in range(4):
        resp = requests.get(URL, params=params, headers=headers, timeout=30)
        if resp.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        break
    else:
        return []

    time.sleep(1)  # stay under about 1 request per second

    records = []
    for item in resp.json().get("data", []):
        ids = item.get("externalIds") or {}
        records.append({
            "topic_id": topic_id,
            "source_type": "journal",
            "title": item.get("title") or "",
            "abstract": item.get("abstract") or "",
            "year": item.get("year"),
            "venue": item.get("venue") or "",
            "doi": (ids.get("DOI") or "").lower(),
            "url": item.get("url") or "",
            "citations": item.get("citationCount") or 0,
            "retrieved_from": "semantic_scholar",
        })
    return records


if __name__ == "__main__":
    results = search(
        "Software defect prediction using machine learning", topic_id="COMP04", limit=5
    )
    for r in results:
        print(r["year"], "|", r["title"][:70], "|", r["doi"])
    print(f"{len(results)} results")