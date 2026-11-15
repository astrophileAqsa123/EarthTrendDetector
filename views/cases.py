# Ready-made cases
import streamlit as st

import core
import ui
from config import STORIES, VARIABLES

ui.page_header("Ready-made cases",
               "Six real questions about our planet. Open one and the places, data and answer load for you. "
               "The app reports whatever the data show, including \"no clear change\".")

names = list(STORIES)
for row in range(0, len(names), 3):
    for col, name in zip(st.columns(3), names[row:row + 3]):
        s = STORIES[name]
        with col.container(border=True, key=f"casecard-{names.index(name)}"):
            st.markdown(f"#### {name}")
            st.write(s["mystery"])
            st.caption(f"Looks at {VARIABLES[s['variable']]['plain_name']}: "
                       f"{s['region_a']['name'].split(',')[0]} vs {s['region_b']['name'].split(',')[0]}")
            if st.button("Open this case", key=f"case_{name}", on_click=core.load_story, args=(name,),
                         width="stretch"):
                st.switch_page(core.RESULTS)

st.write("")
st.markdown("Prefer to choose everything yourself?")
if st.button("Build your own investigation", key="cases_to_build"):
    st.switch_page(core.BUILD)
core.footer()
