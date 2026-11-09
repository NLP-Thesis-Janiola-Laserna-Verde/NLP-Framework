import pandas as pd
from datetime import date
from htmldate import find_date

HALF_LIFE_YEARS = 5
TODAY = date(2026, 11, 10)

def extract_date(url):
    try:
        d = find_date(url, original_date=True, extensive_search=True)
        return pd.to_datetime(d).date() if d else None
    except Exception:
        return None

def currency_score(pub_date):
    if pub_date is None:
        return None
    age_years = (TODAY - pub_date).days / 365.25
    age_years = max(age_years, 0)
    return 0.5 ** (age_years / HALF_LIFE_YEARS)

df = pd.read_csv("sources.csv").head(10)   # start with a few
df["pub_date"] = df["url"].apply(extract_date)
df["date_found"] = df["pub_date"].notna()
df["currency"] = df["pub_date"].apply(currency_score)

df.to_csv("currency_pilot.csv", index=False)
print(df[["url", "pub_date", "currency"]])