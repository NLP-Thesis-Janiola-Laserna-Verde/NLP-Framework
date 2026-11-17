import pandas as pd
from datetime import date
from htmldate import find_date

HALF_LIFE_YEARS = 5
TODAY = date.today()

def extract_date(url):
    try:
        d = find_date(url, original_date=True, extensive_search=True)
        return pd.to_datetime(d).date() if d else None
    except Exception:
        return None

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
    df = pd.read_csv("sources.csv").head(10)   # start with a few
    df["pub_date"] = df["url"].apply(extract_date)
    df["date_found"] = df["pub_date"].notna()
    df["currency"] = df["pub_date"].apply(currency_score)

    df.to_csv("currency_pilot.csv", index=False)
    print(df[["url", "pub_date", "currency"]])