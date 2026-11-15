# core.py
"""Shared state, cached computations and reusable blocks used by every page."""
import json
from types import SimpleNamespace

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

import ui
from ai_helper import AUDIENCES, AIUnavailable, ai_configured, explain_results
from config import POWER_SOURCE, STORIES, TIME_WINDOWS, VARIABLES
from data_fetcher import fetch_time_series
from plain import confidence, fmt_abs, fmt_num, fmt_p, headline, robustness_sentence, template_narrative, tts_sentence
from scanner import scan_grid, scan_variables
from stats_engine import METHODS, add_anomalies, analyze_trend, robustness_summary, window_sensitivity

SINGLE = "Single Location"
COMPARE = "Compare Two Regions"

# page files (relative to app.py), used by st.Page and st.switch_page
HOME = "views/home.py"
CASES = "views/cases.py"
BUILD = "views/build.py"
RESULTS = "views/results.py"
SCANNER = "views/scanner.py"
MAP = "views/regional_map.py"
HOW = "views/how_it_works.py"

COL_UP, COL_DOWN, COL_NS = ui.UP, ui.DOWN, ui.NEUTRAL
TILES = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"

ss = st.session_state

# widget-backed settings that must survive moving between pages
_PERSIST = ["mode", "level", "var_label", "year_range", "method_label"]


def init_state():
    ss.setdefault("mode", COMPARE)
    ss.setdefault("level", "Beginner")
    ss.setdefault("var_label", list(VARIABLES)[0])
    ss.setdefault("year_range", (2000, 2025))
    ss.setdefault("method_label", list(METHODS)[0])
    ss.setdefault("region_a", {"name": "Islamabad, Pakistan", "lat": 33.6844, "lon": 73.0479})
    ss.setdefault("region_b", {"name": "Longyearbyen, Svalbard", "lat": 78.2232, "lon": 15.6267})
    ss.setdefault("last_click", None)
    ss.setdefault("story", None)
    # Streamlit drops a widget's value when its page is not shown. Re-assigning keeps it.
    for k in _PERSIST:
        ss[k] = ss[k]


def cfg() -> SimpleNamespace:
    """Current settings, read fresh from session state (never stored globally)."""
    expert = ss.level == "Expert"
    return SimpleNamespace(
        expert=expert, var_label=ss.var_label, var_info=VARIABLES[ss.var_label],
        year_range=ss.year_range, method=METHODS[ss.method_label] if expert else "seasonal")


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


# ---------------------------------------------------------------- sidebar (analysis pages only)
def sidebar():
    with st.sidebar:
        st.radio("Display mode", ["Beginner", "Expert"], key="level", horizontal=True,
                 help="Beginner uses everyday words. Expert shows the full statistics.")
        expert = ss.level == "Expert"

        st.header("Question")
        st.radio("Places to analyse", [SINGLE, COMPARE], key="mode")
        st.selectbox("Earth system question", list(VARIABLES), key="var_label",
                     format_func=lambda k: ui.clean(VARIABLES[k]["question"]))
        st.caption(f"**What is it?** {VARIABLES[ss.var_label]['definition']}")

        st.header("Time period")
        st.slider("Analysis period (years)", 1981, 2025, key="year_range")
        if ss.year_range[1] - ss.year_range[0] + 1 < 10:
            st.warning("Use 10+ years for reliable climate trends. Short periods are dominated by weather noise.")

        if expert:
            st.header("Confidence test")
            st.selectbox("Significance test", list(METHODS), key="method_label")
            st.caption("Hamed-Rao corrects the p-value for autocorrelation (fewer false positives).")

        st.divider()
        st.caption("AI explanations: " + ("**on** (Groq)" if ai_configured()
                                          else "**off**. Set `GROQ_API_KEY` to turn on. A built-in explanation is used instead."))


# ---------------------------------------------------------------- callbacks
def load_story(name: str):
    s = STORIES[name]
    ss.region_a, ss.region_b = dict(s["region_a"]), dict(s["region_b"])
    ss.var_label = s["variable"]
    ss.year_range = tuple(s["years"])
    ss.mode = COMPARE
    ss.story = name


def dismiss_story():
    ss.story = None


def open_variable(label: str):
    ss.var_label = label


# ---------------------------------------------------------------- shared helpers
FALLBACK_KEYS = {"direction_words", "total_abs", "rate_abs", "confidence_sentence",
                 "time_to_significance_sentence", "robustness_sentence"}


def ai_view(facts: dict) -> dict:
    """Facts as sent to the AI: only computed numbers, none of the pre-written fallback sentences."""
    out = {k: v for k, v in facts.items() if k != "regions"}
    out["regions"] = [{k: v for k, v in r.items() if k not in FALLBACK_KEYS} for r in facts["regions"]]
    return out


def region_facts(region: dict, stats: dict, rob: dict | None) -> dict:
    S = cfg()
    var_info = S.var_info
    rate = stats["change_per_decade"]
    conf_short, conf_sentence, _ = confidence(stats["p_value"])
    tts = stats.get("time_to_significance")
    last_year = S.year_range[1]
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
    S = cfg()
    return {
        "variable": S.var_label, "plain_name": S.var_info["plain_name"], "definition": S.var_info["definition"],
        "unit": S.var_info["unit"], "period": f"{S.year_range[0]}-{S.year_range[1]}",
        "test": "Seasonal Mann-Kendall" if S.method == "seasonal" else "Hamed-Rao modified Mann-Kendall",
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
        st.caption("Written by an AI (Groq) from the numbers computed on this page. "
                   "It describes the results but never calculates them. Double-check anything important.")
    else:
        st.caption(f"Built-in explanation shown. ({saved[2]})")


def explain_ui(facts: dict, pin_key: str):
    c1, c2 = st.columns([2, 1])
    audience = c1.selectbox("Explain it for…", list(AUDIENCES), key=f"aud_{pin_key}")
    c2.write("")
    c2.write("")
    if c2.button("Explain", key=f"ai_{pin_key}", width="stretch"):
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


def active_regions():
    """[(pin, region, label)] for the region(s) the current mode analyzes."""
    if ss.mode == COMPARE:
        return [("a", ss.region_a, "Region A"), ("b", ss.region_b, "Region B")]
    return [("a", ss.region_a, "Target location")]


def footer():
    st.divider()
    st.caption(f"Data: {POWER_SOURCE}. Values are reanalysis (model + observations), not station readings.")


# ---------------------------------------------------------------- region panel
def render_region_panel(region: dict, label: str, pin_key: str):
    S = cfg()
    var_info, year_range, method, expert, var_label = S.var_info, S.year_range, S.method, S.expert, S.var_label
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
    conf_short, conf_sentence, _ = confidence(stats["p_value"])
    sens = get_cached_sensitivity(df) if len(df) // 12 >= 12 else None
    rob = robustness_summary(sens, rate) if sens is not None else None
    rfacts = region_facts(region, stats, rob)

    state = ("up" if rate > 0 else "down") if stats["is_significant"] else "none"
    ui.verdict(pin_key, state, headline(region["name"], var_info, stats, year_range), conf_short, conf_sentence)

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

    tab_trend, tab_solid, tab_ai, tab_sci = st.tabs(["The trend", "Is it solid?", "Explain it", "For scientists"])

    with tab_trend:
        line_col = (COL_UP if rate > 0 else COL_DOWN) if stats["is_significant"] else COL_NS
        fig = go.Figure()
        if expert:
            fig.add_trace(go.Scatter(x=df["date"], y=df["anomaly"], mode="lines", name="Monthly anomaly",
                                     line=dict(color="rgba(23,96,125,0.28)", width=1.2)))
        fig.add_trace(go.Scatter(x=annual["date"], y=annual["anomaly"], mode="lines+markers",
                                 name="Yearly average", line=dict(color=ui.ACCENT, width=2.4)))
        fig.add_trace(go.Scatter(x=df["date"], y=df["trend_line"], mode="lines",
                                 name=f"Overall direction ({fmt_num(rate)}/10 yrs)",
                                 line=dict(color=line_col, width=3, dash="dash")))
        fig.add_hline(y=0, line_width=1, line_color="rgba(128,128,128,0.5)")
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10),
                          yaxis_title=(f"Anomaly ({unit})" if expert else f"Difference from normal ({unit})"),
                          hovermode="x unified",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, width="stretch", theme=None, key=f"anom_{pin_key}")
        st.caption("Each dot is one year compared with this place's normal (its average for the same calendar "
                   "months). The dashed line shows the overall direction, with the seasons removed so they don't "
                   "hide the trend.")

        if not stats["is_significant"] and stats.get("time_to_significance"):
            st.info("**How long until we'd know?** " + tts_sentence(stats["time_to_significance"], year_range[1]))
            st.caption("This is an estimate. It assumes the same pace of change and the same year-to-year "
                       "wobble continue.")
        if var_info.get("caveat"):
            st.warning(var_info["caveat"])
        if expert:
            st.caption(f"95% confidence interval: {fmt_num(stats['ci_low_decade'])} to "
                       f"{fmt_num(stats['ci_high_decade'])} {unit}/decade. The CI comes from a Theil-Sen fit on annual "
                       f"means (slope {fmt_num(stats['annual_sen_per_decade'])}); the headline rate "
                       f"({fmt_num(stats['change_per_decade'])}) comes from the monthly test above, so they can differ slightly.")
            if not stats["ci_consistent"]:
                st.warning("The headline rate falls outside this confidence interval, because the two estimators "
                           "disagree. Treat the size of the trend as uncertain.")
        if stats["change_point_p"] < 0.05 and stats["change_point_year"]:
            st.caption(f"The data suggest an abrupt shift around **{stats['change_point_year']}**"
                       + (f" (Pettitt test, p = {fmt_p(stats['change_point_p'])})" if expert else "")
                       + ". The change may not have been steady.")

    with tab_solid:
        if sens is None:
            st.info("Pick at least 12 years in the sidebar to test how solid the result is.")
        else:
            st.markdown("**Does the answer depend on the years you pick?** Every square is the trend for a "
                        "different start and end year. A solid trend keeps the same colour almost everywhere.")
            st.plotly_chart(robustness_chart(sens, unit, year_range[0], year_range[1]),
                            width="stretch", theme=None, key=f"rob_{pin_key}")
            verdict_box = {"robust": st.success, "fairly_consistent": st.info, "fragile": st.warning}[rob["verdict"]]
            verdict_box(robustness_sentence(rob))
            st.caption("Purple = rising, orange = falling, black dots = statistically significant for that window, "
                       "star = the period you selected. Windows are at least 10 years long. "
                       "A big colour change between neighbouring squares is a warning against cherry-picking years.")

    with tab_ai:
        st.markdown("Get a plain-English write-up of this result.")
        explain_ui(build_facts([rfacts]), pin_key)

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
                                    line=dict(color=ui.ACCENT, width=1.5)))
        fig2.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10),
                           yaxis_title=f"{var_label}", hovermode="x unified")
        st.plotly_chart(fig2, width="stretch", theme=None, key=f"raw_{pin_key}")
        csv_bytes = df[["date", "value", "anomaly", "trend_line"]].to_csv(index=False).encode("utf-8")
        st.download_button(f"Download {region['name']} data (CSV)", data=csv_bytes,
                           file_name=f"trend_{region['lat']:.2f}_{region['lon']:.2f}.csv",
                           mime="text/csv", key=f"dl_{pin_key}")
    return stats, rfacts


# ---------------------------------------------------------------- map picker
def render_map_picker():
    with st.expander("Change places (click the map or type coordinates)", expanded=False):
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
            m = folium.Map(location=[20.0, 15.0], zoom_start=2, tiles=TILES, attr="Esri")
            folium.Marker([ss.region_a["lat"], ss.region_a["lon"]],
                          tooltip=f"Region A: {ss.region_a['name']}",
                          icon=folium.Icon(color="darkblue", icon="info-sign")).add_to(m)
            if ss.mode == COMPARE:
                folium.Marker([ss.region_b["lat"], ss.region_b["lon"]],
                              tooltip=f"Region B: {ss.region_b['name']}",
                              icon=folium.Icon(color="cadetblue", icon="info-sign")).add_to(m)

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
