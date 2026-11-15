"""UI pieces for the source ranking page. Each function draws one part or one state."""
import base64
from functools import lru_cache
from html import escape
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
from PIL import Image

# (key in the data, label shown to the user, color). The colors are the letters of the ARES logo,
# left to right: a (yellow), r (purple), e (teal), s (pink). Cards, legend and score bars all use these.
SIGNALS = [
    ("cur", "Currency", "#EBB84D"),
    ("sem", "Relevance", "#AB5EBE"),
    ("auth", "Authority", "#35A7A7"),
    ("purp", "Purpose", "#FF65C3"),
]
# Extra display info for the signal cards: (tag, icon svg inner markup). Icons are plain strokes.
SIGNAL_CARD = {
    "cur": ("Recency", '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
    "sem": ("Topic match", '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/>'),
    "auth": ("Reputation", '<path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/>'),
    "purp": ("Academic fit", '<path d="M4 5a2 2 0 0 1 2-2h13v15H6a2 2 0 0 0-2 2z"/><path d="M4 20a2 2 0 0 0 2 2h13"/>'),
}
EXAMPLES = [
    "Machine learning defect prediction",
    "Climate change and crop yields",
    "Low-resource translation models",
]
TYPE_LABELS = {"journal": "Journal article", "web": "Web page"}
DISCLAIMER = (
    "Scores estimate suitability. They do not check whether a source's claims are true, "
    "so the decision to cite stays with you."
)

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
:root { --ink: #14233B; --mute: #5B6880; --line: #E8EAF3; --dark: #12162B; }

/* ---- page: soft lavender backdrop tinted with the logo colours ---- */
.stApp, .stApp p, .stApp label, .stApp button, .stApp input, .stApp h1, .stApp h2, .stApp h3, .serif {
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.stApp {
    background:
        radial-gradient(900px 600px at 6% 0%, rgba(96, 200, 214, .38), transparent 62%),
        radial-gradient(800px 560px at 100% 8%, rgba(255, 166, 135, .28), transparent 62%),
        radial-gradient(900px 700px at 92% 100%, rgba(166, 134, 230, .45), transparent 62%),
        radial-gradient(700px 520px at 0% 100%, rgba(255, 150, 200, .26), transparent 62%),
        #E9EAF8;
    background-attachment: fixed;
}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stHeader"] { background: transparent; }

/* ---- the white "window": centred in the viewport, top and bottom ---- */
[data-testid="stMain"] { display: flex; flex-direction: column; padding: clamp(10px, 3vh, 32px) 0; box-sizing: border-box; }
.block-container, [data-testid="stMainBlockContainer"] {
    width: min(1240px, calc(100vw - 200px)); max-width: none !important; margin: auto;
    padding: clamp(14px, 2.5vh, 22px) 44px clamp(28px, 5.5vh, 48px) !important;
    background: rgba(255, 255, 255, .86); border-radius: 36px;
    box-shadow: 0 40px 90px -40px rgba(70, 70, 140, .45), 0 0 0 1px rgba(255, 255, 255, .8) inset;
}

/* ---- left rail: sits in the search bar's row, so it stays level with the bar ---- */
[data-testid="stElementContainer"]:has(.rail), .element-container:has(.rail) { height: 0; min-height: 0; margin-bottom: calc(-1 * clamp(.4rem, 1.4vh, .8rem)); }
.rail { position: fixed; left: 22px; transform: translateY(calc(-50% + 21px)); z-index: 50; display: flex;
        flex-direction: column; align-items: center; gap: 12px; padding: 12px 8px; border-radius: 999px;
        background: rgba(255, 255, 255, .7); backdrop-filter: blur(12px); box-shadow: 0 10px 30px -12px rgba(70, 70, 140, .35); }
.rail a { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
          background: var(--dark); color: #fff !important; text-decoration: none; transition: transform .15s; }
.rail a:hover { transform: scale(1.08); }
.rail a svg { width: 18px; height: 18px; stroke: currentColor; fill: none; stroke-width: 2.2; stroke-linecap: round; }
.rail img { width: 30px; height: 30px; margin-top: 4px; }
@media (max-width: 1280px) { .rail { display: none; }
  .block-container, [data-testid="stMainBlockContainer"] { width: calc(100vw - 48px); } }
[data-testid="stMain"] [data-testid="stVerticalBlock"] { gap: clamp(.4rem, 1.4vh, .8rem); }

/* ---- top bar ---- */
.topbar { display: flex; align-items: center; margin-bottom: clamp(8px, 2vh, 16px); }
.brand { display: flex; align-items: center; gap: 10px; }
.brand .mark { height: 34px; } .brand .word { height: 22px; }
.topbar-end { justify-self: end; font-size: 12px; font-weight: 600; color: #fff; background: var(--dark);
              border-radius: 999px; padding: 9px 16px; }

/* ---- hero ---- */
.hero { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; margin: clamp(22px, 5vh, 52px) 0 clamp(60px, 9vh, 90px); }
.hero h1 { font-size: clamp(30px, 4.6vh, 42px); line-height: 1.08; font-weight: 500; letter-spacing: -.02em; margin: 0 0 10px; padding: 0; max-width: 14em; color: #3F4A5C !important; }
.hero h1 .dim { color: #8A94A8 !important; }
.mascot { position: relative; flex: none; padding: clamp(18px, 3.3vh, 30px) 6px 0 0; }
.mascot img { width: clamp(64px, 10.5vh, 96px); height: clamp(64px, 10.5vh, 96px); display: block; filter: drop-shadow(0 14px 18px rgba(120, 90, 190, .28));
              animation: bob 4s ease-in-out infinite; }
.bubble { position: absolute; top: 0; right: 70px; white-space: nowrap; font-size: 12px; line-height: 1.35; font-weight: 500;
          background: #fff; color: #4A5568; border-radius: 14px; padding: 7px 12px; box-shadow: 0 8px 22px -10px rgba(70, 70, 140, .4); }
@keyframes bob { 50% { transform: translateY(-6px); } }
@media (prefers-reduced-motion: reduce) { .mascot img { animation: none; } }
@media (max-width: 780px) { .mascot { display: none; } .hero h1 { font-size: 34px; } }
@media (max-width: 640px) {
  .block-container, [data-testid="stMainBlockContainer"] { margin: 12px 8px; padding: 20px 18px 28px !important; border-radius: 28px; } }

/* ---- signal cards: one per logo letter, narrower than the search bar and centred, same width as the examples ---- */
.keys { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; width: min(100%, 800px);
        margin: 96px auto clamp(14px, 3.5vh, 36px); }
.kcard { border: 0; border-radius: 16px; padding: 5px 10px; display: grid; grid-template-columns: 34px 1fr;
         align-items: center; gap: 0 10px; transition: transform .18s, box-shadow .18s; }
.kcard { cursor: default; }
.kicon { width: 34px; height: 34px; border-radius: 11px; grid-row: 1 / span 2; display: flex; align-items: center; justify-content: center; color: var(--cd); }
.kicon svg { width: 21px; height: 21px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.kcard b { grid-column: 2; align-self: end; font-size: 16px; line-height: 1.15; font-weight: 600; color: var(--cd) !important; }
.kcard span.d { grid-column: 2; align-self: start; margin-top: 1px; font-size: 11px; line-height: 1.25; color: color-mix(in srgb, var(--cd) 70%, #6B7688); }
.kcard .tag { display: none; }
@media (max-width: 900px) { .keys { grid-template-columns: 1fr 1fr; } }
@media (max-width: 520px) { .keys { grid-template-columns: 1fr; } }

/* ---- short screens: tighten so the start page fits without scrolling ---- */
@media (max-height: 760px) {
  .kcard .tag { display: none; } .kcard { padding: 5px 10px; } .kicon { width: 34px; height: 34px; }
  .note { padding-top: 8px; }
}
@media (max-height: 640px) {
  .hero h1 { font-size: 28px; } .hero { margin-top: 14px; margin-bottom: 12px; }
  .kcard span.d { font-size: 11px; line-height: 1.25; } .kicon { width: 28px; height: 28px; }
  .keys { margin-bottom: 10px; }
}

/* ---- composer (the search form) ---- */
[data-testid="stForm"] { background: #fff; border: 1.5px solid #7CC9CB; border-radius: 32px; padding: 6px 8px 6px 20px; width: min(100%, 840px); margin: 0 auto;
                 box-shadow: none; }
[data-testid="stForm"] [data-baseweb="input"], [data-testid="stForm"] [data-baseweb="base-input"] { background: transparent !important; border: 0 !important; }
[data-testid="stForm"] [data-testid="stTextInputRootElement"] { background: transparent !important; border: 0 !important; box-shadow: none !important; }
[data-testid="stForm"] input { font-size: 18px; height: 34px; padding-left: 8px; }
[data-testid="stForm"] input::placeholder { color: #8A94A8; }
[data-testid="stForm"] [data-testid="stTextInputRootElement"] svg { width: 24px; height: 24px; color: #7A6CCB; }
[data-testid="stForm"] [data-testid="stFormSubmitButton"] { display: flex; justify-content: flex-end; }
/* icon-only round submit button: the label stays in the DOM for screen readers but is visually hidden */
[data-testid="stForm"] button { width: 36px !important; min-width: 36px !important; height: 36px !important; min-height: 36px !important;
                                padding: 0 !important; border-radius: 50% !important; gap: 0 !important; }
[data-testid="stForm"] button, [data-testid="stForm"] button:active, [data-testid="stForm"] button:focus:not(:active) {
    background: #2E8F91 !important; background-color: #2E8F91 !important; border-color: #2E8F91 !important; color: #fff !important; }
[data-testid="stForm"] button:hover { background: #1F6F71 !important; background-color: #1F6F71 !important; border-color: #1F6F71 !important; }
[data-testid="stForm"] button > div { margin: 0 !important; gap: 0 !important; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }
[data-testid="stForm"] button span[data-has-shortcut] { display: flex !important; align-items: center; justify-content: center; gap: 0 !important; margin: 0 !important; width: 100%; }
[data-testid="stForm"] button [data-testid="stMarkdownContainer"] { position: absolute !important; width: 1px !important; height: 1px !important; margin: 0 !important; overflow: hidden !important; clip: rect(0 0 0 0) !important; }
[data-testid="stForm"] button p { position: absolute !important; width: 1px !important; height: 1px !important; margin: 0 !important; padding: 0 !important;
                                  overflow: hidden !important; clip: rect(0 0 0 0) !important; white-space: nowrap !important; }
[data-testid="stForm"] button [data-testid="stIconMaterial"] { margin: 0 !important; font-size: 22px !important; width: 22px !important; height: 22px !important; display: block; line-height: 1; }
[data-testid="stForm"]:focus-within { border-color: #35A7A7; box-shadow: none; }
[data-testid="InputInstructions"] { display: none !important; }

/* ---- buttons: dark pills ---- */
.stButton > button, .stFormSubmitButton > button, .stLinkButton > a {
    border-radius: 999px; font-weight: 600; font-size: 14px; border: 1px solid var(--line); background: #fff; color: var(--ink);
    transition: transform .15s, box-shadow .15s;
}
.stButton > button:hover, .stLinkButton > a:hover { transform: translateY(-1px); box-shadow: 0 8px 18px -10px rgba(70, 70, 140, .5); }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primaryFormSubmit"], .stFormSubmitButton > button {
    background: var(--dark); color: #fff; border-color: var(--dark); padding: 8px 20px;
}
.st-key-examples { width: min(100%, 760px); margin: 2px auto 0; }
[class*="st-key-chip"] .stButton > button p { white-space: nowrap; font-size: 12px !important; color: #8A94A8 !important; }
[class*="st-key-chip"] .stButton > button { background: rgba(231, 233, 241, .45); color: #8A94A8; border-color: rgba(217, 220, 232, .6); font-weight: 400; font-size: 12px; padding: 0 6px; min-height: 30px; height: 30px; }
[class*="st-key-chip"] .stButton > button:hover, [class*="st-key-chip"] .stButton > button:focus:not(:active) {
    background: #E7E9F1; color: #4A5568; border-color: #D9DCE8; }
[class*="st-key-chip"] .stButton > button:hover p { color: #4A5568 !important; }

/* ---- results ---- */
.meta { font-size: 14px; color: var(--mute); }
.note { font-size: 13px; color: var(--mute); border-top: 1px solid var(--line); padding-top: 10px; margin-top: 0; }
.chip { display: inline-block; font-size: 12px; font-weight: 600; padding: 1px 10px; margin-left: 8px;
        background: #F1EFFB; border-radius: 999px; color: #4B3E8C; }
.sw { display: inline-block; width: 12px; height: 12px; border-radius: 4px; margin-right: 8px; }
.legend { font-size: 14px; color: var(--mute); margin: 4px 0 16px; }
.legend .sw:not(:first-child) { margin-left: 16px; }
[class*="st-key-card"] { background: #fff; border: 1px solid var(--line) !important; border-radius: 24px !important;
                         padding: 10px 12px; box-shadow: 0 16px 38px -26px rgba(70, 70, 140, .45); }
.head { display: grid; grid-template-columns: 44px 1fr 88px; gap: 16px; }
.rk { display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 14px;
      background: #F1EFFB; color: #4B3E8C; font-size: 18px; font-weight: 700; }
.t { font-size: 19px; line-height: 1.3; font-weight: 600; }
.t a { color: var(--ink); text-decoration: none; } .t a:hover { text-decoration: underline; }
.score { text-align: right; font-size: 12px; color: var(--mute); }
.score b { display: block; font-size: 30px; font-weight: 600; line-height: 1; color: var(--ink); }
.ab { font-size: 15px; margin: 8px 0 12px; max-width: 70ch; }
.trk { display: flex; gap: 2px; background: #EEF0F6; border-radius: 999px; overflow: hidden; margin: 4px 0 12px; }
table.sig { width: 100%; border-collapse: collapse; font-size: 14px; }
table.sig td, table.sig th { padding: 8px 0; border-bottom: 1px solid #EEF0F6; text-align: right; }
table.sig td:first-child, table.sig th:first-child { text-align: left; }
"""


def inject_css():
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


# ---------- helpers ----------

def contributions(signals, weights):
    """Weighted contribution of each signal.

    A missing signal (None) is left out and the remaining weights are renormalized
    (Equation 3.1 and Algorithm 3.1). Returns (contribution, effective weight, score);
    the contributions add up to the score.
    """
    avail = [k for k, _, _ in SIGNALS if signals.get(k) is not None]
    total_w = sum(weights[k] for k in avail)
    contrib = {k: None for k, _, _ in SIGNALS}
    eff_w = {k: None for k, _, _ in SIGNALS}
    if not avail or total_w == 0:
        return contrib, eff_w, 0.0
    for k in avail:
        eff_w[k] = weights[k] / total_w
        contrib[k] = eff_w[k] * signals[k]
    return contrib, eff_w, sum(v for v in contrib.values() if v is not None)


def _safe_url(url):
    return url if url and url.startswith(("http://", "https://")) else ""


def _meta_line(r):
    authors = r.get("authors") or []
    who = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "") if authors else "Authors not listed"
    year = r.get("year") or "Date not found"
    venue = r.get("venue") or urlparse(r.get("url", "")).netloc or "Source not listed"
    chip = TYPE_LABELS.get(r.get("source_type"), "Source")
    return f'{escape(who)} · {escape(str(year))} · {escape(venue)}<span class="chip">{chip}</span>'


def _bar(contrib, height):
    segs, label = "", []
    for k, name, color in SIGNALS:
        if contrib[k] is not None:
            segs += f'<span style="width:{contrib[k] * 100:.1f}%;background:{color}"></span>'
            label.append(f"{name} {contrib[k]:.2f}")
    return (f'<div class="trk" style="height:{height}px" role="img" '
            f'aria-label="Score breakdown: {", ".join(label)}">{segs}</div>')


def _legend():
    items = "".join(f'<span class="sw" style="background:{c}"></span>{n}' for _, n, c in SIGNALS)
    return f'<div class="legend">{items}</div>'


# ---------- page parts ----------

def _img_b64(path, crop=True):
    """Logo as a data URI, trimmed of its transparent margin so it sits tight in the layout."""
    return _img_cached(str(path), crop)


@lru_cache(maxsize=8)
def _img_cached(path, crop):
    im = Image.open(path).convert("RGBA")
    if crop and im.getbbox():
        im = im.crop(im.getbbox())
    buf = BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def render_header(assets):
    """Top bar with the logo mark and wordmark."""
    assets = Path(assets)
    mark = _img_b64(assets / "logo.png")
    word = _img_b64(assets / "name.png")
    st.markdown(
        f'<div class="topbar"><div class="brand"><img class="mark" src="{mark}" alt="ARES logo">'
        f'<img class="word" src="{word}" alt="ARES"></div></div>',
        unsafe_allow_html=True,
    )


def render_rail(assets):
    """Left rail (new search + logo). Call it just before the search form so the rail stays level with the bar."""
    mark = _img_b64(Path(assets) / "logo.png")
    st.markdown(
        '<nav class="rail" aria-label="Quick actions">'
        '<a href="./" target="_self" title="New search" aria-label="New search">'
        '<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg></a>'
        f'<img src="{mark}" alt=""></nav>',
        unsafe_allow_html=True,
    )


def show_hero(assets):
    mark = _img_b64(Path(assets) / "logo.png")
    st.markdown(
        '<div class="hero"><div><h1><span class="dim">Ready to find</span> sources<br>you can cite?</h1></div>'
        f'<div class="mascot"><div class="bubble">Hey there!<br>Got a topic?</div>'
        f'<img src="{mark}" alt=""></div></div>',
        unsafe_allow_html=True,
    )


def show_examples(on_pick):
    """Example topics. Clicking one runs that search."""
    with st.container(key="examples"):
        cols = st.columns(len(EXAMPLES))
        for i, (col, text) in enumerate(zip(cols, EXAMPLES)):
            with col:
                st.button(text, key=f"chip{i}", on_click=on_pick, args=(text,), use_container_width=True)


def show_disclaimer():
    st.markdown(f'<div class="note">{DISCLAIMER}</div>', unsafe_allow_html=True)


# ---------- states ----------

def show_empty_state():
    """No search yet: the four signals as cards."""
    desc = {
        "cur": "Recency of the publication.",
        "sem": "Alignment with your research topic.",
        "auth": "Reputation of the journal or website.",
        "purp": "Scholarly rather than promotional.",
    }
    items = ""
    for k, n, c in SIGNALS:
        tag, icon = SIGNAL_CARD[k]
        items += (
            f'<div class="kcard" style="background:{c}24;--cd:color-mix(in srgb,{c} 78%,#000)">'
            f'<div class="kicon" style="background:{c}40">'
            f'<svg viewBox="0 0 24 24">{icon}</svg></div>'
            f'<b>{n}</b><span class="d">{desc[k]}</span><span class="tag">{tag}</span></div>'
        )
    st.markdown(f'<div class="keys">{items}</div>', unsafe_allow_html=True)


def show_short_query():
    st.error("Enter at least three words so the search has enough to work with.")


def show_no_results(removed=0):
    extra = f" {removed} sources were removed as blogs, forums, opinion, or commercial pages." if removed else ""
    st.info("No suitable sources found for this topic." + extra + " Try different or more specific words.")


def show_service_banner(failed, on_retry):
    names = " and ".join(failed) if len(failed) < 3 else ", ".join(failed)
    verb = "is" if len(failed) == 1 else "are"
    st.warning(f"**{names} {verb} not responding.** Showing results from the other services.")
    st.button("Try again", key="retry_partial", on_click=on_retry)


def show_all_down(on_retry):
    st.error("**The search can't run right now.** None of the search services are responding.")
    st.button("Try again", key="retry_all", on_click=on_retry)


def show_summary(n_ranked, removed):
    st.markdown(f"{n_ranked} sources ranked. {removed} removed as blogs, forums, opinion, or commercial pages.")
    st.markdown(_legend(), unsafe_allow_html=True)


def result_card(r, rank):
    contrib, eff_w, score = contributions(r["signals"], r["weights"])
    url = _safe_url(r.get("url"))
    title = escape(r.get("title") or "Untitled")
    title_html = f'<a href="{escape(url)}" target="_blank" rel="noopener">{title}</a>' if url else title
    abstract = escape((r.get("abstract") or "")[:280])
    missing = [n for k, n, _ in SIGNALS if r["signals"].get(k) is None]

    with st.container(border=True, key=f"card{rank}"):
        st.markdown(
            f'<div class="head"><span class="rk">{rank}</span>'
            f'<div><div class="t">{title_html}</div><div class="meta">{_meta_line(r)}</div></div>'
            f'<div class="score"><b>{score:.2f}</b>Suitability</div></div>'
            f'<p class="ab">{abstract}</p>{_bar(contrib, 10)}',
            unsafe_allow_html=True,
        )
        if missing:
            st.markdown(
                f'<p class="meta">{", ".join(missing)}: n/a. Not found for this source, '
                "so the other weights were adjusted.</p>",
                unsafe_allow_html=True,
            )
        if url:
            st.link_button("Open source", url)
        with st.expander("Show score breakdown"):
            rows = ""
            for k, name, color in SIGNALS:
                s, w, c = r["signals"].get(k), eff_w[k], contrib[k]
                cells = ("n/a", "n/a", "n/a") if s is None else (f"{s:.2f}", f"{w:.2f}", f"{c:.2f}")
                rows += (f'<tr><td><span class="sw" style="background:{color}"></span>{name}</td>'
                         + "".join(f"<td>{x}</td>" for x in cells) + "</tr>")
            st.markdown(_bar(contrib, 18), unsafe_allow_html=True)
            st.markdown(
                '<table class="sig"><thead><tr><th scope="col">Signal</th><th scope="col">Score</th>'
                '<th scope="col">Weight</th><th scope="col">Contribution</th></tr></thead>'
                f"<tbody>{rows}</tbody></table>",
                unsafe_allow_html=True,
            )