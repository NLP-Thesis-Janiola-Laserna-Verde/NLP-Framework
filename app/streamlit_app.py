"""Search page. Reads mock_results.json for now; replace load_results() with the real backend later.

Run from the repo root:  streamlit run app/streamlit_app.py
"""
import json
import math
import time
from pathlib import Path

import streamlit as st

import components as ui

APP_DIR = Path(__file__).parent
ASSETS = APP_DIR.parent / "assets"
PAGE_SIZE = 10      # FR16: 10 results per page
MAX_RESULTS = 30    # FR16: at most 30 results per query
MIN_WORDS = 3
STEPS = [
    "Searching Semantic Scholar and Crossref",
    "Searching the open web",
    "Reading pages",
    "Scoring and ranking",
]
DEMO_STATES = ["Normal", "One service down", "All services down", "No results"]

st.set_page_config(page_title="ARES", page_icon=str(ASSETS / "logo.png"), layout="wide",
                   initial_sidebar_state="collapsed")
ui.inject_css()
ss = st.session_state
ss.setdefault("data", None)
ss.setdefault("page", 1)
ss.setdefault("query", "")
ss.setdefault("error", False)

# Design-only switch for testing every state. Remove it once the backend is connected.
demo = st.sidebar.selectbox("Demo data (for testing the design)", DEMO_STATES)


def load_results(query, demo_state="Normal"):
    """Stand-in for the backend. Replace this body with a call to /rank later."""
    data = json.loads((APP_DIR / "mock_results.json").read_text(encoding="utf-8"))
    if demo_state == "One service down":
        data["meta"]["failed_services"] = ["Crossref"]
    elif demo_state == "All services down":
        data = {"meta": {"ranked": 0, "removed_by_filter": 0,
                         "failed_services": ["Semantic Scholar", "Crossref", "Tavily"]}, "results": []}
    elif demo_state == "No results":
        data["results"] = []
        data["meta"]["ranked"] = 0
    return data


def run_search(query, demo_state):
    with st.status("Searching...", expanded=True) as status:
        for step in STEPS:
            st.write(step)
            time.sleep(0.4)
        data = load_results(query, demo_state)
        status.update(label="Done", state="complete", expanded=False)
    return data


def retry():
    ss.retry_query = ss.query


def go_to(page):
    ss.page = page


def pick_example(text):
    ss.query = ss.retry_query = text


def pagination(page, pages, total):
    first, last = (page - 1) * PAGE_SIZE + 1, min(page * PAGE_SIZE, total)
    st.caption(f"Showing {first}–{last} of {total}")
    if pages > 1:
        cols = st.columns([1.3] + [0.6] * pages + [1.3] + [6 - 0.6 * pages])
        cols[0].button("Previous", key="prev", disabled=page == 1, on_click=go_to, args=(page - 1,))
        for p in range(1, pages + 1):
            cols[p].button(str(p), key=f"pg{p}", type="primary" if p == page else "secondary",
                           on_click=go_to, args=(p,))
        cols[pages + 1].button("Next", key="next", disabled=page == pages, on_click=go_to, args=(page + 1,))


# ---------- page ----------
ui.render_header(ASSETS)
hero_slot = st.container()    # heading, filled below, only while there are no results
form_slot = st.container()    # search bar
chips_slot = st.container()   # example topics, only while there are no results
cards_slot = st.container() 

with form_slot:
    ui.render_rail(ASSETS)
    with st.form("search", border=False):
        field, button = st.columns([16, 1], vertical_alignment="center")
        query = field.text_input("Research topic", value=ss.query, label_visibility="collapsed",
                                 icon=":material/search:",
                                 placeholder="Type your research topic, e.g. software defect prediction")
        submitted = button.form_submit_button("Rank sources", type="primary", use_container_width=True,
                                              icon=":material/arrow_upward:", help="Rank sources")
if ss.get("retry_query"):
    query, submitted = ss.pop("retry_query"), True

if submitted:
    ss.query = query
    if len(query.split()) < MIN_WORDS:
        ss.error, ss.data = True, None
    else:
        ss.error = False
        ss.data = run_search(query, demo)
        ss.page = 1

if ss.data is None:
    with hero_slot:
        ui.show_hero(ASSETS)
    with chips_slot:
        ui.show_examples(pick_example)
    with cards_slot:
        ui.show_empty_state()

if ss.error:
    ui.show_short_query()

data = ss.data
if data is not None:
    meta = data["meta"]
    failed = meta.get("failed_services", [])
    if len(failed) >= 3:
        ui.show_all_down(retry)
    else:
        if failed:
            ui.show_service_banner(failed, retry)
        if not data["results"]:
            ui.show_no_results(meta.get("removed_by_filter", 0))
        else:
            results = sorted(data["results"], key=lambda r: r["score"], reverse=True)[:MAX_RESULTS]
            ui.show_summary(len(results), meta.get("removed_by_filter", 0))
            pages = math.ceil(len(results) / PAGE_SIZE)
            page = min(ss.page, pages)
            start = (page - 1) * PAGE_SIZE
            for rank, r in enumerate(results[start:start + PAGE_SIZE], start=start + 1):
                ui.result_card(r, rank)
            pagination(page, pages, len(results))

ui.show_disclaimer()

# streamlit run app/streamlit_app.py