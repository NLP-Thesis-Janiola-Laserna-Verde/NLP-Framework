import pandas as pd
from urllib.parse import urlparse

STRONG_SUFFIXES = ["gov", "edu", "gov.ph", "edu.ph", "ac.uk"]   # -> 1.00
MID_SUFFIXES = ["org"]                                          # -> 0.50
NEWS_DOMAINS = {                                                # -> 0.50 (starter list, agree on it)
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nytimes.com",
    "theguardian.com", "washingtonpost.com", "aljazeera.com",
    "inquirer.net", "rappler.com", "philstar.com", "gmanetwork.com",
}

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

df = pd.read_csv("sources_web.csv", dtype=str)
df.columns = df.columns.str.strip()

is_web = df["record_type"].str.strip().str.lower() == "web"
df["host"] = df["url"].apply(get_host)
df["authority_score"] = None
df["authority_basis"] = "n/a (paper)"

res = df.loc[is_web, "url"].apply(domain_score)
df.loc[is_web, "authority_score"] = res.apply(lambda r: r[0])
df.loc[is_web, "authority_basis"] = res.apply(lambda r: r[1])
df["authority_score"] = pd.to_numeric(df["authority_score"])

df.to_csv("authority_web_pilot.csv", index=False)
print(df[["host", "record_type", "authority_basis", "authority_score"]])