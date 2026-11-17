from datetime import date

from CRAAP.currency import age_in_years, currency_score

TODAY = date(2026, 11, 17)


def test_missing_date_returns_null():
    assert age_in_years(None, TODAY) is None
    assert currency_score(None, TODAY) is None


def test_future_date_gives_age_zero():
    assert age_in_years(date(2030, 1, 1), TODAY) == 0
    assert currency_score(date(2030, 1, 1), TODAY) == 1.0


def test_today_gives_age_zero():
    assert age_in_years(TODAY, TODAY) == 0


def test_normal_decay_halves_at_half_life():
    score = currency_score(date(2021, 11, 17), TODAY)
    assert score is not None
    assert abs(score - 0.5) < 0.01