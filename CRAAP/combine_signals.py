"""Combine the four CRAAP signals into one table (one row per source).

Columns: s_sem (relevance), s_cur (currency), s_auth (authority), s_purp (purpose).
A signal that could not be computed is stored as NaN/null, never 0, so the ranker
can tell "scored zero" apart from "no data".

Run from the CRAAP folder:  python combine_signals.py
"""
import pandas as pd
from pathlib import Path

CSV_DIR = Path(__file__).resolve().parents[1] / "csv"
SIGNAL_COLS = ["s_sem", "s_cur", "s_auth", "s_purp"]


def _signal(df, col, name):
    """Take (source_id, col) from df as a one-column frame named `name`.
    Missing values stay NaN; they are coerced to numbers, never filled with 0."""
    if df is None:
        return pd.DataFrame(columns=[name], index=pd.Index([], name="source_id"), dtype="float64")
    out = df[["source_id", col]].copy()
    out[col] = pd.to_numeric(out[col], errors="coerce")
    # drop nulls first so a row with a real score wins over a duplicate that has none
    out = out.dropna(subset=[col]).drop_duplicates("source_id").set_index("source_id")
    return out.rename(columns={col: name})


def combine_signals(relevance=None, currency=None, authority=None, purpose=None):
    """Outer-join the four signal frames on source_id.

    relevance  -> column "relevance"
    currency   -> column "currency"
    authority  -> column "authority_score"
    purpose    -> column "purpose"   (not implemented yet: stays all-null)

    Any source missing from a frame, or with a missing value, gets NaN for that signal.
    """
    table = pd.concat([
        _signal(relevance, "relevance", "s_sem"),
        _signal(currency, "currency", "s_cur"),
        _signal(authority, "authority_score", "s_auth"),
        _signal(purpose, "purpose", "s_purp"),
    ], axis=1).sort_index()
    return table.reindex(columns=SIGNAL_COLS).astype("float64")


if __name__ == "__main__":
    rel = pd.read_csv(CSV_DIR / "relevance_pilot.csv")
    cur = pd.read_csv(CSV_DIR / "currency_pilot.csv")
    auth = pd.concat([pd.read_csv(CSV_DIR / "authority_paper_pilot.csv"),
                      pd.read_csv(CSV_DIR / "authority_web_pilot.csv")], ignore_index=True)

    signals = combine_signals(relevance=rel, currency=cur, authority=auth)
    signals.to_csv(CSV_DIR / "signals_pilot.csv")
    print(signals)
    print("\nmissing per signal:\n", signals.isna().sum())