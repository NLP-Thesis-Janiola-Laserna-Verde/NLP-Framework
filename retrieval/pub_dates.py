"""Publication dates: htmldate for web pages, Crossref / Semantic Scholar for papers.

Main entry point: get_pub_date(url, record_type=None, doi=None, title=None)
returns (date or None, source) where source is "htmldate", "crossref" or "semantic_scholar".
A missing date is always None, never a guess.
"""
import os
import re
import time
from datetime import date
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from htmldate import find_date

load_dotenv()
MAILTO = os.getenv("CROSSREF_MAILTO")
S2_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

CROSSREF_URL = "https://api.crossref.org/works/"
S2_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper/"
S2_FIELDS = "title,publicationDate,year"

_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s?#]+", re.IGNORECASE)


# ---------- helpers ----------

def doi_from_url(url):
    """Pull a DOI out of a URL like https://doi.org/10.1038/s41586-021-03819-2, else None."""
    m = _DOI_RE.search(str(url or ""))
    return m.group(0).rstrip(".,;)").lower() if m else None


def _norm_title(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def _get_json(url, params=None, headers=None, attempts=3):
    """GET with a short retry on 429. Returns parsed JSON or None on any failure."""
    for attempt in range(attempts):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
        except requests.RequestException:
            return None
        if resp.status_code == 429:
            time.sleep(2 ** attempt)
            continue
        if resp.status_code != 200:
            return None
        try:
            return resp.json()
        except ValueError:
            return None
    return None


def _parts_to_date(parts):
    """Crossref date-parts [[2024, 5, 3]] -> date. Missing month/day default to 1."""
    if not parts or not parts[0] or parts[0][0] is None:
        return None
    p = list(parts[0]) + [1, 1]
    try:
        return date(int(p[0]), int(p[1] or 1), int(p[2] or 1))
    except (TypeError, ValueError):
        return None


# ---------- Crossref ----------

def parse_crossref(message):
    """Earliest sensible publication date from a Crossref work record."""
    for key in ("issued", "published-online", "published-print", "published"):
        d = _parts_to_date((message.get(key) or {}).get("date-parts"))
        if d:
            return d
    return None


def crossref_date(doi):
    if not doi:
        return None
    params = {"mailto": MAILTO} if MAILTO else None
    data = _get_json(CROSSREF_URL + quote(doi, safe="/"), params=params)
    return parse_crossref((data or {}).get("message", {}))


# ---------- Semantic Scholar ----------

def parse_semantic_scholar(item):
    """publicationDate is YYYY-MM-DD when known. Otherwise fall back to Jan 1 of the year."""
    if not item:
        return None
    pd_str = item.get("publicationDate")
    if pd_str:
        try:
            return date.fromisoformat(pd_str)
        except ValueError:
            pass
    year = item.get("year")
    if year:
        try:
            return date(int(year), 1, 1)
        except (TypeError, ValueError):
            pass
    return None


def semantic_scholar_date(doi=None, title=None):
    headers = {"x-api-key": S2_KEY} if S2_KEY else None
    if doi:
        data = _get_json(f"{S2_PAPER_URL}DOI:{quote(doi, safe='/')}",
                         params={"fields": S2_FIELDS}, headers=headers)
        return parse_semantic_scholar(data)
    if title:
        data = _get_json(S2_PAPER_URL + "search",
                         params={"query": title, "limit": 1, "fields": S2_FIELDS},
                         headers=headers)
        hits = (data or {}).get("data") or []
        # only trust the top hit when the title matches exactly (ignoring case/punctuation)
        if hits and _norm_title(hits[0].get("title")) == _norm_title(title):
            return parse_semantic_scholar(hits[0])
    return None


def paper_date(doi=None, title=None):
    """Crossref first, Semantic Scholar as fallback. Returns (date, source) or (None, None)."""
    d = crossref_date(doi)
    if d:
        return d, "crossref"
    d = semantic_scholar_date(doi=doi, title=title)
    if d:
        return d, "semantic_scholar"
    return None, None


# ---------- web pages ----------

def web_date(url_or_html):
    """Publication date of a web page via htmldate (url or raw HTML). None if not found."""
    try:
        d = find_date(url_or_html, original_date=True, extensive_search=True)
        return date.fromisoformat(d) if d else None
    except Exception:
        return None


# ---------- one entry point ----------

def get_pub_date(url, record_type=None, doi=None, title=None):
    """(date, source). Papers use Crossref/Semantic Scholar, web pages use htmldate."""
    doi = doi or doi_from_url(url)
    if doi or str(record_type or "").strip().lower() == "paper":
        d, src = paper_date(doi=doi, title=title)
        if d:
            return d, src
    d = web_date(url) if url else None
    return (d, "htmldate") if d else (None, None)