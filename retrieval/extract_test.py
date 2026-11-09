"""Test text extraction (trafilatura) and date extraction (htmldate) on a few web sources.

Run dedupe.py first so data/candidates/*.csv exists.
"""
import glob

import pandas as pd
import trafilatura
from htmldate import find_date

N_SAMPLES = 10


def test_url(url):
    html = trafilatura.fetch_url(url)
    if not html:
        return {"url": url, "fetched": False, "text_len": 0, "date": None}

    text = trafilatura.extract(html, include_comments=False) or ""
    try:
        date = find_date(html)
    except Exception:
        date = None
    return {"url": url, "fetched": True, "text_len": len(text), "date": date}


if __name__ == "__main__":
    files = glob.glob("data/candidates/*.csv")
    if not files:
        raise SystemExit("No candidates found. Run: python -m retrieval.dedupe")

    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    web = df[df["source_type"] == "web"].dropna(subset=["url"])
    sample = web.sample(min(N_SAMPLES, len(web)), random_state=1)

    rows = []
    for url in sample["url"]:
        r = test_url(url)
        rows.append(r)
        print(f"{'OK  ' if r['text_len'] > 200 else 'FAIL'} | len={r['text_len']:>6} "
              f"| date={r['date']} | {url[:70]}")

    out = pd.DataFrame(rows)
    out.to_csv("data/extraction_test.csv", index=False)

    ok = (out["text_len"] > 200).sum()
    dated = out["date"].notna().sum()
    print(f"\nText extracted: {ok}/{len(out)} | Date found: {dated}/{len(out)}")