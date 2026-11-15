# Landing page
import streamlit as st

import core
import ui

ui.hero("See what is really changing on Earth",
        "Choose a place and a question. We test more than 40 years of NASA data and tell you, "
        "in plain words, whether the change is real.")

st.markdown("### Where do you want to start?")
c1, c2 = st.columns(2)
with c1.container(key="choice-cases"):
    st.markdown("#### Try a ready-made case")
    st.write("Six real questions, such as whether the Arctic really warms faster than the rest of the planet. "
             "One click loads the places, the data and the answer.")
    if st.button("Browse cases", key="go_cases", type="primary", width="stretch"):
        st.switch_page(core.CASES)
with c2.container(key="choice-build"):
    st.markdown("#### Ask your own question")
    st.write("Pick a topic, a kind of place and a time span. Not sure what to look at? "
             "Type what you are curious about and we will suggest a topic.")
    if st.button("Build an investigation", key="go_build", type="primary", width="stretch"):
        st.switch_page(core.BUILD)

st.markdown("### What you get")
s1, s2, s3 = st.columns(3)
with s1.container(key="step-1"):
    st.markdown("**A clear answer**")
    st.write("A short sentence says whether something is rising, falling, or not clearly changing.")
with s2.container(key="step-2"):
    st.markdown("**How sure we are**")
    st.write("Every result comes with a plain-language confidence level, not just a number.")
with s3.container(key="step-3"):
    st.markdown("**A reality check**")
    st.write("We test whether the answer changes when you pick different start and end years.")

st.markdown("### Want to go deeper?")
d1, d2, d3 = st.columns(3)
if d1.button("Scan every variable at a place", key="go_scan", width="stretch"):
    st.switch_page(core.SCANNER)
if d2.button("Map a whole region", key="go_map", width="stretch"):
    st.switch_page(core.MAP)
if d3.button("How we know it is real", key="go_how", width="stretch"):
    st.switch_page(core.HOW)

st.info("**Good to know:** the values come from a NASA model blended with observations, so they describe a "
        "large area around a point, not one weather station. A trend shows what changed, not why.")
core.footer()
