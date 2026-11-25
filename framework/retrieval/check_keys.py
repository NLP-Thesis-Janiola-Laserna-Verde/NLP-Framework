"""Check that the API keys in .env work.

run:
pip install requests python-dotenv
python -m framework.retrieval.check_keys

"""
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()


def report(name, ok, detail=""):
    print(f"[{'OK' if ok else 'FAIL'}] {name} {detail}")


def safe_request(method, name, url, **kwargs):
    try:
        return requests.request(method, url, **kwargs)
    except requests.exceptions.Timeout:
        report(name, False, "- timeout")
    except requests.exceptions.ConnectionError as exc:
        if "Failed to resolve" in str(exc) or "NameResolutionError" in repr(exc):
            report(name, False, "- DNS resolution failed")
        else:
            report(name, False, f"- network error: {exc.__class__.__name__}")
    except requests.exceptions.RequestException as exc:
        report(name, False, f"- network error: {exc.__class__.__name__}")
    return None


def check_semantic_scholar():
    key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if not key:
        return report("Semantic Scholar", False, "- key is empty")
    r = safe_request(
        "GET",
        "Semantic Scholar",
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={"query": "machine learning", "limit": 1, "fields": "title,year"},
        headers={"x-api-key": key},
        timeout=15,
    )
    if r is not None:
        report("Semantic Scholar", r.ok, f"- HTTP {r.status_code}")


def check_tavily():
    key = os.getenv("TAVILY_API_KEY")
    if not key:
        return report("Tavily", False, "- key is empty")
    r = safe_request(
        "POST",
        "Tavily",
        "https://api.tavily.com/search",
        headers={"Authorization": f"Bearer {key}"},
        json={"query": "machine learning", "max_results": 1},
        timeout=15,
    )
    if r is not None:
        report("Tavily", r.ok, f"- HTTP {r.status_code}")


def check_crossref():
    mailto = os.getenv("CROSSREF_MAILTO")
    r = safe_request(
        "GET",
        "Crossref",
        "https://api.crossref.org/works",
        params={"query": "machine learning", "rows": 1, "mailto": mailto},
        timeout=15,
    )
    if r is not None:
        report("Crossref", r.ok, f"- HTTP {r.status_code}")


def check_supabase():
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
    if not url or not key:
        return print("[SKIP] Supabase - not set up yet")
    r = safe_request(
        "GET",
        "Supabase",
        f"{url.rstrip('/')}/rest/v1/",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=15,
    )
    if r is not None:
        report("Supabase", r.ok, f"- HTTP {r.status_code}")


if __name__ == "__main__":
    check_semantic_scholar()
    time.sleep(1)  # Semantic Scholar limit: 1 request per second
    check_tavily()
    check_crossref()
    check_supabase()