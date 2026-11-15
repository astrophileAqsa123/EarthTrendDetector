# app.py
import json

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from ai_helper import AUDIENCES, AIUnavailable, ai_configured, explain_results, suggest_variables
from config import (CATEGORIES, PLACE_PRESETS, POWER_SOURCE, STORIES, TIME_WINDOWS, VARIABLES)
from data_fetcher import fetch_time_series
from plain import (confidence, fmt_abs, fmt_num, fmt_p, headline, robustness_sentence,
                   template_narrative, tts_sentence)
from scanner import scan_grid, scan_variables
from stats_engine import (METHODS, add_anomalies, analyze_trend, field_significant, robustness_summary,
                          window_sensitivity)

SINGLE = "Single Location"
COMPARE = "Compare Two Regions"
V_START, V_DET, V_SCAN, V_GRID = "🧭 Start here", "🕵️ Detective", "🔬 Trend Scanner", "🗺️ Regional Map"
VIEWS = [V_START, V_DET, V_SCAN, V_GRID]

# Colour-blind-safe pair (purple = rising, orange = falling)
COL_UP, COL_DOWN, COL_NS = "#5e3c99", "#e66101", "#9e9e9e"

st.set_page_config(page_title="Earth System Trend Detective", page_icon="🌍", layout="wide")

st.title("🌍 Earth System Trend Detective")
st.markdown(
    "Use real NASA data to find out **what** is changing on Earth, **where**, **how much**, "
    "and **how sure** we can be that the change is real."
)


# ---------------------------------------------------------------- cached work
@st.cache_data(ttl=86400, show_spinner=False)
def get_cached_analysis(lat: float, lon: float, param: str, start_year: int, end_year: int, method: str):
    df = add_anomalies(fetch_time_series(lat, lon, param, start_year, end_year))
    stats = analyze_trend(df, method)
    return df, stats


@st.cache_data(ttl=86400, show_spinner=False)
def get_cached_sensitivity(df: pd.DataFrame):
    return window_sensitivity(df)


@st.cache_data(ttl=86400, show_spinner=False)
def get_cached_scan(lat, lon, start_year, end_year, method):
    return scan_variables(lat, lon, start_year, end_year, method)


@st.cache_data(ttl=86400, show_spinner=False)
def get_cached_grid(lat, lon, param, start_year, end_year, method, half_width, step):
    return scan_grid(lat, lon, param, start_year, end_year, method, half_width, step)


@st.cache_data(ttl=86400, show_spinner=False)
def get_cached_narrative(facts_json: str, audience: str) -> str:
    return explain_results(json.loads(facts_json), audience)


# ---------------------------------------------------------------- session state
ss = st.session_state
ss.setdefault("mode", COMPARE)
ss.setdefault("level", "Beginner")
ss.setdefault("view", V_START)
ss.setdefault("var_label", list(VARIABLES)[0])
ss.setdefault("year_range", (2000, 2025))
ss.setdefault("method_label", list(METHODS)[0])
ss.setdefault("region_a", {"name": "Islamabad, Pakistan", "lat": 33.6844, "lon": 73.0479})
ss.setdefault("region_b", {"name": "Longyearbyen, Svalbard", "lat": 78.2232, "lon": 15.6267})
ss.setdefault("last_click", None)   # last map click we already handled
ss.setdefault("story", None)

ALL_PLACES = {p["name"]: p for places in PLACE_PRESETS.values() for p in places}


# ---------------------------------------------------------------- callbacks
def go_to(view: str):
    ss.view = view


def load_story(name: str):
    s = STORIES[name]
    ss.region_a, ss.region_b = dict(s["region_a"]), dict(s["region_b"])
    ss.var_label = s["variable"]
    ss.year_range = tuple(s["years"])
    ss.mode = COMPARE
    ss.story = name
    ss.view = V_DET


def dismiss_story():
    ss.story = None


def start_custom():
    biome = ss.g_biome
    place = ALL_PLACES[ss[f"g_place_{biome}"]]
    ss.region_a = dict(place)
    other = ss.g_compare
    if other != "(none)":
        ss.region_b, ss.mode = dict(ALL_PLACES[other]), COMPARE
    else:
        ss.mode = SINGLE
    ss.var_label = ss[f"g_var_{ss.g_cat}"]
    ss.year_range = TIME_WINDOWS[ss.g_window]
    ss.story = None
    ss.view = V_DET


def use_suggestion(label: str):
    ss.g_cat = VARIABLES[label]["category"]
    ss[f"g_var_{ss.g_cat}"] = label


def open_variable(label: str):
    ss.var_label = label
    ss.view = V_DET


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.radio("Display mode", ["Beginner", "Expert"], key="level", horizontal=True,
             help="Beginner uses everyday words. Expert shows the full statistics.")
    expert = ss.level == "Expert"

    st.header("1. What are you curious about?")
    st.radio("Investigation Mode", [SINGLE, COMPARE], key="mode")
    st.selectbox("Earth system question", list(VARIABLES), key="var_label",
                 format_func=lambda k: VARIABLES[k]["question"])
    var_label = ss.var_label
    var_info = VARIABLES[var_label]
    st.caption(f"**What is it?** {var_info['definition']}")

    st.header("2. When?")
    st.slider("Analysis period (years)", 1981, 2025, key="year_range")
    year_range = ss.year_range
    n_years = year_range[1] - year_range[0] + 1
    if n_years < 10:
        st.warning("Use 10+ years for reliable climate trends. Short periods are dominated by weather noise.")

    if expert:
        st.header("3. How sure do we need to be?")
        st.selectbox("Significance test", list(METHODS), key="method_label")
        method = METHODS[ss.method_label]
        st.caption("Hamed-Rao corrects the p-value for autocorrelation (fewer false positives).")
    else:
        method = "seasonal"

    st.divider()
    st.caption("🤖 AI explanations: " + ("**on** (Groq)" if ai_configured()
                                        else "**off**. Set `GROQ_API_KEY` to turn on. A built-in explanation is used instead."))


st.radio("View", VIEWS, key="view", horizontal=True, label_visibility="collapsed")
view = ss.view


# ---------------------------------------------------------------- shared helpers
FALLBACK_KEYS = {"direction_words", "total_abs", "rate_abs", "confidence_sentence",
                 "time_to_significance_sentence", "robustness_sentence"}


def ai_view(facts: dict) -> dict:
    """Facts as sent to the AI: only computed numbers, none of the pre-written fallback sentences."""
    out = {k: v for k, v in facts.items() if k != "regions"}
    out["regions"] = [{k: v for k, v in r.items() if k not in FALLBACK_KEYS} for r in facts["regions"]]
    return out


def region_facts(region: dict, stats: dict, rob: dict | None) -> dict:
    rate = stats["change_per_decade"]
    conf_short, conf_sentence, _ = confidence(stats["p_value"])
    tts = stats.get("time_to_significance")
    last_year = year_range[1]
    return {
        "name": region["name"], "lat": round(region["lat"], 3), "lon": round(region["lon"], 3),
        "significant": stats["is_significant"],
        "trend_direction": "increasing" if rate > 0 else "decreasing",
        "rate_per_decade": round(rate, 4), "total_change": round(stats["total_change"], 4),
        "p_value": round(stats["p_value"], 5), "how_sure": conf_short,
        "ci_95_per_decade": [round(stats["ci_low_decade"], 4), round(stats["ci_high_decade"], 4)],
        "kendall_tau": round(stats["tau"], 3),
        "abrupt_shift_year": stats["change_point_year"] if stats["change_point_p"] < 0.05 else None,
        "time_to_significance": ({"extra_years_expected": tts["extra_50"], "year_expected": tts["year_50"],
                                  "extra_years_for_high_confidence": tts["extra_80"],
                                  "year_high_confidence": tts["year_80"]} if tts else None),
        "robustness": ({"verdict": rob["verdict"], "windows_tested": rob["n_windows"],
                        "pct_windows_same_direction": round(100 * rob["same_sign_share"]),
                        "pct_windows_significant": round(100 * rob["significant_share"])}
                       if rob and rob["n_windows"] else None),
        # offline fallback text (never sent to the AI)
        "direction_words": var_info["up_phrase"] if rate > 0 else var_info["down_phrase"],
        "total_abs": fmt_abs(stats["total_change"]), "rate_abs": fmt_abs(rate),
        "confidence_sentence": conf_sentence,
        "time_to_significance_sentence": tts_sentence(tts, last_year),
        "robustness_sentence": robustness_sentence(rob),
    }


def build_facts(regions: list) -> dict:
    return {
        "variable": var_label, "plain_name": var_info["plain_name"], "definition": var_info["definition"],
        "unit": var_info["unit"], "period": f"{year_range[0]}-{year_range[1]}",
        "test": "Seasonal Mann-Kendall" if method == "seasonal" else "Hamed-Rao modified Mann-Kendall",
        "data_source": "NASA MERRA-2 reanalysis via NASA POWER (monthly, ~50 km grid cell)",
        "regions": regions,
    }


def run_explanation(facts: dict, audience: str, key: str):
    payload = json.dumps(ai_view(facts), sort_keys=True)
    sig = payload + audience
    try:
        with st.spinner("Asking the AI detective..."):
            text = get_cached_narrative(payload, audience)
        ss[key] = (sig, text, None)
    except AIUnavailable as e:
        ss[key] = (sig, template_narrative(facts), str(e))


def show_explanation(facts: dict, audience: str, key: str):
    saved = ss.get(key)
    if not saved:
        return
    sig = json.dumps(ai_view(facts), sort_keys=True) + audience
    if saved[0] != sig:
        st.caption("Settings changed since the last explanation. Press the button again.")
        return
    st.write(saved[1])
    if saved[2] is None:
        st.caption("✨ Written by an AI (Groq) from the numbers computed on this page. "
                   "It describes the results but never calculates them. Double-check anything important.")
    else:
        st.caption(f"Built-in explanation shown. ({saved[2]})")


def explain_ui(facts: dict, pin_key: str):
    c1, c2 = st.columns([2, 1])
    audience = c1.selectbox("Explain it for…", list(AUDIENCES), key=f"aud_{pin_key}")
    c2.write("")
    c2.write("")
    if c2.button("🤖 Explain", key=f"ai_{pin_key}", width="stretch"):
        run_explanation(facts, audience, f"expl_{pin_key}")
    show_explanation(facts, audience, f"expl_{pin_key}")


def robustness_chart(sens: pd.DataFrame, stats_unit: str, y0: int, y1: int):
    piv = sens.pivot(index="start", columns="end", values="slope_per_decade")
    sig = sens[sens["significant"]]
    fig = go.Figure(go.Heatmap(
        x=piv.columns, y=piv.index, z=piv.values, colorscale="PuOr", zmid=0,
        colorbar=dict(title=f"{stats_unit} / 10 yrs"),
        hovertemplate="Start %{y} → end %{x}<br>%{z:+.3f} per 10 years<extra></extra>"))
    fig.add_trace(go.Scatter(x=sig["end"], y=sig["start"], mode="markers", name="significant (p < 0.05)",
                             marker=dict(color="black", size=4), hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[y1], y=[y0], mode="markers", name="your selection",
                             marker=dict(symbol="star", size=14, color="gold", line=dict(color="black", width=1)),
                             hoverinfo="skip"))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis_title="End year", yaxis_title="Start year", yaxis_autorange="reversed",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


# ---------------------------------------------------------------- region panel
def render_region_panel(region: dict, label: str, pin_key: str):
    st.subheader(f"{label}: {region['name']}")
    st.caption(f"Coordinates: `{region['lat']:.4f}°, {region['lon']:.4f}°`")

    try:
        with st.spinner(f"Fetching NASA data for {region['name']}..."):
            df, stats = get_cached_analysis(region["lat"], region["lon"], var_info["param"],
                                            year_range[0], year_range[1], method)
    except Exception as e:  # network errors, bad ranges, too-short series
        st.error(f"Could not analyze this location: {e}")
        return None

    unit = var_info["unit"]
    rate = stats["change_per_decade"]
    conf_short, conf_sentence, conf_emoji = confidence(stats["p_value"])
    sens = get_cached_sensitivity(df) if len(df) // 12 >= 12 else None
    rob = robustness_summary(sens, rate) if sens is not None else None
    rfacts = region_facts(region, stats, rob)

    # ---- headline answer
    box = st.success if stats["is_significant"] else st.info
    box(f"{headline(region['name'], var_info, stats, year_range)}\n\n{conf_emoji} **{conf_short}.** {conf_sentence}")

    c1, c2, c3 = st.columns(3)
    if expert:
        c1.metric("Rate of change", f"{fmt_num(rate)} {unit}/dec", delta=stats["tendency"].title(), delta_color="off")
        c2.metric(f"Total shift ({stats['years_analyzed']} yrs)", f"{fmt_num(stats['total_change'])} {unit}")
        c3.metric("p-value", fmt_p(stats["p_value"]),
                  delta="Significant" if stats["is_significant"] else "Not significant", delta_color="off")
    else:
        c1.metric(f"Total change in {stats['years_analyzed']:.0f} years", f"{fmt_num(stats['total_change'])} {unit}")
        c2.metric("Speed (per 10 years)", f"{fmt_num(rate)} {unit}")
        c3.metric("How sure are we?", conf_short)

    df = df.copy()
    df["trend_line"] = stats["trend_line"]
    df["year"] = df["date"].dt.year
    annual = df.groupby("year", as_index=False)["anomaly"].mean()
    annual["date"] = pd.to_datetime(annual["year"].astype(str) + "-07-01")

    tab_trend, tab_solid, tab_ai, tab_sci = st.tabs(
        ["📈 The trend", "🔍 Is it solid?", "🤖 Explain it", "🧪 For scientists"])

    # ---- tab 1: the trend
    with tab_trend:
        line_col = (COL_UP if rate > 0 else COL_DOWN) if stats["is_significant"] else COL_NS
        fig = go.Figure()
        if expert:
            fig.add_trace(go.Scatter(x=df["date"], y=df["anomaly"], mode="lines", name="Monthly anomaly",
                                     line=dict(color="rgba(100,149,237,0.35)", width=1.2)))
        fig.add_trace(go.Scatter(x=annual["date"], y=annual["anomaly"], mode="lines+markers",
                                 name="Yearly average", line=dict(color="#1f77b4", width=2)))
        fig.add_trace(go.Scatter(x=df["date"], y=df["trend_line"], mode="lines",
                                 name=f"Overall direction ({fmt_num(rate)}/10 yrs)",
                                 line=dict(color=line_col, width=3, dash="dash")))
        fig.add_hline(y=0, line_width=1, line_color="rgba(128,128,128,0.5)")
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10),
                          yaxis_title=(f"Anomaly ({unit})" if expert else f"Difference from normal ({unit})"),
                          hovermode="x unified",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, width="stretch", key=f"anom_{pin_key}")
        st.caption("Each dot is one year compared with this place's normal (its average for the same calendar "
                   "months). The dashed line shows the overall direction, with the seasons removed so they don't "
                   "hide the trend.")

        if not stats["is_significant"] and stats.get("time_to_significance"):
            st.info("⏳ **How long until we'd know?** " + tts_sentence(stats["time_to_significance"], year_range[1]))
            st.caption("This is an estimate. It assumes the same pace of change and the same year-to-year "
                       "wobble continue.")
        if var_info.get("caveat"):
            st.warning("⚠️ " + var_info["caveat"])
        if expert:
            st.caption(f"95% confidence interval: {fmt_num(stats['ci_low_decade'])} to "
                       f"{fmt_num(stats['ci_high_decade'])} {unit}/decade. The CI comes from a Theil-Sen fit on annual "
                       f"means (slope {fmt_num(stats['annual_sen_per_decade'])}); the headline rate "
                       f"({fmt_num(stats['change_per_decade'])}) comes from the monthly test above, so they can differ slightly.")
            if not stats["ci_consistent"]:
                st.warning("The headline rate falls outside this confidence interval, because the two estimators "
                           "disagree. Treat the size of the trend as uncertain.")
        if stats["change_point_p"] < 0.05 and stats["change_point_year"]:
            st.caption(f"⚡ The data suggest an abrupt shift around **{stats['change_point_year']}**"
                       + (f" (Pettitt test, p = {fmt_p(stats['change_point_p'])})" if expert else "")
                       + ". The change may not have been steady.")

    # ---- tab 2: robustness heatmap
    with tab_solid:
        if sens is None:
            st.info("Pick at least 12 years in the sidebar to test how solid the result is.")
        else:
            st.markdown("**Does the answer depend on the years you pick?** Every square is the trend for a "
                        "different start and end year. A solid trend keeps the same colour almost everywhere.")
            st.plotly_chart(robustness_chart(sens, unit, year_range[0], year_range[1]),
                            width="stretch", key=f"rob_{pin_key}")
            verdict_box = {"robust": st.success, "fairly_consistent": st.info, "fragile": st.warning}[rob["verdict"]]
            verdict_box(robustness_sentence(rob))
            st.caption("Purple = rising, orange = falling, black dots = statistically significant for that window, "
                       "star = the period you selected. Windows are at least 10 years long. "
                       "A big colour change between neighbouring squares is a warning against cherry-picking years.")

    # ---- tab 3: AI explanation
    with tab_ai:
        st.markdown("Get a plain-English write-up of this result.")
        explain_ui(build_facts([rfacts]), pin_key)

    # ---- tab 4: scientists
    with tab_sci:
        st.write(f"**Variable:** {var_info['source']}  \n**Source:** {POWER_SOURCE}")
        test_name = "Seasonal Mann-Kendall" if method == "seasonal" else "Hamed-Rao modified Mann-Kendall"
        st.write(f"**Test:** {test_name}; Kendall's tau = {stats['tau']:.3f}, p = {fmt_p(stats['p_value'])}. "
                 f"Sen's slope = {fmt_num(rate)} {unit}/decade (95% CI {fmt_num(stats['ci_low_decade'])} to "
                 f"{fmt_num(stats['ci_high_decade'])}, from a separate Theil-Sen fit on annual means, slope "
                 f"{fmt_num(stats['annual_sen_per_decade'])}; headline and CI are different estimators). "
                 "Linear trend only. Values are model-based (reanalysis), not station measurements.")
        tts = stats.get("time_to_significance")
        if tts:
            st.write(f"**Time to significance:** regression on annual anomalies, lag-1 autocorrelation "
                     f"r = {tts['autocorr']:.2f}; ~50% power in {tts['extra_50'] or '>' + str(tts['max_extra'])} yrs, "
                     f"~80% power in {tts['extra_80'] or '>' + str(tts['max_extra'])} yrs.")
        if df["interpolated"].any():
            st.write(f"{int(df['interpolated'].sum())} missing month(s) were linearly interpolated.")
        fig2 = go.Figure(go.Scatter(x=df["date"], y=df["value"], mode="lines", name="Monthly mean",
                                    line=dict(color="#1f77b4", width=1.5)))
        fig2.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10),
                           yaxis_title=f"{var_label}", hovermode="x unified")
        st.plotly_chart(fig2, width="stretch", key=f"raw_{pin_key}")
        csv_bytes = df[["date", "value", "anomaly", "trend_line"]].to_csv(index=False).encode("utf-8")
        st.download_button(f"⬇️ Download {region['name']} data (CSV)", data=csv_bytes,
                           file_name=f"trend_{region['lat']:.2f}_{region['lon']:.2f}.csv",
                           mime="text/csv", key=f"dl_{pin_key}")
    return stats, rfacts


# ---------------------------------------------------------------- map picker
def render_map_picker():
    with st.expander("🗺️ Change location (click the map or type coordinates)", expanded=False):
        map_col1, map_col2 = st.columns([3, 1])

        with map_col2:
            if ss.mode == COMPARE:
                st.radio("Clicking the map updates:", ["Region A", "Region B"], key="active_pin")
                active = ss.active_pin
            else:
                active = "Region A"
            slot = "region_a" if active == "Region A" else "region_b"
            target = ss[slot]

            st.markdown("**Or enter coordinates:**")
            with st.form("manual_location"):
                tag = f"{slot}_{target['lat']}_{target['lon']}"
                name_in = st.text_input("Label", value=target["name"], key=f"name_{tag}")
                lat_in = st.number_input("Latitude", value=float(target["lat"]), min_value=-90.0,
                                         max_value=90.0, step=0.5, key=f"lat_{tag}")
                lon_in = st.number_input("Longitude", value=float(target["lon"]), min_value=-180.0,
                                         max_value=180.0, step=0.5, key=f"lon_{tag}")
                if st.form_submit_button("Update location", width="stretch"):
                    ss[slot] = {"name": name_in, "lat": lat_in, "lon": lon_in}
                    st.rerun()

        with map_col1:
            m = folium.Map(
                location=[20.0, 15.0], zoom_start=2,
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
                attr="Esri",
            )
            folium.Marker([ss.region_a["lat"], ss.region_a["lon"]],
                          tooltip=f"Region A: {ss.region_a['name']}",
                          icon=folium.Icon(color="purple", icon="info-sign")).add_to(m)
            if ss.mode == COMPARE:
                folium.Marker([ss.region_b["lat"], ss.region_b["lon"]],
                              tooltip=f"Region B: {ss.region_b['name']}",
                              icon=folium.Icon(color="orange", icon="info-sign")).add_to(m)

            map_data = st_folium(m, height=320, use_container_width=True, key="world_map",
                                 returned_objects=["last_clicked"])

            click = map_data.get("last_clicked") if map_data else None
            if click:
                lat = round(max(-90.0, min(90.0, click["lat"])), 4)
                lon = round(((click["lng"] + 180) % 360) - 180, 4)   # un-wrap panned maps
                # Only act on a NEW click; st_folium keeps returning the old one otherwise.
                if (lat, lon) != ss.last_click:
                    ss.last_click = (lat, lon)
                    ss[slot] = {"name": f"Selected point ({lat}°, {lon}°)", "lat": lat, "lon": lon}
                    st.rerun()


def active_regions():
    """[(pin, region, label)] for the region(s) the current mode analyzes."""
    if ss.mode == COMPARE:
        return [("a", ss.region_a, "Region A"), ("b", ss.region_b, "Region B")]
    return [("a", ss.region_a, "Target location")]


# ================================================================ VIEW: START HERE
def render_start():
    st.markdown("### 🕵️ Pick a mystery to investigate")
    st.caption("Each story loads real places and a real NASA variable. The app reports whatever the data show, "
               "including \"no clear change\".")
    names = list(STORIES)
    for row in range(0, len(names), 3):
        for col, name in zip(st.columns(3), names[row:row + 3]):
            s = STORIES[name]
            with col.container(border=True):
                st.markdown(f"#### {s['emoji']} {name}")
                st.write(s["mystery"])
                st.caption(f"Tests: {VARIABLES[s['variable']]['plain_name']} · "
                           f"{s['region_a']['name'].split(',')[0]} vs {s['region_b']['name'].split(',')[0]}")
                st.button("Investigate →", key=f"story_{name}", on_click=load_story, args=(name,),
                          width="stretch")

    st.divider()
    st.markdown("### 🧭 Or build your own investigation")

    st.markdown("**Not sure what to look at?** Describe what you are curious about and we'll suggest variables.")
    qc1, qc2 = st.columns([4, 1])
    q = qc1.text_input("Your question", key="g_q", label_visibility="collapsed",
                       placeholder="e.g. Are summers getting hotter? Is my farmland drying out? Is solar power improving?")
    qc2.button("✨ Suggest", key="g_suggest_btn", width="stretch",
               on_click=lambda: ss.__setitem__("g_suggest", suggest_variables(ss.get("g_q", ""), VARIABLES)))
    sugg = ss.get("g_suggest")
    if sugg and sugg[0]:
        labels, why, used_ai = sugg
        st.caption(("✨ AI suggestion: " if used_ai else "🔎 ") + (why or "Here are some matches."))
        for col, label in zip(st.columns(len(labels)), labels):
            col.button(f"{VARIABLES[label]['emoji']} Use {VARIABLES[label]['plain_name']}",
                       key=f"use_{label}", on_click=use_suggestion, args=(label,), width="stretch")
    elif sugg is not None and ss.get("g_q"):
        st.caption("No obvious match. Try different words, or pick a topic below.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**1. What topic?**")
        st.selectbox("Topic", CATEGORIES, key="g_cat", label_visibility="collapsed")
        opts = [lab for lab, i in VARIABLES.items() if i["category"] == ss.g_cat]
        st.selectbox("Variable", opts, key=f"g_var_{ss.g_cat}", label_visibility="collapsed",
                     format_func=lambda k: VARIABLES[k]["question"])
        chosen = VARIABLES[ss[f"g_var_{ss.g_cat}"]]
        st.caption(f"**What is it?** {chosen['definition']}  \n**Why care?** {chosen['why']}")
    with c2:
        st.markdown("**2. What kind of place?**")
        st.selectbox("Kind of place", list(PLACE_PRESETS), key="g_biome", label_visibility="collapsed")
        st.selectbox("Place", [p["name"] for p in PLACE_PRESETS[ss.g_biome]],
                     key=f"g_place_{ss.g_biome}", label_visibility="collapsed")
        st.selectbox("Compare with (optional)", ["(none)"] + list(ALL_PLACES), key="g_compare")
    with c3:
        st.markdown("**3. How far back?**")
        st.selectbox("Time window", list(TIME_WINDOWS), key="g_window", label_visibility="collapsed",
                     index=1)
        st.caption("Longer periods give more reliable answers, because short ones are dominated by weather noise.")
        st.button("🔎 Start investigating", key="g_go", type="primary", on_click=start_custom, width="stretch")

    with st.expander("How does this work?"):
        st.markdown(
            "1. **Get the data.** Monthly NASA satellite-and-model data for the place you choose.\n"
            "2. **Remove the seasons.** We compare each month with that month's normal, so summer versus winter "
            "doesn't hide the trend.\n"
            "3. **Find the direction and speed.** A robust method (Sen's slope) finds how fast things are changing.\n"
            "4. **Test whether it is real.** A Mann-Kendall test asks: *could ups and downs this size happen by chance?* "
            "If the chance is under 5%, we call it statistically significant.\n"
            "5. **Stress-test it.** We check whether the answer survives different start and end years, and estimate "
            "how many more years of data an unclear trend would need.")


# ================================================================ VIEW: DETECTIVE
def describe(region, s):
    conf_short = confidence(s["p_value"])[0]
    phrase = (var_info["up_phrase"] if s["change_per_decade"] > 0 else var_info["down_phrase"]) \
        if s["is_significant"] else "no clear change"
    extra = f", $p={fmt_p(s['p_value'])}$" if expert else ""
    return (f"**{region['name']}**: {phrase} ({fmt_num(s['change_per_decade'])} {var_info['unit']} per 10 years; "
            f"{conf_short.lower()}{extra})")


def render_detective():
    if ss.story:
        s = STORIES[ss.story]
        with st.container(border=True):
            st.markdown(f"**{s['emoji']} Case file: {ss.story}**  \n{s['mystery']}")
            st.markdown("**Clues to look for:**  \n" + "  \n".join(f"- {c}" for c in s["clues"]))
            st.button("Close case file", key="close_story", on_click=dismiss_story)

    with st.expander(f"ℹ️ What is {var_info['plain_name']}?", expanded=not expert and not ss.story):
        st.write(f"{var_info['definition']}  \n**Why it matters:** {var_info['why']}")

    if ss.mode == SINGLE:
        res = render_region_panel(ss.region_a, "Target location", "a")
        if res:
            stats_a, _ = res
            st.markdown("### 🕵️ Detective case summary")
            st.write(f"Between **{year_range[0]} and {year_range[1]}**, {describe(ss.region_a, stats_a)}.")
    else:
        col_left, col_right = st.columns(2)
        with col_left:
            res_a = render_region_panel(ss.region_a, "Region A", "a")
        with col_right:
            res_b = render_region_panel(ss.region_b, "Region B", "b")

        if res_a and res_b:
            (stats_a, facts_a), (stats_b, facts_b) = res_a, res_b
            st.divider()
            st.markdown("### 🕵️ Comparing the two places")
            opposite = (stats_a["is_significant"] and stats_b["is_significant"]
                        and stats_a["tendency"] != stats_b["tendency"])
            both_sig = stats_a["is_significant"] and stats_b["is_significant"]
            body = f"{describe(ss.region_a, stats_a)}  \n{describe(ss.region_b, stats_b)}"
            if opposite:
                st.warning(f"**🔀 Opposite trends confirmed.** The same variable is moving in opposite directions.  \n{body}")
            elif both_sig:
                st.info(f"**Both places show a real trend in the same direction.**  \n{body}")
            else:
                st.write(f"**No opposite significant trends found for this variable and period.**  \n{body}")
            with st.expander("🤖 Get an AI write-up comparing the two places", expanded=False):
                explain_ui(build_facts([facts_a, facts_b]), "cmp")


# ================================================================ VIEW: TREND SCANNER
def render_scan_result(pin, region, label):
    st.subheader(f"{label}: {region['name']}")
    err = ss.get(f"scan_err_{pin}")
    if err:
        st.error(f"Scan failed: {err}")
        return
    res = ss.get(f"scan_{pin}")
    expected = (region["lat"], region["lon"], year_range, method)
    if not res:
        st.caption("Press **Run trend scan** to analyze this location.")
        return
    if res[0] != expected:
        st.caption("Settings or location changed since the last scan. Press the button to re-run.")
        return

    scan_df = res[1]
    sig = scan_df[scan_df["Significant"]]
    if len(sig):
        top = sig.iloc[0]
        kept = int(scan_df["Holds up after multiple-test correction"].sum())
        st.success(f"**{len(sig)} of {len(scan_df)} variables show a significant trend.** Strongest evidence: "
                   f"**{top['Variable']}** ({top['Direction']}, {fmt_num(top['Rate / decade'])} {top['Unit']}/decade, "
                   f"p = {fmt_p(top['p-value'])}).")
        st.caption(f"Because many variables are tested at once, a few can look significant by pure chance. "
                   f"**{kept}** of {len(sig)} still hold up after correcting for that (Benjamini-Hochberg).")
    else:
        st.info("No variable shows a significant trend here for this period. A longer record might change that.")

    fig = go.Figure(go.Bar(
        x=scan_df["Kendall tau"], y=scan_df["Variable"], orientation="h",
        marker_color=[COL_UP if (s and t > 0) else COL_DOWN if s else COL_NS
                      for s, t in zip(scan_df["Significant"], scan_df["Kendall tau"])],
        text=[("significant" if s else "not significant") for s in scan_df["Significant"]],
        hovertemplate="%{y}<br>strength = %{x:.2f}<br>%{text}<extra></extra>"))
    fig.update_layout(height=max(280, 34 * len(scan_df)), margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(title="Trend strength (Kendall's tau)", range=[-1, 1]),
                      yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, width="stretch", key=f"scan_chart_{pin}")
    st.caption("Purple = significant increase, orange = significant decrease, grey = no clear change.")

    if expert:
        st.dataframe(scan_df, hide_index=True, width="stretch", column_config={
            "Rate / decade": st.column_config.NumberColumn(format="%+.4f"),
            "95% CI low": st.column_config.NumberColumn(format="%+.4f"),
            "95% CI high": st.column_config.NumberColumn(format="%+.4f"),
            "% of mean / decade": st.column_config.NumberColumn(format="%+.2f%%"),
            "Kendall tau": st.column_config.NumberColumn(format="%.3f"),
            "p-value": st.column_config.NumberColumn(format="%.4f"),
            "Change-point year": st.column_config.NumberColumn(format="%d"),
        })
    else:
        simple = pd.DataFrame({
            "Variable": scan_df["Variable"],
            "What's happening": [
                (VARIABLES[v]["up_phrase"] if r > 0 else VARIABLES[v]["down_phrase"]) if s else "no clear change"
                for v, r, s in zip(scan_df["Variable"], scan_df["Rate / decade"], scan_df["Significant"])],
            "Speed (per 10 years)": [f"{fmt_num(r)} {u}" for r, u in zip(scan_df["Rate / decade"], scan_df["Unit"])],
            "How sure?": [confidence(p)[0] for p in scan_df["p-value"]],
        })
        st.dataframe(simple, hide_index=True, width="stretch")

    c1, c2 = st.columns([3, 1])
    pick = c1.selectbox("Look closer at one of these", list(scan_df["Variable"]), key=f"open_{pin}")
    c2.write("")
    c2.write("")
    c2.button("Open →", key=f"open_btn_{pin}", on_click=open_variable, args=(pick,), width="stretch")


def render_scanner():
    regs = active_regions()
    st.markdown("**Which Earth-system variables are trending?** Every variable is tested for "
                f"{year_range[0]}–{year_range[1]} and ranked by evidence of a trend"
                + (" at both regions." if len(regs) == 2 else "."))
    if st.button("🔬 Run trend scan", key="run_scan"):
        with st.spinner("Scanning all variables..."):
            for pin, reg, _ in regs:
                try:
                    ss[f"scan_{pin}"] = ((reg["lat"], reg["lon"], year_range, method),
                                         get_cached_scan(reg["lat"], reg["lon"], year_range[0], year_range[1], method))
                    ss[f"scan_err_{pin}"] = None
                except Exception as e:
                    ss[f"scan_{pin}"] = None
                    ss[f"scan_err_{pin}"] = str(e)
    for col, (pin, reg, label) in zip(st.columns(len(regs)), regs):
        with col:
            render_scan_result(pin, reg, label)


# ================================================================ VIEW: REGIONAL MAP
def render_grid_result(pin, region, label, grid_key):
    st.subheader(f"{label}: {region['name']}")
    err = ss.get(f"grid_err_{pin}")
    if err:
        st.error(f"Map failed: {err}")
        return
    gres = ss.get(f"grid_{pin}")
    if not gres:
        st.caption("Press **Build trend map** to analyze the area around this location.")
        return
    if gres[0] != grid_key:
        st.caption("Settings or location changed since the last map. Press the button to rebuild it.")
        return

    gdf = gres[1]
    gm = folium.Map(location=[region["lat"], region["lon"]], zoom_start=5 if grid_key[5] <= 4 else 4,
                    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
                    attr="Esri")
    for _, r in gdf.iterrows():
        color = (COL_UP if r["rate_per_decade"] > 0 else COL_DOWN) if r["significant"] else COL_NS
        folium.CircleMarker(
            [r["lat"], r["lon"]], radius=6 + 14 * abs(r["tau"]), color=color, weight=1,
            fill=True, fill_color=color, fill_opacity=0.65 if r["significant"] else 0.3,
            tooltip=f"{r['lat']:.1f}°, {r['lon']:.1f}° | {fmt_num(r['rate_per_decade'])} {var_info['unit']}/10 yrs | p={fmt_p(r['p_value'])}",
        ).add_to(gm)
    st_folium(gm, height=400, use_container_width=True, key=f"grid_map_{pin}", returned_objects=[])

    n_up = int(((gdf["rate_per_decade"] > 0) & gdf["significant"]).sum())
    n_dn = int(((gdf["rate_per_decade"] < 0) & gdf["significant"]).sum())
    st.markdown(f"**{len(gdf)} points:** {n_up} significant increases (purple), {n_dn} significant decreases (orange), "
                f"{len(gdf) - n_up - n_dn} no clear change (grey). Circle size = trend strength.")
    n_fdr = int(gdf["significant_fdr"].sum())
    if n_up + n_dn:
        st.caption(f"{n_fdr} of the {n_up + n_dn} significant points still hold up after correcting for testing "
                   "many places at once.")
    if n_up + n_dn:
        if field_significant(gdf["p_value"].to_numpy()):
            st.caption("**Field significance:** the map as a whole shows a real signal, more than chance alone "
                       "would produce (Benjamini-Hochberg at 2×α, Wilks 2016). Neighbouring points are correlated, "
                       "so read individual dots with care.")
        else:
            st.warning("**Field significance not reached:** the scattered significant points are about what "
                       "chance alone would produce across this many tests. Do not read them as a regional trend.")
    if n_up and n_dn:
        st.warning("**Opposite trends inside the same area.** Part of this region is moving up while another part is moving down.")
    st.download_button("⬇️ Download grid results (CSV)", gdf.to_csv(index=False).encode("utf-8"),
                       file_name=f"regional_trend_grid_{pin}.csv", mime="text/csv", key=f"dl_grid_{pin}")


def render_grid():
    regs = active_regions()
    st.markdown(f"**Where is {var_info['plain_name']} changing?** The same trend test is run at every point of a grid "
                "around each location, so you can see areas moving in different directions.")
    g1, g2 = st.columns(2)
    half_width = g1.slider("Half-width of area (degrees)", 2, 10, 4, step=2, key="grid_half")
    step = g2.select_slider("Grid spacing (degrees)", options=[1, 2, 3, 4], value=2, key="grid_step")
    n_pts = (int(2 * half_width / step) + 1) ** 2
    st.caption(f"{n_pts} points per location ({n_pts * len(regs)} in total). 1° is about 111 km; "
               "the source data are ~50 km cells.")

    def grid_key_for(reg):
        return (reg["lat"], reg["lon"], var_info["param"], year_range, method, half_width, step)

    if n_pts > 49:
        st.warning("Too many points. Increase the spacing or reduce the area (max 49 points per location).")
    elif st.button("🗺️ Build trend map", key="run_grid"):
        with st.spinner(f"Fetching and testing {n_pts * len(regs)} points from NASA POWER..."):
            for pin, reg, _ in regs:
                try:
                    ss[f"grid_{pin}"] = (grid_key_for(reg),
                                         get_cached_grid(reg["lat"], reg["lon"], var_info["param"], year_range[0],
                                                         year_range[1], method, float(half_width), float(step)))
                    ss[f"grid_err_{pin}"] = None
                except Exception as e:
                    ss[f"grid_{pin}"] = None
                    ss[f"grid_err_{pin}"] = str(e)
    for col, (pin, reg, label) in zip(st.columns(len(regs)), regs):
        with col:
            render_grid_result(pin, reg, label, grid_key_for(reg))


# ================================================================ ROUTER
if view == V_START:
    render_start()
else:
    render_map_picker()
    st.divider()
    if view == V_DET:
        render_detective()
    elif view == V_SCAN:
        render_scanner()
    else:
        render_grid()

st.divider()
st.caption(f"Data: {POWER_SOURCE}. Values are reanalysis (model + observations), not station readings.")
