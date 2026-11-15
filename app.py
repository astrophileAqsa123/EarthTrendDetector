# app.py: entry point. Sets up the theme and the page navigation; every page lives in views/.
import streamlit as st

import core
import ui

st.set_page_config(page_title="Earth System Trend Detective", page_icon="🌍", layout="wide")
ui.inject_css()
core.init_state()

pages = [
    st.Page(core.HOME, title="Home", icon=":material/home:", default=True),
    st.Page(core.RESULTS, title="Compare & Trends", icon=":material/monitoring:"),
    st.Page(core.PLACES, title="City & country", icon=":material/location_city:"),
    st.Page(core.SCANNER, title="Trend scanner", icon=":material/radar:"),
    st.Page(core.MAP, title="Regional map", icon=":material/map:"),
    st.Page(core.HOW, title="How it works", icon=":material/help:"),
    st.Page(core.CASES, title="Cases", icon=":material/travel_explore:"),
]
st.navigation(pages, position="top").run()
