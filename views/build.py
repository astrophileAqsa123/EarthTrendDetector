# Build your own investigation
import streamlit as st

import core
import ui
from ai_helper import suggest_variables
from config import CATEGORIES, PLACE_PRESETS, TIME_WINDOWS, VARIABLES

ss = st.session_state
ALL_PLACES = {p["name"]: p for places in PLACE_PRESETS.values() for p in places}


def start_custom():
    biome = ss.g_biome
    ss.region_a = dict(ALL_PLACES[ss[f"g_place_{biome}"]])
    other = ss.g_compare
    if other != "(none)":
        ss.region_b, ss.mode = dict(ALL_PLACES[other]), core.COMPARE
    else:
        ss.mode = core.SINGLE
    ss.var_label = ss[f"g_var_{ss.g_cat}"]
    ss.year_range = TIME_WINDOWS[ss.g_window]
    ss.story = None


def use_suggestion(label: str):
    ss.g_cat = VARIABLES[label]["category"]
    ss[f"g_var_{ss.g_cat}"] = label


ui.page_header("Build your own investigation",
               "Answer three questions and we will run the analysis. Takes about a minute.")

with st.container(key="builder"):
    st.markdown("**Not sure what to look at?** Describe what you are curious about and we will suggest a topic.")
    qc1, qc2 = st.columns([4, 1])
    qc1.text_input("Your question", key="g_q", label_visibility="collapsed",
                   placeholder="e.g. Are summers getting hotter? Is my farmland drying out? Is solar power improving?")
    qc2.button("Suggest", key="g_suggest_btn", width="stretch",
               on_click=lambda: ss.__setitem__("g_suggest", suggest_variables(ss.get("g_q", ""), VARIABLES)))
    sugg = ss.get("g_suggest")
    if sugg and sugg[0]:
        labels, why, used_ai = sugg
        st.caption(("AI suggestion: " if used_ai else "") + (why or "Here are some matches."))
        for col, label in zip(st.columns(len(labels)), labels):
            col.button(f"Use {VARIABLES[label]['plain_name']}", key=f"use_{label}",
                       on_click=use_suggestion, args=(label,), width="stretch")
    elif sugg is not None and ss.get("g_q"):
        st.caption("No obvious match. Try different words, or pick a topic below.")

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**1. What topic?**")
        st.selectbox("Topic", CATEGORIES, key="g_cat", label_visibility="collapsed", format_func=ui.clean)
        opts = [lab for lab, i in VARIABLES.items() if i["category"] == ss.g_cat]
        st.selectbox("Variable", opts, key=f"g_var_{ss.g_cat}", label_visibility="collapsed",
                     format_func=lambda k: ui.clean(VARIABLES[k]["question"]))
        chosen = VARIABLES[ss[f"g_var_{ss.g_cat}"]]
        st.caption(f"**What is it?** {chosen['definition']}  \n**Why care?** {chosen['why']}")
    with c2:
        st.markdown("**2. What kind of place?**")
        st.selectbox("Kind of place", list(PLACE_PRESETS), key="g_biome", label_visibility="collapsed",
                     format_func=ui.clean)
        st.selectbox("Place", [p["name"] for p in PLACE_PRESETS[ss.g_biome]],
                     key=f"g_place_{ss.g_biome}", label_visibility="collapsed")
        st.selectbox("Compare with (optional)", ["(none)"] + list(ALL_PLACES), key="g_compare")
    with c3:
        st.markdown("**3. How far back?**")
        st.selectbox("Time window", list(TIME_WINDOWS), key="g_window", label_visibility="collapsed", index=1)
        st.caption("Longer periods give more reliable answers, because short ones are dominated by weather noise.")
        if st.button("Start investigating", key="g_go", type="primary", width="stretch", on_click=start_custom):
            st.switch_page(core.RESULTS)

st.write("")
st.markdown("Want a ready-made example instead?")
if st.button("Browse cases", key="build_to_cases"):
    st.switch_page(core.CASES)
core.footer()
