"""Clean text extracted by trafilatura: HTML leftovers, unreadable characters, extra whitespace."""
import html
import re
import unicodedata

# soft hyphen, zero-width space/joiners, word joiner, BOM
_INVISIBLE = dict.fromkeys(map(ord, "\u00ad\u200b\u200c\u200d\u2060\ufeff"), None)
_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def clean_text(text, single_line=False):
    """Return readable text with markup, junk characters and extra whitespace removed.

    single_line=True also folds line breaks into spaces (useful for CSV abstracts).
    """
    if not text:
        return ""
    text = html.unescape(text)
    text = _TAG_RE.sub(" ", text)
    text = unicodedata.normalize("NFKC", text)   # also turns non-breaking spaces into plain ones
    text = text.translate(_INVISIBLE)
    text = text.replace("\ufffd", "")             # replacement char from bad decoding
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_RE.sub("", text)
    text = re.sub(r"[^\S\n]+", " ", text)         # runs of spaces/tabs -> one space
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)        # at most one blank line
    text = text.strip()
    if single_line:
        text = re.sub(r"\s+", " ", text)
    return text