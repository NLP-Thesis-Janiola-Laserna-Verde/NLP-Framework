import pandas as pd

from CRAAP.combine_signals import SIGNAL_COLS, combine_signals


def test_columns_and_one_row_per_source():
    rel = pd.DataFrame({"source_id": ["A", "B"], "relevance": [0.9, 0.4]})
    cur = pd.DataFrame({"source_id": ["A", "B"], "currency": [0.5, 0.8]})
    auth = pd.DataFrame({"source_id": ["A", "B"], "authority_score": [1.0, 0.5]})
    out = combine_signals(rel, cur, auth)
    assert list(out.columns) == SIGNAL_COLS
    assert list(out.index) == ["A", "B"]


def test_missing_value_stays_null_not_zero():
    rel = pd.DataFrame({"source_id": ["A"], "relevance": [0.9]})
    cur = pd.DataFrame({"source_id": ["A"], "currency": [None]})
    out = combine_signals(rel, cur)
    assert pd.isna(out.loc["A", "s_cur"])


def test_source_absent_from_a_signal_gets_null():
    rel = pd.DataFrame({"source_id": ["A", "B"], "relevance": [0.9, 0.4]})
    auth = pd.DataFrame({"source_id": ["A"], "authority_score": [1.0]})
    out = combine_signals(rel, authority=auth)
    assert pd.isna(out.loc["B", "s_auth"])


def test_real_zero_is_kept_as_zero():
    auth = pd.DataFrame({"source_id": ["A"], "authority_score": [0.0]})
    out = combine_signals(authority=auth)
    assert out.loc["A", "s_auth"] == 0.0


def test_unimplemented_purpose_is_all_null():
    rel = pd.DataFrame({"source_id": ["A"], "relevance": [0.9]})
    out = combine_signals(rel)
    assert out["s_purp"].isna().all()