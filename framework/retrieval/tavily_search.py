"""Tavily retrieval for non-journal web sources. Needs TAVILY_API_KEY in .env."""
import os

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
API_KEY = os.getenv("TAVILY_API_KEY")

# Journal sites are covered by Crossref / Semantic Scholar. Skip them here.
EXCLUDE = ["doi.org", "sciencedirect.com", "springer.com", "ieeexplore.ieee.org"]


def search(query, topic_id="", max_results=10):
    """Return a list of candidate records for one topic."""
    if not API_KEY:
        raise RuntimeError("Set TAVILY_API_KEY in .env")

    client = TavilyClient(api_key=API_KEY)
    resp = client.search(
        query=query,
        max_results=max_results,
        search_depth="basic",
        exclude_domains=EXCLUDE,
    )

    records = []
    for item in resp.get("results", []):
        records.append({
            "topic_id": topic_id,
            "source_type": "web",
            "title": item.get("title", ""),
            "abstract": item.get("content", ""),  # snippet, not a real abstract
            "year": None,                          # htmldate fills this later (task 8)
            "venue": "",
            "doi": "",
            "url": item.get("url", ""),
            "citations": 0,
            "retrieved_from": "tavily",
        })
    return records


if __name__ == "__main__":
    results = search(
        "Software defect prediction using machine learning", topic_id="COMP04", max_results=5
    )
    for r in results:
        print(r["title"][:70], "|", r["url"])
    print(f"{len(results)} results")