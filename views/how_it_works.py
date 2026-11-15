# Method and limits, in plain words
import streamlit as st

import core
import ui

ui.page_header("How it works", "What the app does with the data, and what it cannot tell you.")

st.markdown("### From data to answer")
steps = [
    ("Get the data", "Monthly NASA satellite-and-model data for the place you choose."),
    ("Remove the seasons", "Each month is compared with that month's normal, so summer versus winter doesn't hide the trend."),
    ("Find direction and speed", "A robust method (Sen's slope) finds how fast things are changing."),
    ("Test whether it is real", "A Mann-Kendall test asks: could ups and downs this size happen by chance? "
                                "If the chance is under 5%, we call the trend statistically significant."),
    ("Stress-test it", "We check whether the answer survives different start and end years, and estimate how many "
                       "more years of data an unclear trend would need."),
]
for i, (title, text) in enumerate(steps, 1):
    st.markdown(f"**{i}. {title}.** {text}")

st.markdown("### Reading the colours")
ui.legend_key()
st.caption("The purple and orange pair is chosen so it stays readable for people with colour-blindness.")

st.markdown("### What to keep in mind")
st.markdown(
    "- **Model-based values.** The data are a reanalysis (a model blended with observations) on a grid of about "
    "50 km, not readings from a single weather station.\n"
    "- **A trend is not a cause.** The app shows what changed and how sure we are, never why.\n"
    "- **\"No clear change\" is a real answer.** Short or noisy records often cannot show a trend yet.\n"
    "- **The AI never calculates.** If an AI explanation is switched on, it only describes numbers already computed "
    "on the page.")

st.write("")
if st.button("Start with a case", key="how_cases", type="primary"):
    st.switch_page(core.CASES)
core.footer()
