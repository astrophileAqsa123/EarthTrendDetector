# Results: the trend at one or two places
import streamlit as st

import core
import ui
from config import STORIES

ss = st.session_state
core.sidebar()
S = core.cfg()

ui.page_header("Results", "What is changing, how fast, and how sure we are. Change the question, time period "
                          "or places any time.")


def describe(region, s):
    conf_short = core.confidence(s["p_value"])[0]
    phrase = (S.var_info["up_phrase"] if s["change_per_decade"] > 0 else S.var_info["down_phrase"]) \
        if s["is_significant"] else "no clear change"
    extra = f", $p={core.fmt_p(s['p_value'])}$" if S.expert else ""
    return (f"**{region['name']}**: {phrase} ({core.fmt_num(s['change_per_decade'])} {S.var_info['unit']} per 10 years; "
            f"{conf_short.lower()}{extra})")


if ss.story:
    s = STORIES[ss.story]
    with st.container(border=True, key="casefile"):
        st.markdown(f"**Case file: {ss.story}**  \n{s['mystery']}")
        st.markdown("**Clues to look for:**  \n" + "  \n".join(f"- {c}" for c in s["clues"]))
        st.button("Close case file", key="close_story", on_click=core.dismiss_story)

core.render_map_picker()

with st.expander(f"What is {S.var_info['plain_name']}?", expanded=not S.expert and not ss.story):
    st.write(f"{S.var_info['definition']}  \n**Why it matters:** {S.var_info['why']}")

if ss.mode == core.SINGLE:
    res = core.render_region_panel(ss.region_a, "Target location", "a")
    if res:
        stats_a, _ = res
        st.markdown("### Case summary")
        st.write(f"Between **{S.year_range[0]} and {S.year_range[1]}**, {describe(ss.region_a, stats_a)}.")
else:
    col_left, col_right = st.columns(2)
    with col_left:
        res_a = core.render_region_panel(ss.region_a, "Region A", "a")
    with col_right:
        res_b = core.render_region_panel(ss.region_b, "Region B", "b")

    if res_a and res_b:
        (stats_a, facts_a), (stats_b, facts_b) = res_a, res_b
        st.divider()
        st.markdown("### Comparing the two places")
        opposite = (stats_a["is_significant"] and stats_b["is_significant"]
                    and stats_a["tendency"] != stats_b["tendency"])
        both_sig = stats_a["is_significant"] and stats_b["is_significant"]
        body = f"{describe(ss.region_a, stats_a)}  \n{describe(ss.region_b, stats_b)}"
        if opposite:
            st.warning(f"**Opposite trends confirmed.** The same variable is moving in opposite directions.  \n{body}")
        elif both_sig:
            st.info(f"**Both places show a real trend in the same direction.**  \n{body}")
        else:
            st.write(f"**No opposite significant trends found for this variable and period.**  \n{body}")
        with st.expander("Get an AI write-up comparing the two places", expanded=False):
            core.explain_ui(core.build_facts([facts_a, facts_b]), "cmp")

st.divider()
st.markdown("**What next?**")
n1, n2, n3 = st.columns(3)
if n1.button("Scan every variable here", key="next_scan", width="stretch"):
    st.switch_page(core.SCANNER)
if n2.button("Map the surrounding region", key="next_map", width="stretch"):
    st.switch_page(core.MAP)
if n3.button("Try another case", key="next_cases", width="stretch"):
    st.switch_page(core.CASES)
core.footer()
