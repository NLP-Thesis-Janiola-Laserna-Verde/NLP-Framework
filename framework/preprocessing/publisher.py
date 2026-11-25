"""Publisher names for web pages.

Order of attempts (the basis is reported so you can see which one worked):
  1. metadata   - JSON-LD "publisher", og:site_name, <meta name="publisher">, ...
  2. spacy      - ORG entities in the copyright / "published by" lines and the footer
  3. spacy_title - ORG entity in the last segment of the <title> ("Page | Organization")
  4. domain     - the host name, as a last resort
     ("domain (page not reachable)" means the page could not be downloaded at all)
Setup once: pip install spacy && python -m spacy download en_core_web_sm
"""
import json
import re
from urllib.parse import urlparse

import requests
import trafilatura
from lxml import html as lxml_html

from framework.preprocessing.clean_text import clean_text

_NLP = None
BASIS_UNREACHABLE = "domain (page not reachable)"   # page could not be downloaded
_COPYRIGHT_RE = re.compile(r"(?:©|\(c\)|copyright)[^\n]{0,120}", re.IGNORECASE)
_PUBLISHED_BY_RE = re.compile(r"(?:published|produced|maintained) by[^\n.]{0,100}", re.IGNORECASE)
_TITLE_SPLIT_RE = re.compile(r"\s+[|\-–—:]\s+")
_META_XPATHS = [
    '//meta[@property="og:site_name"]/@content',
    '//meta[@name="publisher"]/@content',
    '//meta[@name="citation_publisher"]/@content',
    '//meta[@name="DC.publisher"]/@content',
    '//meta[@name="application-name"]/@content',
]
_NOISE_RE = re.compile(r"\ball rights reserved\b.*", re.IGNORECASE)
# menu / footer words: an "organization" containing these is almost always page furniture
_MENU_WORDS = {"contact", "newsletters", "newsletter", "procurement", "subscribe", "login",
               "privacy", "terms", "cookies", "careers", "menu", "search", "home", "share",
               "follow", "sitemap", "accessibility", "us"}
MAX_ORG_WORDS = 7


def _valid_org(name):
    words = re.findall(r"[A-Za-z']+", name)
    if not 1 <= len(words) <= MAX_ORG_WORDS:
        return False
    return not any(w.lower() in _MENU_WORDS for w in words)


def _nlp():
    global _NLP
    if _NLP is None:
        import spacy
        try:
            _NLP = spacy.load("en_core_web_sm",
                              disable=["tagger", "parser", "attribute_ruler", "lemmatizer"])
        except OSError:
            raise RuntimeError("spaCy model missing. Run: python -m spacy download en_core_web_sm")
    return _NLP


def _orgs(text):
    """ORG entities spaCy finds in a short piece of text, cleaned and in order."""
    text = _NOISE_RE.sub("", text or "").strip()
    if not text:
        return []
    out = []
    for ent in _nlp()(text).ents:
        if ent.label_ == "ORG":
            name = clean_text(ent.text, single_line=True).strip(" ,.;:-|")
            if len(name) > 1 and _valid_org(name) and name not in out:
                out.append(name)
    return out


def _walk(node):
    """Yield every dict inside nested JSON-LD (lists, @graph, ...)."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def _page_titles(tree):
    """Parts of a multi-part <title> that name the page or its section, not the publisher.

    In "Page | Section | Site" the last part is the publisher, so everything before it is excluded.
    A one-part title is usually just the site name (a homepage), so it is NOT excluded.
    """
    titles = tree.xpath("//title/text()")
    if not titles:
        return set()
    parts = _TITLE_SPLIT_RE.split(clean_text(titles[0], single_line=True))
    return {_norm(p) for p in parts[:-1]} if len(parts) >= 2 else set()


def _from_metadata(tree):
    titles = _page_titles(tree)
    for script in tree.xpath('//script[@type="application/ld+json"]'):
        try:
            data = json.loads(script.text or "")
        except ValueError:
            continue
        for node in _walk(data):
            pub = node.get("publisher")
            if isinstance(pub, dict):
                pub = pub.get("name")
            if isinstance(pub, str) and pub.strip():
                return clean_text(pub, single_line=True)
    for xp in _META_XPATHS:
        for value in tree.xpath(xp):
            if value and value.strip() and _norm(value) not in titles:
                return clean_text(value, single_line=True)
    return None


def _page_text(tree):
    return re.sub(r"[ \t\r\f\v]+", " ", tree.text_content())


def _from_spacy_footer(tree):
    text = _page_text(tree)
    snippets = [m.group(0) for m in _COPYRIGHT_RE.finditer(text)]
    snippets += [m.group(0) for m in _PUBLISHED_BY_RE.finditer(text)]
    for snip in snippets:
        orgs = _orgs(snip)
        if orgs:
            return orgs[0]
    return None


def _from_spacy_title(tree):
    titles = tree.xpath("//title/text()")
    if not titles:
        return None
    parts = _TITLE_SPLIT_RE.split(clean_text(titles[0], single_line=True))
    if len(parts) < 2:
        return None
    orgs = _orgs(parts[-1])
    return orgs[0] if orgs else None


def _domain(url):
    host = (urlparse(str(url or "")).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def extract_publisher(html, url=""):
    """(publisher, basis) from raw HTML. Falls back to the domain, or (None, None) if no host."""
    tree = None
    if html:
        try:
            tree = lxml_html.fromstring(html)
        except Exception:
            tree = None
    if tree is not None:
        name = _from_metadata(tree)
        if name:
            return name, "metadata"
        name = _from_spacy_footer(tree)
        if name:
            return name, "spacy"
        name = _from_spacy_title(tree)
        if name:
            return name, "spacy_title"
    host = _domain(url)
    if not host:
        return None, None
    return (host, "domain") if html else (host, BASIS_UNREACHABLE)


_BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_html(url):
    """trafilatura first; if that fails, retry with browser-like headers. None if both fail."""
    html = trafilatura.fetch_url(url)
    if html:
        return html
    try:
        resp = requests.get(url, headers=_BROWSER_HEADERS, timeout=20)
    except requests.RequestException:
        return None
    return resp.text if resp.status_code == 200 and resp.text else None


def publisher_from_url(url):
    """Fetch the page, then extract_publisher. Download failures fall back to the domain."""
    return extract_publisher(fetch_html(url), url)