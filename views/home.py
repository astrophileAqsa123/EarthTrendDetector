# Landing page
import streamlit as st

import core
import places
import ui
from config import CATEGORIES, VARIABLES

ss = st.session_state
n_vars = len(VARIABLES)

# ---- hero: one question, with the finder sitting on the stripes
ui.hero("Is the place you live really changing?",
        f"Pick any city or country. We test more than 40 years of NASA data across {n_vars} signals, from "
        "temperature to rainfall to soil moisture, and tell you in plain words what is real.")

with st.container(key="finder"):
    st.markdown("#### Look up a place")
    f1, f2, f3, f4 = st.columns([2.2, 2.2, 1.3, 1.5], vertical_alignment="bottom")
    f1.selectbox("Country", places.country_names(), key="pl_country")
    cities = places.cities_of(ss.pl_country)
    if cities and ss.pl_city not in cities:
        ss.pl_city = places.default_city(ss.pl_country)
    f2.selectbox("City", list(cities) or ["No cities listed"], key="pl_city", disabled=not cities)
    go_city = f3.button("City trends", key="go_city", type="primary", width="stretch", disabled=not cities,
                        on_click=core.go_places, args=(core.KIND_CITY,))
    go_country = f4.button("Whole country", key="go_country", width="stretch",
                           on_click=core.go_places, args=(core.KIND_COUNTRY,))
    if go_city or go_country:
        st.switch_page(core.PLACES)

st.write("")
st.write("")

# ---- what is tracked
left, right = st.columns([2, 3], gap="large")
with left:
    st.markdown(f"### {n_vars} signals, one page")
    st.write("Every place is checked for heat, water, land and soil, air, sun and energy. You see each one as a "
             "chart with a clear verdict, so a warming city that is also getting drier does not hide behind "
             "a single number.")
    st.write("Cities use the data for the area around the city. A whole country is the average of several "
             "points spread across it.")
with right:
    st.markdown(ui.variable_groups(VARIABLES, CATEGORIES), unsafe_allow_html=True)

# ---- reliability
st.markdown("### Every answer says how sure it is")
p1, p2, p3 = st.columns(3)
with p1.container(key="promise-verdict"):
    st.markdown("**A plain verdict**")
    st.write("Rising, falling, or no clear change, in one sentence.")
with p2.container(key="promise-sure"):
    st.markdown("**How sure we are**")
    st.write("A confidence level you can read, not just a number.")
with p3.container(key="promise-check"):
    st.markdown("**A reality check**")
    st.write("We repeat the test over many start and end years, so a lucky window cannot fool you.")
ui.legend_key()

# ---- other ways in
st.markdown("### Other ways to explore")
ways = [
    ("Ready-made cases", "Six real questions, such as whether the Arctic warms faster than the rest of the planet.", core.CASES),
    ("Build your own", "Pick a topic, a kind of place and a time span, or describe what you are curious about.", core.BUILD),
    ("Trend scanner", "Rank every variable at one place by how clearly it is changing.", core.SCANNER),
    ("Regional map", "Test a whole area on a grid and see where it moves in opposite directions.", core.MAP),
    ("How it works", "The method, and what it cannot tell you.", core.HOW),
]
for i, (title, text, page) in enumerate(ways):
    with st.container(key="way-last" if i == len(ways) - 1 else f"way-{i}"):
        w1, w2, w3 = st.columns([2, 6, 1.3], vertical_alignment="center")
        w1.markdown(f"#### {title}")
        w2.write(text)
        if w3.button("Open", key=f"open_{i}", width="stretch"):
            st.switch_page(page)

st.write("")
st.info("**Good to know:** the values come from a NASA model blended with observations, so they describe a "
        "large area around a point, not one weather station. A trend shows what changed, not why.")
core.footer()
