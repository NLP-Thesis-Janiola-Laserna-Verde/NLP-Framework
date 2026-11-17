import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))
from retrieval import publisher as pub

try:
    pub._nlp()
    HAS_MODEL = True
except Exception:
    HAS_MODEL = False

needs_model = pytest.mark.skipif(not HAS_MODEL, reason="en_core_web_sm not installed")


def test_metadata_site_name_wins():
    html = '<html><head><meta property="og:site_name" content="Rappler"></head><body></body></html>'
    assert pub.extract_publisher(html, "https://www.rappler.com/x") == ("Rappler", "metadata")


def test_json_ld_publisher():
    html = ('<html><head><script type="application/ld+json">'
            '{"@graph":[{"@type":"Article","publisher":{"name":"Philippine Daily Inquirer"}}]}'
            '</script></head><body></body></html>')
    assert pub.extract_publisher(html, "https://x.net/a") == ("Philippine Daily Inquirer", "metadata")


@needs_model
def test_spacy_reads_copyright_line():
    html = ("<html><head><title>Dengue</title></head><body><p>Text</p>"
            "<footer>© 2026 World Health Organization. All rights reserved.</footer></body></html>")
    name, basis = pub.extract_publisher(html, "https://www.who.int/x")
    assert (name, basis) == ("World Health Organization", "spacy")


@needs_model
def test_spacy_reads_title_suffix():
    html = "<html><head><title>Information literacy | UNESCO</title></head><body><p>Hi</p></body></html>"
    _, basis = pub.extract_publisher(html, "https://www.unesco.org/x")
    assert basis in ("spacy_title", "domain")  # a short acronym may not be tagged ORG


def test_domain_fallback_when_nothing_found():
    html = "<html><head><title>Hello</title></head><body><p>Nothing here</p></body></html>"
    assert pub.extract_publisher(html, "https://www.example.org/page") == ("example.org", "domain")


def test_no_html_falls_back_to_domain():
    assert pub.extract_publisher(None, "https://www.ox.ac.uk/") == ("ox.ac.uk", pub.BASIS_UNREACHABLE)


def test_no_html_no_url_is_none():
    assert pub.extract_publisher(None, "") == (None, None)


@needs_model
def test_meta_equal_to_first_part_of_long_title_is_rejected():
    html = ('<html><head><title>Physical Activity Basics | Physical Activity | CDC</title>'
            '<meta name="application-name" content="Physical Activity Basics"></head>'
            '<body><p>Hi</p></body></html>')
    name, _ = pub.extract_publisher(html, "https://www.cdc.gov/x")
    assert name != "Physical Activity Basics"


def test_homepage_site_name_equal_to_title_is_kept():
    html = ('<html><head><title>Department of Education</title>'
            '<meta property="og:site_name" content="Department of Education"></head>'
            '<body><p>Hi</p></body></html>')
    assert pub.extract_publisher(html, "https://www.deped.gov.ph/") == ("Department of Education", "metadata")


@needs_model
def test_menu_text_is_not_mistaken_for_an_organization():
    html = ("<html><head><title>Physical activity</title></head><body><p>Text</p>"
            "<footer>Library Procurement Publications Contact us Newsletters Report</footer>"
            "</body></html>")
    assert pub.extract_publisher(html, "https://www.who.int/x") == ("who.int", "domain")


def test_valid_org_rules():
    assert pub._valid_org("World Health Organization")
    assert not pub._valid_org("Library Procurement Publications Contact us Newsletters Report")
    assert not pub._valid_org("A B C D E F G H")


@needs_model
def test_cdc_style_page_uses_last_title_part_not_section_name():
    html = ('<html><head><title>Physical Activity Basics and Your Health | Physical Activity Basics | CDC</title>'
            '<meta property="og:title" content="Physical Activity Basics and Your Health">'
            '<meta property="og:site_name" content="Physical Activity Basics"></head>'
            '<body><h1>Physical Activity Basics and Your Health</h1><p>Text</p></body></html>')
    assert pub.extract_publisher(html, "https://www.cdc.gov/physical-activity-basics/") == ("CDC", "spacy_title")