# collect_genre_data.py

'''
for collecting candidate sources for genre classification annotation using tavily and semantic scholar.

Run from the repository root:
    python -m framework.craap.purpose.collect_genre_data

'''

import os, re, time, requests, pandas as pd, trafilatura

from pathlib import Path
OUT = Path(__file__).parent

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from dotenv import load_dotenv
from tavily import TavilyClient
from framework.preprocessing.clean_text import clean_text 


load_dotenv()
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
S2_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
print("S2 key loaded:", bool(S2_KEY))

def debug(message):
    print(f"[DEBUG {time.strftime('%H:%M:%S')}] {message}", flush=True)

GENRE_TOPICS = [
    "climate change adaptation in coastal cities",
    "online learning and student outcomes",
    "air pollution and respiratory health",
    "social media and misinformation",
    "teacher training in public schools",
    "machine learning for crop yield prediction",
    "mental health support for college students",
    "cybersecurity awareness programs",
    "plastic waste management",
    "childhood vaccination uptake",
    "remote work and productivity",
    "microfinance and poverty reduction",
]
NEWS  = ["rappler.com", "inquirer.net", "bbc.com", "reuters.com", "theguardian.com", "philstar.com"]
BLOG  = ["medium.com", "substack.com", "wordpress.com", "blogspot.com"]
FORUM = ["stackexchange.com", "quora.com", "stackoverflow.com"]
OPINION_PAT = re.compile(r"/(opinion|editorial|commentary|op-ed)/", re.I)

def guess(url, source):
    if source == "semantic_scholar":
        return "research"
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if OPINION_PAT.search(url): return "opinion"
    if any(host.endswith(d) for d in FORUM): return "forum"
    if any(host.endswith(d) for d in BLOG): return "blog"
    if any(host.endswith(d) for d in NEWS): return "news"
    if re.search(r"\.(gov|edu)(\.[a-z]{2})?$|\.ac\.[a-z]{2}$", host): return "research"
    return "unknown"

def papers(q, n=10):
    debug(f"Semantic Scholar search: {q!r} (limit={n})")
    headers = {"x-api-key": S2_KEY} if S2_KEY else {}
    for attempt in range(4):
        r = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={"query": q, "limit": n, "openAccessPdf": "",
                    "fields": "title,abstract,url"},
            headers=headers, timeout=30)
        if r.status_code == 429:
            debug(f"Semantic Scholar rate limited; retrying attempt {attempt + 2}")
            time.sleep(5 * (attempt + 1))
            continue
        break
    if r.status_code != 200:
        print("Semantic Scholar", r.status_code, q); return []
    results = [{"url": p["url"], "title": clean_text(p["title"], single_line=True), "source": "semantic_scholar",
             "how_found": "natural", "text": clean_text(f"{p['title']}. {p['abstract']}", single_line=True)}
            for p in r.json().get("data", []) if p.get("abstract")]
    debug(f"Semantic Scholar returned {len(results)} records")
    return results

def web(q, how, domains=None, n=10):
    try:
        res = tavily.search(q, max_results=n, include_domains=domains or [],
                            include_raw_content=True)
    except Exception as e:
        print("Tavily error:", e); return []
    return [{"url": r["url"], "title": clean_text(r["title"], single_line=True), "source": "tavily",
             "how_found": how,
             "text": clean_text(r.get("raw_content") or r.get("content"), single_line=True)}
            for r in res["results"]]

def allowed(url):
    p = urlparse(url); rp = RobotFileParser()
    rp.set_url(f"{p.scheme}://{p.netloc}/robots.txt")
    try:
        rp.read(); return rp.can_fetch("*", url)
    except Exception:
        return False

def fill_text(row):
    if row["text"]:
        debug(f"Using existing text: {row['url']}")
        return row["text"]
    if not allowed(row["url"]):
        debug(f"Robots denied or unavailable: {row['url']}")
        return None
    debug(f"Fetching page: {row['url']}")
    html = trafilatura.fetch_url(row["url"])
    if not html:
        debug(f"No HTML returned: {row['url']}")
        return None
    text = trafilatura.extract(html, include_comments=True)
    text = clean_text(text, single_line=True)
    debug(f"Extracted {len(text) if text else 0} characters: {row['url']}")
    return text

rows = []
for t in GENRE_TOPICS:
    debug(f"Starting topic: {t}")
    rows += papers(t)
    rows += web(t, "natural")                                   # like the real system
    rows += web(f"{t} discussion question", "targeted", FORUM, 5)
    rows += web(f"{t} opinion editorial", "targeted", NEWS, 5)
    rows += web(f"{t} my experience thoughts", "targeted", BLOG, 5)
    rows += web(f"best {t} tools pricing buy", "targeted", None, 5)
    debug(f"Finished topic: {t}; total collected={len(rows)}")
    time.sleep(3)

debug(f"Building dataframe from {len(rows)} collected records")
df = pd.DataFrame(rows).drop_duplicates("url")
debug(f"After URL deduplication: {len(df)} records")
print("before filter:\n", df.groupby(["source", "how_found"]).size())
df = df[df.text.fillna("").str.len() > 200].drop_duplicates("text")
print("after filter:\n", df.groupby(["source", "how_found"]).size())
df = df[df.text.fillna("").str.len() > 200].drop_duplicates("text")
debug(f"After text filtering and deduplication: {len(df)} records")
df["text"] = df.text.str[:5000]
df["guess"] = [guess(u, s) for u, s in zip(df.url, df.source)]
df = df.sample(frac=1, random_state=42).reset_index(drop=True)   # random order
df.insert(0, "id", range(len(df)))
print(len(df), "candidates"); print(df.guess.value_counts())

# review sheet: NO guess column, so labelers aren't anchored
sheet = df[["id", "title", "url"]].copy()
sheet["snippet"] = df.text.str[:400].str.replace("\n", " ")
sheet["labeler"] = [["A", "B", "C"][i % 3] for i in range(len(df))]
sheet["genre"] = ""
sheet["notes"] = ""
df.to_csv(OUT / "candidates.csv", index=False)
sheet.to_csv(OUT / "review_sheet.csv", index=False)
debug("Wrote candidates.csv and review_sheet.csv")

# second-labeler check sheet: 25 random rows, labeled by a DIFFERENT person
check = sheet.sample(25, random_state=7).drop(columns=["genre", "notes"])
check["genre"] = ""
check.to_csv(OUT / "check_sheet.csv", index=False)
debug("Wrote check_sheet.csv; collection complete")