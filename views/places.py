# City & country trends: every variable at once, for one city or for a whole country
import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

import core
import places
import ui
from config import CATEGORIES, VARIABLES
from scanner import summarize_places

ss = st.session_state
core.sidebar_period()
S = core.cfg()
year_range, method, expert = S.year_range, S.method, S.expert
CITY, COUNTRY = core.KIND_CITY, core.KIND_COUNTRY

ui.page_header("City & country trends",
               "Choose a city or a whole country and see how every Earth-system variable has changed, "
               "from temperature to rainfall to soil moisture.")


# ---------------------------------------------------------------- small helpers
def plain(label: str) -> str:
    name = VARIABLES[label]["plain_name"]
    return name[:1].upper() + name[1:]


def state_of(stats: dict) -> str:
    if not stats["is_significant"]:
        return "none"
    return "up" if stats["change_per_decade"] > 0 else "down"


def phrase_of(label: str, stats: dict) -> str:
    if not stats["is_significant"]:
        return "No clear change"
    p = VARIABLES[label]["up_phrase" if stats["change_per_decade"] > 0 else "down_phrase"]
    return p[:1].upper() + p[1:]


def ensure_option(key: str, options: list):
    """Keep a selectbox's remembered value valid when its options change."""
    if options and ss.get(key) not in options:
        ss[key] = options[0]


# ---------------------------------------------------------------- picker
with st.container(key="picker"):
    st.radio("Show trends for", [CITY, COUNTRY], key="pl_kind", horizontal=True)
    c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment="bottom")
    c1.selectbox("Country", places.country_names(), key="pl_country")
    country = ss.pl_country
    cinfo = places.country(country)

    pts, place_name, region, can_run = [], country, None, True
    if ss.pl_kind == CITY:
        cities = places.cities_of(country)
        if cities:
            if ss.pl_city not in cities:
                ss.pl_city = places.default_city(country)
            c2.selectbox("City", list(cities), key="pl_city")
            pick = cities[ss.pl_city]
            pts = [(pick["lat"], pick["lon"])]
            place_name = f"{pick['name']}, {country}"
            region = {"name": place_name, "lat": pick["lat"], "lon": pick["lon"]}
            k, sig_id = 1, ss.pl_city
        else:
            can_run = False
            c2.caption("No cities are listed for this country. Choose “Whole country” instead.")
            k, sig_id = 0, None
    else:
        n_max = len(cinfo["points"])
        if n_max > 2:
            ss.pl_points = max(2, min(ss.pl_points, n_max))
            c2.slider("Sample points", 2, n_max, key="pl_points",
                      help="The country figure is the average of these points. More points describe the country "
                           "better but take longer to load.")
        k, sig_id = min(ss.pl_points, n_max), None
        pts = places.country_points(country, k)
    run = c3.button("Show trends", key="pl_run", type="primary", width="stretch", disabled=not can_run)

    if ss.pl_kind == CITY and pts:
        st.caption(f"{pick['name']} has about {places.fmt_pop(pick['pop'])}. The data describes the ~50 km grid cell "
                   f"around {pts[0][0]:.2f}°, {pts[0][1]:.2f}°, not a single weather station.")
    elif ss.pl_kind == COUNTRY:
        where = ("spread across the main landmass (remote islands and overseas territories are left out)"
                 if cinfo["note"] == "main landmass" else "placed at the country's largest cities")
        st.caption(f"{k} sample point{'s' if k != 1 else ''} {where}. The country trend is the trend of their average.")

sig = (ss.pl_kind, country, sig_id, k, year_range, method)

autorun = ss.pop("pl_autorun", False)     # set by the landing page so the result is ready on arrival
if (run or autorun) and pts:
    slow = len(pts) > 1
    msg = (f"Fetching NASA data for {len(pts)} points across {country}. This can take up to a minute..."
           if slow else f"Fetching NASA data for {place_name}...")
    try:
        with st.spinner(msg):
            data = core.get_cached_places(tuple(pts), year_range[0], year_range[1], method)
        ss.pl_result = (sig, data, None, place_name, region)
    except Exception as e:
        ss.pl_result = (sig, None, str(e), place_name, region)


# ---------------------------------------------------------------- one variable card
def trend_figure(df: pd.DataFrame, stats: dict, unit: str) -> go.Figure:
    state = state_of(stats)
    line_col = {"up": core.COL_UP, "down": core.COL_DOWN, "none": core.COL_NS}[state]
    annual = df.groupby(df["date"].dt.year)["anomaly"].mean().rename_axis("year").reset_index()
    annual["date"] = pd.to_datetime(annual["year"].astype(str) + "-07-01")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=annual["date"], y=annual["anomaly"], mode="lines+markers", name="Yearly average",
                             line=dict(color=ui.ACCENT, width=2), marker=dict(size=4),
                             hovertemplate=f"%{{x|%Y}}: %{{y:+.2f}} {unit}<extra></extra>"))
    fig.add_trace(go.Scatter(x=df["date"], y=stats["trend_line"], mode="lines", name="Overall direction",
                             line=dict(color=line_col, width=3, dash="dash"), hoverinfo="skip"))
    fig.add_hline(y=0, line_width=1, line_color="rgba(128,128,128,0.5)")
    fig.update_layout(height=220, margin=dict(l=4, r=4, t=6, b=4), showlegend=False,
                      yaxis_title=f"Change ({unit})", yaxis_title_font_size=11)
    return fig


def variable_card(label: str, v: dict, idx: int, is_country: bool):
    info, stats, pts_stats = VARIABLES[label], v["stats"], v["points"]
    state = state_of(stats)
    conf_short = core.confidence(stats["p_value"])[0]
    with st.container(key=f"vcard-{state}-{idx}"):
        st.markdown(f"**{plain(label)}**")
        st.markdown(f'<span class="state-pill state-{state}">{phrase_of(label, stats)}</span>'
                    f'<span class="conf-text">{conf_short}</span>', unsafe_allow_html=True)
        st.plotly_chart(trend_figure(v["df"], stats, info["unit"]), width="stretch", theme=None,
                        key=f"pl_chart_{idx}")
        line = f"{core.fmt_num(stats['change_per_decade'])} {info['unit']} per 10 years"
        if expert:
            line += f" · p = {core.fmt_p(stats['p_value'])} · tau = {stats['tau']:.2f}"
        st.caption(line)
        if is_country and pts_stats:
            up = sum(1 for p in pts_stats if p["significant"] and p["rate"] > 0)
            down = sum(1 for p in pts_stats if p["significant"] and p["rate"] < 0)
            st.caption(f"Across {len(pts_stats)} points: {up} up, {down} down, {len(pts_stats) - up - down} unclear.")


# ---------------------------------------------------------------- results
def overview(data: dict, summ: pd.DataFrame, place_name: str, is_country: bool):
    sig_rows = summ[summ["Significant"]]
    if len(sig_rows):
        top = sig_rows.iloc[0]
        kept = int(summ["Holds up after multiple-test correction"].sum())
        word = VARIABLES[top["Variable"]]["up_phrase" if top["Rate / decade"] > 0 else "down_phrase"]
        st.success(f"**{len(sig_rows)} of {len(summ)} variables show a significant trend in {place_name}.** "
                   f"Strongest evidence: **{VARIABLES[top['Variable']]['plain_name']}**, {word} "
                   f"({core.fmt_num(top['Rate / decade'])} {top['Unit']} per 10 years).")
        st.caption(f"Because many variables are tested at once, a few can look significant by pure chance. "
                   f"**{kept}** of {len(sig_rows)} still hold up after correcting for that (Benjamini-Hochberg).")
    else:
        st.info(f"No variable shows a significant trend in {place_name} for this period. A longer record might change that.")

    names = [plain(v) for v in summ["Variable"]]
    fig = go.Figure(go.Bar(
        x=summ["Kendall tau"], y=names, orientation="h",
        marker_color=[core.COL_UP if (s and t > 0) else core.COL_DOWN if s else core.COL_NS
                      for s, t in zip(summ["Significant"], summ["Kendall tau"])],
        text=["significant" if s else "not significant" for s in summ["Significant"]],
        hovertemplate="%{y}<br>strength = %{x:.2f}<br>%{text}<extra></extra>"))
    fig.update_layout(height=max(300, 34 * len(summ)), margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(title="Trend strength (Kendall's tau)", range=[-1, 1]),
                      yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, width="stretch", theme=None, key="pl_overview_chart")
    ui.legend_key()

    if expert:
        show = summ if is_country else summ.drop(columns=["Points up", "Points down", "Points unclear"])
        st.dataframe(show, hide_index=True, width="stretch", height=35 * (len(show) + 1) + 3, column_config={
            "Rate / decade": st.column_config.NumberColumn(format="%+.4f"),
            "95% CI low": st.column_config.NumberColumn(format="%+.4f"),
            "95% CI high": st.column_config.NumberColumn(format="%+.4f"),
            "Kendall tau": st.column_config.NumberColumn(format="%.3f"),
            "p-value": st.column_config.NumberColumn(format="%.4f"),
        })
    else:
        table = {
            "Variable": names,
            "What's happening": [
                (VARIABLES[v]["up_phrase"] if r > 0 else VARIABLES[v]["down_phrase"]) if s else "no clear change"
                for v, r, s in zip(summ["Variable"], summ["Rate / decade"], summ["Significant"])],
            "Speed (per 10 years)": [f"{core.fmt_num(r)} {u}" for r, u in zip(summ["Rate / decade"], summ["Unit"])],
            "How sure?": [core.confidence(p)[0] for p in summ["p-value"]],
        }
        if is_country:
            table["Points that agree"] = [f"{u} up, {d} down, {n} unclear" for u, d, n in
                                          zip(summ["Points up"], summ["Points down"], summ["Points unclear"])]
        st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch", height=35 * (len(summ) + 1) + 3)

    st.download_button("Download this table (CSV)", data=summ.to_csv(index=False).encode("utf-8"),
                       file_name=f"trends_{place_name.replace(', ', '_').replace(' ', '-')}.csv",
                       mime="text/csv", key="pl_dl")


def country_map(data: dict):
    options = list(data["vars"])
    ensure_option("pl_map_var", options)
    st.selectbox("Colour the points by", options, key="pl_map_var", format_func=plain)
    pts_stats = data["vars"][ss.pl_map_var]["points"]
    if not pts_stats:
        st.caption("No per-point results for this variable.")
        return
    unit = VARIABLES[ss.pl_map_var]["unit"]
    lats, lons = [p["lat"] for p in pts_stats], [p["lon"] for p in pts_stats]
    m = folium.Map(location=[sum(lats) / len(lats), sum(lons) / len(lons)], zoom_start=4,
                   tiles=core.TILES, attr="Esri")
    for p in pts_stats:
        color = (core.COL_UP if p["rate"] > 0 else core.COL_DOWN) if p["significant"] else core.COL_NS
        folium.CircleMarker(
            [p["lat"], p["lon"]], radius=9, color=color, weight=1, fill=True, fill_color=color,
            fill_opacity=0.75 if p["significant"] else 0.35,
            tooltip=f"{p['lat']:.1f}°, {p['lon']:.1f}° | {core.fmt_num(p['rate'])} {unit}/10 yrs "
                    f"| p={core.fmt_p(p['p_value'])}").add_to(m)
    if len(pts_stats) > 1:
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(30, 30))
    st_folium(m, height=360, use_container_width=True, key="pl_map", returned_objects=[])
    ui.legend_key()


def render_result(res: tuple):
    _, data, err, place_name, region = res
    if err:
        st.error(f"Could not analyse {place_name}: {err}")
        return
    is_country = res[0][0] == COUNTRY
    summ = summarize_places(data)

    st.markdown(f"### {place_name}")
    if is_country and data["n_ok"] < data["n_points"]:
        st.warning(f"{data['n_points'] - data['n_ok']} of {data['n_points']} sample points could not be loaded. "
                   f"The average uses the other {data['n_ok']}.")
    missing = len(VARIABLES) - len(data["vars"])
    if missing:
        st.caption(f"{missing} variable{'s' if missing != 1 else ''} had too little data here and "
                   f"{'are' if missing != 1 else 'is'} left out.")
    st.caption("In each chart the line is the yearly average compared with this place's normal. The dashed line is "
               "the overall direction, with the seasons removed so they don't hide the trend.")

    tabs = st.tabs(["Overview"] + [ui.clean(c) for c in CATEGORIES])
    with tabs[0]:
        overview(data, summ, place_name, is_country)
        if is_country and data["n_ok"] > 1:
            with st.expander("Where does the country figure come from?"):
                country_map(data)
        if not is_country and region:
            st.divider()
            o1, o2 = st.columns([3, 1], vertical_alignment="bottom")
            options = list(data["vars"])
            ensure_option("pl_open_var", options)
            o1.selectbox("Look closer at one variable", options, key="pl_open_var", format_func=plain)
            if o2.button("Open full analysis", key="pl_open_btn", width="stretch",
                         on_click=core.open_city, args=(region, ss.pl_open_var)):
                st.switch_page(core.RESULTS)
    for tab, cat in zip(tabs[1:], CATEGORIES):
        with tab:
            members = [(i, lab) for i, (lab, info) in enumerate(VARIABLES.items())
                       if info["category"] == cat and lab in data["vars"]]
            if not members:
                st.caption("No data for this group.")
            for row in range(0, len(members), 3):
                for col, (i, lab) in zip(st.columns(3), members[row:row + 3]):
                    with col:
                        variable_card(lab, data["vars"][lab], i, is_country)
    with st.expander("What do these variables mean?"):
        for lab, info in VARIABLES.items():
            st.markdown(f"**{plain(lab)}.** {info['definition']} {info['why']}")


res = ss.get("pl_result")
if not res:
    st.info("Choose a place and press **Show trends**. A city loads in a few seconds. A whole country "
            "samples several points and can take up to a minute.")
elif res[0] != sig:
    st.caption("The place or settings changed since the last result. Press **Show trends** to update.")
else:
    render_result(res)
core.footer()
