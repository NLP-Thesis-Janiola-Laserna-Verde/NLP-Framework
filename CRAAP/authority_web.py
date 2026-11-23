import pandas as pd
from pathlib import Path
from urllib.parse import urlparse

CSV_DIR = Path(__file__).resolve().parents[1] / "csv"

STRONG_SUFFIXES = ["gov", "edu", "gov.ph", "edu.ph", "ac.uk", "int"]   # -> 1.00
MID_SUFFIXES = ["org"]                                                  # -> 0.50
NEWS_FILE = CSV_DIR / "news_domains.csv"                                # columns: domain,reason  -> 0.50
DOI_HOSTS = {"doi.org", "dx.doi.org"}                                   # scholarly records, not web pages

NEWS_DOMAINS = set(
    pd.read_csv(NEWS_FILE, dtype=str)["domain"].str.strip().str.lower()
)


def get_host(url):
    url = str(url).strip()
    if "://" not in url:
        url = "http://" + url
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def matches(host, domain):
    return host == domain or host.endswith("." + domain)


def domain_score(url):
    host = get_host(url)
    if not host:
        return None, "no_host"
    if host in DOI_HOSTS:
        return None, "doi_link"          # should be a paper record; no domain score
    for s in STRONG_SUFFIXES:
        if matches(host, s):
            return 1.0, f"domain:.{s}"
    for d in NEWS_DOMAINS:
        if matches(host, d):
            return 0.5, "domain:news"
    for s in MID_SUFFIXES:
        if matches(host, s):
            return 0.5, f"domain:.{s}"
    return 0.0, "domain:other"


if __name__ == "__main__":
    df = pd.read_csv(CSV_DIR / "sources_web.csv", dtype=str)
    df.columns = df.columns.str.strip()

    is_web = df["record_type"].str.strip().str.lower() == "web"
    df["host"] = df["url"].apply(get_host)
    df["authority_score"] = None
    df["authority_basis"] = "n/a (paper)"

    res = df.loc[is_web, "url"].apply(domain_score)
    df.loc[is_web, "authority_score"] = res.apply(lambda r: r[0])
    df.loc[is_web, "authority_basis"] = res.apply(lambda r: r[1])
    df["authority_score"] = pd.to_numeric(df["authority_score"])

    df.to_csv(CSV_DIR / "authority_web_pilot.csv", index=False)
    print(df[["host", "record_type", "authority_basis", "authority_score"]])
    print()
    print(df.loc[is_web, "authority_basis"].value_counts())