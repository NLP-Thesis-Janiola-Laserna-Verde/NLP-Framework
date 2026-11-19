# retrieve_candidates.py
# Retrieves candidate sources for the topics in topics.csv, ONCE, and caches the raw API responses.
#
# Run from the repo root:
#   python retrieve_candidates.py --sets pilot
#   python retrieve_candidates.py --sets tuning validation test
#
# Raw responses are cached in data/retrieval/raw/ re-running does NOT query the APIs again
# (it only rebuilds the CSV). Delete a cached file by hand if you really need to re-retrieve it.

import argparse, hashlib, json, os, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import pandas as pd
import requests
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
S2_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
MAILTO = (os.getenv("CROSSREF_MAILTO") or "").split("#")[0].strip()
TAVILY_KEY = os.getenv("TAVILY_API_KEY")

S2_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,abstract,year,publicationDate,venue,publicationTypes,externalIds,url,openAccessPdf,authors"

# Tavily is meant to supply NON-journal sources, so it excludes the big publisher/aggregator sites.
EXCLUDE = ["sciencedirect.com", "springer.com", "nature.com", "wiley.com", "tandfonline.com",
           "ieee.org", "acm.org", "arxiv.org", "semanticscholar.org", "researchgate.net",
           "jstor.org", "mdpi.com", "frontiersin.org", "sagepub.com", "ncbi.nlm.nih.gov"]

SERVICES = ["semantic_scholar", "crossref", "tavily"]   # order used for round-robin merging
SCHOLARLY = {"semantic_scholar", "crossref"}


# ---------------------------------------------------------------- fetchers (return None on failure)
def fetch_s2(q):
    headers = {"x-api-key": S2_KEY} if S2_KEY else {}
    r = None
    for attempt in range(5):
        r = requests.get(S2_URL, params={"query": q, "limit": 20, "fields": S2_FIELDS},
                         headers=headers, timeout=30)
        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            try:
                delay = min(max(float(retry_after), 0), 120) if retry_after else min(5 * (attempt + 1), 60)
            except ValueError:
                delay = min(5 * (attempt + 1), 60)
            time.sleep(delay)
            continue
        break
    if r is None or r.status_code != 200:
        print("  Semantic Scholar failed:", getattr(r, "status_code", "no response")); return None
    return r.json().get("data", [])


def fetch_crossref(q):
    params = {"query.bibliographic": q, "rows": 20,
              "select": "DOI,title,container-title,publisher,issued,type,URL,abstract,author"}
    if MAILTO:
        params["mailto"] = MAILTO
    try:
        r = requests.get("https://api.crossref.org/works", params=params, timeout=30)
    except requests.RequestException as e:
        print("  Crossref failed:", e); return None
    if r.status_code != 200:
        print("  Crossref failed:", r.status_code); return None
    return r.json()["message"]["items"]


def fetch_tavily(q):
    try:
        res = TavilyClient(api_key=TAVILY_KEY).search(q, max_results=20, exclude_domains=EXCLUDE)
        return res["results"]
    except Exception as e:
        print("  Tavily failed:", e); return None


FETCHERS = {"semantic_scholar": fetch_s2, "crossref": fetch_crossref, "tavily": fetch_tavily}


def cached(path, query, fn):
    """Return the cached raw response if it exists; otherwise fetch and save it (failures are not cached)."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    data = fn(query)
    if data is None:
        return {"query": query, "retrieved_at": None, "data": None}
    obj = {"query": query, "retrieved_at": datetime.now(timezone.utc).isoformat(), "data": data}
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    time.sleep(1)
    return obj


# ---------------------------------------------------------------- normalization helpers
def norm_doi(d):
    if not d:
        return None
    d = d.strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d or None


def canon_url(u):
    if not u:
        return None
    p = urlparse(u.strip())
    host = p.netloc.lower().removeprefix("www.")
    q = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith("utm_")
         and k.lower() not in {"fbclid", "gclid", "ref"}]
    return urlunparse(("https", host, p.path.rstrip("/"), "", urlencode(q), "")) or None


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip() or None


def rec(service, rank, **kw):
    base = {"title": None, "url": None, "doi": None, "authors": None, "publisher": None,
            "venue": None, "pub_year": None, "pub_date": None, "abstract": None,
            "work_type": None, "open_access": None}
    base.update(kw)
    base["doi"] = norm_doi(base["doi"])
    base["services"] = {service}
    base["order"] = None
    base["svc_rank"] = rank
    return base


def norm_s2(items):
    out = []
    for i, p in enumerate(items or []):
        doi = (p.get("externalIds") or {}).get("DOI")
        names = [a.get("name") for a in (p.get("authors") or [])[:5] if a.get("name")]
        out.append(rec("semantic_scholar", i, title=p.get("title"), url=p.get("url"), doi=doi,
                       authors="; ".join(names) or None, venue=p.get("venue") or None,
                       pub_year=p.get("year"), pub_date=p.get("publicationDate"),
                       abstract=p.get("abstract"),
                       work_type=";".join(p.get("publicationTypes") or []) or None,
                       open_access=bool((p.get("openAccessPdf") or {}).get("url"))))
    return out


def norm_crossref(items):
    out = []
    for i, p in enumerate(items or []):
        parts = ((p.get("issued") or {}).get("date-parts") or [[None]])[0]
        year = parts[0] if parts else None
        date = "-".join(f"{x:02d}" if j else str(x) for j, x in enumerate(parts) if x) or None
        names = [" ".join(filter(None, [a.get("given"), a.get("family")])) for a in (p.get("author") or [])[:5]]
        title = (p.get("title") or [None])[0]
        out.append(rec("crossref", i, title=title, url=p.get("URL"), doi=p.get("DOI"),
                       authors="; ".join(n for n in names if n) or None,
                       publisher=p.get("publisher"),
                       venue=(p.get("container-title") or [None])[0],
                       pub_year=year, pub_date=date, abstract=strip_tags(p.get("abstract")),
                       work_type=p.get("type")))
    return out


def norm_tavily(items):
    out = []
    for i, p in enumerate(items or []):
        pub = p.get("published_date")
        year = int(pub[:4]) if pub and pub[:4].isdigit() else None
        host = urlparse(p.get("url") or "").netloc.lower().removeprefix("www.") or None
        out.append(rec("tavily", i, title=p.get("title"), url=p.get("url"), publisher=host,
                       pub_year=year, pub_date=pub, abstract=p.get("content"), work_type="web page"))
    return out


NORMALIZERS = {"semantic_scholar": norm_s2, "crossref": norm_crossref, "tavily": norm_tavily}


# ---------------------------------------------------------------- merge + select
def merge(lists):
    """Round-robin across services (keeps the API order), merging records for the same DOI/URL."""
    merged, doi_map, url_map = [], {}, {}
    longest = max((len(l) for l in lists.values()), default=0)
    for i in range(longest):
        for svc in SERVICES:
            if i >= len(lists.get(svc, [])):
                continue
            r = lists[svc][i]
            cu = canon_url(r["url"])
            hit = doi_map.get(r["doi"]) if r["doi"] else None
            hit = hit or (url_map.get(cu) if cu else None)
            if hit is None:
                r["order"] = len(merged)
                merged.append(r); hit = r
            else:
                hit["services"] |= r["services"]
                for f in ("title", "url", "doi", "authors", "publisher", "venue", "pub_year",
                          "pub_date", "work_type", "open_access"):
                    if r[f] is not None and (hit[f] is None or (svc == "crossref" and f in
                            ("pub_year", "pub_date", "venue", "publisher"))):
                        hit[f] = r[f]
                if len(r["abstract"] or "") > len(hit["abstract"] or ""):
                    hit["abstract"] = r["abstract"]
            if hit["doi"]:
                doi_map[hit["doi"]] = hit
            hu = canon_url(hit["url"])
            if hu:
                url_map[hu] = hit
    return merged


def select(merged, n_sch, n_web):
    usable = [r for r in merged if r["title"] and (r["url"] or r["doi"])]
    for r in usable:
        if not r["url"] and r["doi"]:
            r["url"] = f"https://doi.org/{r['doi']}"
    sch = [r for r in usable if r["services"] & SCHOLARLY]
    web = [r for r in usable if not (r["services"] & SCHOLARLY)]
    pick = sch[:n_sch] + web[:n_web]
    total = n_sch + n_web
    if len(pick) < total:                       # fill from whichever pool still has records
        rest = [r for r in sch[n_sch:] + web[n_web:]]
        rest.sort(key=lambda r: r["order"])
        pick += rest[: total - len(pick)]
    pick.sort(key=lambda r: r["order"])
    return pick


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topics", default="csv/topics.csv")
    ap.add_argument("--sets", nargs="+", default=["pilot"])
    ap.add_argument("--out", default="data/retrieval")
    ap.add_argument("--n-scholarly", type=int, default=20)
    ap.add_argument("--n-web", type=int, default=10)
    a = ap.parse_args()

    out = Path(a.out); raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    topics = pd.read_csv(a.topics)
    topics = topics[topics.set.isin(a.sets)]
    print(f"{len(topics)} topics in sets {a.sets}")

    rows, summary = [], []
    for _, t in topics.iterrows():
        print(f"\n{t.topic_id}: {t.topic_text}")
        lists, failed = {}, []
        for svc in SERVICES:
            obj = cached(raw / f"{t.topic_id}_{svc}.json", t.topic_text, FETCHERS[svc])
            if obj["data"] is None:
                failed.append(svc); lists[svc] = []
            else:
                lists[svc] = NORMALIZERS[svc](obj["data"])
        sel = select(merge(lists), a.n_scholarly, a.n_web)
        for rank, r in enumerate(sel, 1):
            key = r["doi"] or canon_url(r["url"]) or r["title"]
            rows.append({
                "query_id": t.topic_id, "topic": t.topic_text, "set": t.set,
                "source_id": hashlib.sha1(key.encode()).hexdigest()[:10],
                "title": r["title"], "url": r["url"], "doi": r["doi"], "authors": r["authors"],
                "publisher": r["publisher"], "venue": r["venue"], "pub_year": r["pub_year"],
                "pub_date": r["pub_date"], "abstract": r["abstract"], "work_type": r["work_type"],
                "open_access": r["open_access"], "retrieved_from": "+".join(sorted(r["services"])),
                "kind": "scholarly" if r["services"] & SCHOLARLY else "web",
                "retrieval_rank": rank})
        d = pd.DataFrame([x for x in rows if x["query_id"] == t.topic_id])
        summary.append({"topic": t.topic_id, "n": len(d),
                        "scholarly": int((d.kind == "scholarly").sum()) if len(d) else 0,
                        "web": int((d.kind == "web").sum()) if len(d) else 0,
                        "no_abstract": int(d.abstract.isna().sum()) if len(d) else 0,
                        "no_year": int(d.pub_year.isna().sum()) if len(d) else 0,
                        "failed": ",".join(failed)})

    label = "_".join(a.sets)
    df = pd.DataFrame(rows)
    df.to_csv(out / f"candidates_{label}.csv", index=False)
    print("\n=== summary (check that every topic has ~30 with a mix) ===")
    print(pd.DataFrame(summary).to_string(index=False))
    print(f"\nSaved {len(df)} rows to {out / f'candidates_{label}.csv'}")


if __name__ == "__main__":
    main()