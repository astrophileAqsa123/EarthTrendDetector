# Trend scanner: every variable at the chosen place(s)
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import core
import ui
from config import VARIABLES

ss = st.session_state
core.sidebar()
S = core.cfg()
year_range, method, expert = S.year_range, S.method, S.expert

ui.page_header("Trend scanner", "Test every Earth-system variable at once and see which ones are changing most clearly.")
core.render_map_picker()


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
                   f"**{top['Variable']}** ({top['Direction']}, {core.fmt_num(top['Rate / decade'])} {top['Unit']}/decade, "
                   f"p = {core.fmt_p(top['p-value'])}).")
        st.caption(f"Because many variables are tested at once, a few can look significant by pure chance. "
                   f"**{kept}** of {len(sig)} still hold up after correcting for that (Benjamini-Hochberg).")
    else:
        st.info("No variable shows a significant trend here for this period. A longer record might change that.")

    fig = go.Figure(go.Bar(
        x=scan_df["Kendall tau"], y=scan_df["Variable"], orientation="h",
        marker_color=[core.COL_UP if (s and t > 0) else core.COL_DOWN if s else core.COL_NS
                      for s, t in zip(scan_df["Significant"], scan_df["Kendall tau"])],
        text=[("significant" if s else "not significant") for s in scan_df["Significant"]],
        hovertemplate="%{y}<br>strength = %{x:.2f}<br>%{text}<extra></extra>"))
    fig.update_layout(height=max(280, 34 * len(scan_df)), margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(title="Trend strength (Kendall's tau)", range=[-1, 1]),
                      yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, width="stretch", theme=None, key=f"scan_chart_{pin}")
    ui.legend_key()

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
            "Speed (per 10 years)": [f"{core.fmt_num(r)} {u}" for r, u in zip(scan_df["Rate / decade"], scan_df["Unit"])],
            "How sure?": [core.confidence(p)[0] for p in scan_df["p-value"]],
        })
        st.dataframe(simple, hide_index=True, width="stretch")

    c1, c2 = st.columns([3, 1])
    pick = c1.selectbox("Look closer at one of these", list(scan_df["Variable"]), key=f"open_{pin}")
    c2.write("")
    c2.write("")
    if c2.button("Open", key=f"open_btn_{pin}", on_click=core.open_variable, args=(pick,), width="stretch"):
        st.switch_page(core.RESULTS)


regs = core.active_regions()
st.markdown("**Which Earth-system variables are trending?** Every variable is tested for "
            f"{year_range[0]}–{year_range[1]} and ranked by evidence of a trend"
            + (" at both regions." if len(regs) == 2 else "."))
if st.button("Run trend scan", key="run_scan", type="primary"):
    with st.spinner("Scanning all variables..."):
        for pin, reg, _ in regs:
            try:
                ss[f"scan_{pin}"] = ((reg["lat"], reg["lon"], year_range, method),
                                     core.get_cached_scan(reg["lat"], reg["lon"], year_range[0], year_range[1], method))
                ss[f"scan_err_{pin}"] = None
            except Exception as e:
                ss[f"scan_{pin}"] = None
                ss[f"scan_err_{pin}"] = str(e)
for col, (pin, reg, label) in zip(st.columns(len(regs)), regs):
    with col:
        render_scan_result(pin, reg, label)
core.footer()
