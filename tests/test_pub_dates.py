import sys
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from framework.preprocessing import pub_dates as pd_


def test_doi_from_url():
    assert pd_.doi_from_url("https://doi.org/10.1038/s41586-021-03819-2") == "10.1038/s41586-021-03819-2"
    assert pd_.doi_from_url("https://arxiv.org/abs/2005.11401") is None
    assert pd_.doi_from_url(None) is None


def test_crossref_full_and_partial_dates():
    assert pd_.parse_crossref({"issued": {"date-parts": [[2021, 8, 3]]}}) == date(2021, 8, 3)
    assert pd_.parse_crossref({"issued": {"date-parts": [[2021]]}}) == date(2021, 1, 1)
    assert pd_.parse_crossref({"issued": {"date-parts": [[None]]},
                               "published-online": {"date-parts": [[2020, 2]]}}) == date(2020, 2, 1)
    assert pd_.parse_crossref({}) is None


def test_semantic_scholar_date_and_year_fallback():
    assert pd_.parse_semantic_scholar({"publicationDate": "2022-03-09", "year": 2022}) == date(2022, 3, 9)
    assert pd_.parse_semantic_scholar({"publicationDate": None, "year": 2019}) == date(2019, 1, 1)
    assert pd_.parse_semantic_scholar({"publicationDate": None, "year": None}) is None
    assert pd_.parse_semantic_scholar(None) is None


def test_paper_falls_back_to_semantic_scholar(monkeypatch):
    monkeypatch.setattr(pd_, "crossref_date", lambda doi: None)
    monkeypatch.setattr(pd_, "semantic_scholar_date", lambda doi=None, title=None: date(2020, 5, 22))
    assert pd_.paper_date(doi="10.1/x") == (date(2020, 5, 22), "semantic_scholar")


def test_paper_prefers_crossref(monkeypatch):
    monkeypatch.setattr(pd_, "crossref_date", lambda doi: date(2021, 1, 1))
    monkeypatch.setattr(pd_, "semantic_scholar_date", lambda doi=None, title=None: date(1999, 1, 1))
    assert pd_.paper_date(doi="10.1/x") == (date(2021, 1, 1), "crossref")


def test_missing_everywhere_returns_none(monkeypatch):
    monkeypatch.setattr(pd_, "crossref_date", lambda doi: None)
    monkeypatch.setattr(pd_, "semantic_scholar_date", lambda doi=None, title=None: None)
    monkeypatch.setattr(pd_, "web_date", lambda u: None)
    assert pd_.get_pub_date("https://doi.org/10.1/x") == (None, None)


def test_web_page_uses_htmldate_on_html():
    html = ('<html><head><meta property="article:published_time" content="2023-04-05T10:00:00+00:00">'
            '</head><body><p>Hello</p></body></html>')
    assert pd_.web_date(html) == date(2023, 4, 5)


def test_web_page_without_date_is_none():
    assert pd_.web_date("<html><body><p>No date here</p></body></html>") is None