import sys
from datetime import date
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
sys.path.append(str(PROJECT_ROOT))
from framework.preprocessing.pub_dates import get_pub_date

HALF_LIFE_YEARS = 5
TODAY = date.today()

def extract_date(url):
    """Web pages use htmldate; DOI links use Crossref, then Semantic Scholar."""
    return get_pub_date(url)[0]

def age_in_years(pub_date, today=None):
    """Age in years; None if the date is missing, 0 if it is in the future."""
    if pub_date is None or pd.isna(pub_date):
        return None
    today = today or TODAY
    return max((today - pub_date).days / 365.25, 0)

def currency_score(pub_date, today=None):
    age = age_in_years(pub_date, today)
    if age is None:
        return None
    return 0.5 ** (age / HALF_LIFE_YEARS)

if __name__ == "__main__":
    df = pd.read_csv(DATA_DIR / "sources" / "sources.csv").head(10)   # start with a few
    found = df["url"].apply(get_pub_date)
    df["pub_date"] = found.apply(lambda r: r[0])
    df["date_source"] = found.apply(lambda r: r[1])
    df["date_found"] = df["pub_date"].notna()
    df["currency"] = df["pub_date"].apply(currency_score)

    df.to_csv(DATA_DIR / "signals" / "currency_pilot.csv", index=False)
    print(df[["url", "pub_date", "date_source", "currency"]])