# Regional map: the trend test at every point of a grid
import folium
import streamlit as st
from streamlit_folium import st_folium

import core
import ui
from stats_engine import field_significant

ss = st.session_state
core.sidebar()
S = core.cfg()
var_info, year_range, method = S.var_info, S.year_range, S.method

ui.page_header("Regional map", "See whether a whole area is changing the same way, or whether parts of it move in opposite directions.")
core.render_map_picker()


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
                    tiles=core.TILES, attr="Esri")
    for _, r in gdf.iterrows():
        color = (core.COL_UP if r["rate_per_decade"] > 0 else core.COL_DOWN) if r["significant"] else core.COL_NS
        folium.CircleMarker(
            [r["lat"], r["lon"]], radius=6 + 14 * abs(r["tau"]), color=color, weight=1,
            fill=True, fill_color=color, fill_opacity=0.65 if r["significant"] else 0.3,
            tooltip=f"{r['lat']:.1f}°, {r['lon']:.1f}° | {core.fmt_num(r['rate_per_decade'])} {var_info['unit']}/10 yrs | p={core.fmt_p(r['p_value'])}",
        ).add_to(gm)
    st_folium(gm, height=400, use_container_width=True, key=f"grid_map_{pin}", returned_objects=[])
    ui.legend_key()

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
    st.download_button("Download grid results (CSV)", gdf.to_csv(index=False).encode("utf-8"),
                       file_name=f"regional_trend_grid_{pin}.csv", mime="text/csv", key=f"dl_grid_{pin}")


regs = core.active_regions()
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
elif st.button("Build trend map", key="run_grid", type="primary"):
    with st.spinner(f"Fetching and testing {n_pts * len(regs)} points from NASA POWER..."):
        for pin, reg, _ in regs:
            try:
                ss[f"grid_{pin}"] = (grid_key_for(reg),
                                     core.get_cached_grid(reg["lat"], reg["lon"], var_info["param"], year_range[0],
                                                          year_range[1], method, float(half_width), float(step)))
                ss[f"grid_err_{pin}"] = None
            except Exception as e:
                ss[f"grid_{pin}"] = None
                ss[f"grid_err_{pin}"] = str(e)
for col, (pin, reg, label) in zip(st.columns(len(regs)), regs):
    with col:
        render_grid_result(pin, reg, label, grid_key_for(reg))
core.footer()
