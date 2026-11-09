"""Check that the API keys in .env work.

run:
pip install requests python-dotenv
python -m retrieval.check_keys

"""
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()


def report(name, ok, detail=""):
    print(f"[{'OK' if ok else 'FAIL'}] {name} {detail}")


def check_semantic_scholar():
    key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if not key:
        return report("Semantic Scholar", False, "- key is empty")
    r = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={"query": "machine learning", "limit": 1, "fields": "title,year"},
        headers={"x-api-key": key},
        timeout=15,
    )
    report("Semantic Scholar", r.ok, f"- HTTP {r.status_code}")


def check_tavily():
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return report("Tavily", False, "- key is empty")
    r = requests.post(
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {key}"},
        json={"query": "machine learning", "max_results": 1},
        timeout=15,
    )
    report("Tavily", r.ok, f"- HTTP {r.status_code}")


def check_crossref():
    mailto = os.getenv("CROSSREF_MAILTO")
    r = requests.get(
        "https://api.crossref.org/works",
        params={"query": "machine learning", "rows": 1, "mailto": mailto},
        timeout=15,
    )
    report("Crossref", r.ok, f"- HTTP {r.status_code}")


def check_supabase():
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
    if not url or not key:
        return print("[SKIP] Supabase - not set up yet")
    r = requests.get(
        f"{url.rstrip('/')}/rest/v1/",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=15,
    )
    report("Supabase", r.ok, f"- HTTP {r.status_code}")


if __name__ == "__main__":
    check_semantic_scholar()
    time.sleep(1)  # Semantic Scholar limit: 1 request per second
    check_tavily()
    check_crossref()
    check_supabase()