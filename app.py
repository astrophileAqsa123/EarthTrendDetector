# app.py: entry point. Sets up the theme and the page navigation; every page lives in views/.
import streamlit as st

import core
import ui

st.set_page_config(page_title="Earth System Trend Detective", page_icon="🌍", layout="wide")
ui.inject_css()
core.init_state()


pages = [
    st.Page(core.HOME, title="Home", icon=":material/home:", default=True),
    st.Page(core.PLACES, title="Look up a place", icon=":material/location_city:"),
    st.Page(core.RESULTS, title="Compare places", icon=":material/compare_arrows:"),
    st.Page(core.SCANNER, title="Scan a place", icon=":material/radar:"),
    st.Page(core.MAP, title="Map a region", icon=":material/map:"),
    st.Page(core.CASES, title="Guided cases", icon=":material/travel_explore:"),
    st.Page(core.BUILD, title="Build your own", icon=":material/tune:"),
    st.Page(core.HOW, title="How it works", icon=":material/help:"),
]
st.navigation(pages, position="top").run()