# Landing page
import streamlit as st

import core
import places
import ui
from config import CATEGORIES, VARIABLES

ss = st.session_state
n_vars = len(VARIABLES)

# (question it answers, tool name, what it does, page, button label, mode to preselect)
TOOLS = [
    ("Is my city or country changing?", "Look up a place",
     "Pick any city or a whole country and get a verdict on every signal.",
     core.PLACES, "Look up a place", None),
    ("Is one place changing faster than another?", "Compare two places",
     "Put two places side by side on one signal, such as the Arctic against South Asia.",
     core.RESULTS, "Compare places", core.COMPARE),
    ("What is changing most right here?", "Scan one place",
     f"Rank all {n_vars} signals at a single spot by how clearly each one is moving.",
     core.SCANNER, "Scan a place", None),
    ("Where does it change, and where not?", "Map a region",
     "Test a whole area on a grid and spot the places that move in opposite directions.",
     core.MAP, "Open the map", None),
    ("Not sure where to start?", "Guided cases",
     "Six real mysteries, like the Sahel drought, loaded with the places and data ready to read.",
     core.CASES, "See the cases", None),
    ("Have a question of your own?", "Build your own",
     "Describe what you are curious about and we suggest what to test and where.",
     core.BUILD, "Build an investigation", None),
]


def _prepare(mode):
    """Button callback: preselect single/compare mode before the next page opens."""
    if mode:
        ss.mode = mode


# ---- 1. hero: say what this is, in one breath
ui.hero(
    "See what is really changing on Earth.",
    f"Earth System Trend Detective tests more than 40 years of NASA data for any city, country or region, "
    f"across {n_vars} signals from temperature to rainfall to soil moisture. It tells you in plain words "
    "what is rising, what is falling, and what is just random noise.",
    eyebrow="Earth System Trend Detective",
    chips=["NASA POWER data, 1981 to 2025", f"{n_vars} Earth signals", "Plain-language verdicts", "No sign-up needed"],
)

# ---- 2. quick start (one of several ways in, not the whole product)
with st.container(key="finder"):
    st.markdown("#### Quick start: look up a city or a country")
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

# ---- 3. every tool, each framed as the question it answers
ui.section("Pick the question you want to answer",
           "Every tool uses the same NASA data and the same statistical tests. They differ in what you ask.",
           kicker="Six ways to explore")

for start in range(0, len(TOOLS), 3):
    cols = st.columns(3, gap="medium")
    for col, i in zip(cols, range(start, min(start + 3, len(TOOLS)))):
        question, title, text, page, label, mode = TOOLS[i]
        with col.container(key=f"tool-{i}"):
            st.markdown(f'<p class="tool-q">{question}</p>', unsafe_allow_html=True)
            st.markdown(f"#### {title}")
            st.write(text)
            if st.button(label, key=f"go_tool_{i}", width="stretch", on_click=_prepare, args=(mode,)):
                st.switch_page(page)

# ---- 4. how it works + what an answer looks like
ui.section("From NASA data to a plain answer", kicker="How it works")
a, b = st.columns([1.05, 1], gap="large", vertical_alignment="center")
with a:
    ui.steps([
        ("Pick a place and a question",
         "A city, a country, two places to compare, or a patch of the map."),
        ("We test the NASA record",
         "Monthly data since 1981, with the normal seasons removed so they cannot fake a trend. "
         "We then repeat the test over many start and end years."),
        ("You get a plain verdict",
         "Rising, falling or no clear change, how sure we are, and a chart you can check yourself."),
    ])
with b:
    st.markdown('<div class="sample-tag">What an answer looks like (illustration)</div>', unsafe_allow_html=True)
    ui.verdict("demo", "up",
               "**Your city is getting warmer.** Between 1981 and 2025 the average air temperature rose steadily.",
               "Very sure", "We are very sure this is a real change, not just random ups and downs.")
    ui.legend_key()
    st.caption("Many places show no clear change for some signals. The app says so instead of forcing a story.")

# ---- 5. what is tracked
ui.section(f"{n_vars} signals, checked for every place", kicker="What we track")
left, right = st.columns([2, 3], gap="large")
with left:
    st.write("Every place is checked for heat, water, land and soil, air, sun and energy. You see each one as a "
             "chart with a clear verdict, so a warming city that is also getting drier does not hide behind "
             "a single number.")
    st.write("Cities use the data for the area around the city. A whole country is the average of several "
             "points spread across it.")
with right:
    st.markdown(ui.variable_groups(VARIABLES, CATEGORIES), unsafe_allow_html=True)

# ---- 6. reliability
ui.section("Every answer says how sure it is", kicker="Why you can trust it")
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

st.write("")
st.info("**Good to know:** the values come from a NASA model blended with observations, so they describe a "
        "large area around a point, not one weather station. A trend shows what changed, not why.")
core.footer()