# scanner.py
"""Trend Scanner (rank all variables for a place) and Regional Trend Map (grid of slopes)."""
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

from config import VARIABLES
from data_fetcher import fetch_many, fetch_time_series
from stats_engine import add_anomalies, analyze_trend, benjamini_hochberg, field_significant


def scan_variables(lat: float, lon: float, start_year: int, end_year: int, method: str) -> pd.DataFrame:
    """Analyze every variable in config.VARIABLES for one location, ranked by evidence of a trend."""
    params = [v["param"] for v in VARIABLES.values()]
    data = fetch_many(lat, lon, params, start_year, end_year)

    rows = []
    for label, info in VARIABLES.items():
        df = data.get(info["param"])
        if df is None:
            continue
        try:
            df = add_anomalies(df)
            s = analyze_trend(df, method)
        except ValueError:
            continue
        rows.append({
            "Variable": label,
            "Unit": info["unit"],
            "Rate / decade": s["change_per_decade"],
            "95% CI low": s["ci_low_decade"],
            "95% CI high": s["ci_high_decade"],
            # meaningless for °C (arbitrary zero); suppressed when the mean is within ~2 noise-SDs of zero
            "% of mean / decade": (s["pct_of_mean_per_decade"]
                                   if info["unit"] != "°C" and s["pct_of_mean_per_decade"] is not None else np.nan),
            "Kendall tau": s["tau"],
            "p-value": s["p_value"],
            "Significant": s["is_significant"],
            "Change-point year": s["change_point_year"] if s["change_point_p"] < 0.05 else None,
            "Direction": s["tendency"],
        })
    if not rows:
        raise ValueError("No variable had enough data to analyze at this location.")
    out = pd.DataFrame(rows)
    # Many variables are tested at once, so some will look significant by pure chance.
    out["Holds up after multiple-test correction"] = benjamini_hochberg(out["p-value"].to_numpy()) & out["Significant"].to_numpy()
    out["_abs_tau"] = out["Kendall tau"].abs()
    out = out.sort_values(["Significant", "_abs_tau"], ascending=[False, False]).drop(columns="_abs_tau")
    return out.reset_index(drop=True)


def scan_grid(lat: float, lon: float, param: str, start_year: int, end_year: int,
              method: str, half_width: float = 4.0, step: float = 2.0) -> pd.DataFrame:
    """Trend at each point of a square grid centred on (lat, lon). Spacing should be >= 1 degree
    because the underlying MERRA-2 grid is ~0.5 x 0.625 degrees."""
    offsets = np.arange(-half_width, half_width + 1e-9, step)
    points = [(float(np.clip(lat + dy, -89.5, 89.5)), float(((lon + dx + 180) % 360) - 180))
              for dy in offsets for dx in offsets]

    def work(pt):
        try:
            df = add_anomalies(fetch_time_series(pt[0], pt[1], param, start_year, end_year))
            s = analyze_trend(df, method)
        except Exception:
            return None  # ocean / missing cell -> skip
        return {"lat": pt[0], "lon": pt[1], "rate_per_decade": s["change_per_decade"],
                "tau": s["tau"], "p_value": s["p_value"], "significant": s["is_significant"]}

    with ThreadPoolExecutor(max_workers=4) as ex:
        results = [r for r in ex.map(work, points) if r]
    if not results:
        raise ValueError("No grid point returned usable data (is the area all ocean?).")
    out = pd.DataFrame(results)
    out["significant_fdr"] = benjamini_hochberg(out["p_value"].to_numpy()) & out["significant"].to_numpy()
    out.attrs["field_significant"] = field_significant(out["p_value"].to_numpy())
    return out


def analyze_points(points: list, start_year: int, end_year: int, method: str) -> dict:
    """Trend of EVERY variable for a city (one point) or a country (several points).

    With several points the monthly values of all points are averaged first, then the trend test runs on
    that average, so the answer describes the area as a whole. Each point is also tested on its own,
    so the page can show how much the points agree.
    """
    params = [v["param"] for v in VARIABLES.values()]

    def work(pt):
        try:
            return fetch_many(pt[0], pt[1], params, start_year, end_year)
        except Exception as e:   # one failing point must not sink the others
            return e

    with ThreadPoolExecutor(max_workers=4) as ex:
        fetched = list(ex.map(work, points))
    ok = [(pt, d) for pt, d in zip(points, fetched) if isinstance(d, dict)]
    if not ok:
        errs = [str(d) for d in fetched if isinstance(d, Exception)]
        raise ValueError(errs[0] if errs else "No data came back for this place.")

    out = {}
    for label, info in VARIABLES.items():
        param = info["param"]
        series = [(pt, d[param]) for pt, d in ok if param in d]
        if not series:
            continue
        try:
            if len(series) == 1:
                base = series[0][1][["date", "value"]].copy()
            else:
                wide = pd.concat([s.set_index("date")["value"].rename(i) for i, (_, s) in enumerate(series)],
                                 axis=1, join="inner")
                base = pd.DataFrame({"date": wide.index, "value": wide.mean(axis=1).to_numpy()}).reset_index(drop=True)
            df = add_anomalies(base)
            stats = analyze_trend(df, method)
        except ValueError:
            continue
        per_point = []
        if len(series) > 1:
            for pt, s in series:
                try:
                    ps = analyze_trend(add_anomalies(s), method)
                except ValueError:
                    continue
                per_point.append({"lat": pt[0], "lon": pt[1], "rate": ps["change_per_decade"],
                                  "p_value": ps["p_value"], "significant": ps["is_significant"]})
        out[label] = {"df": df, "stats": stats, "points": per_point}
    if not out:
        raise ValueError("No variable had enough data to analyze for this place.")
    return {"vars": out, "n_points": len(points), "n_ok": len(ok), "points_ok": [pt for pt, _ in ok]}


def summarize_places(data: dict) -> pd.DataFrame:
    """One row per variable, strongest evidence first. Used for the table, the bar chart and the CSV."""
    rows = []
    for label, v in data["vars"].items():
        s, info, pts = v["stats"], VARIABLES[label], v["points"]
        up = sum(1 for p in pts if p["significant"] and p["rate"] > 0)
        down = sum(1 for p in pts if p["significant"] and p["rate"] < 0)
        rows.append({
            "Variable": label, "Unit": info["unit"],
            "Rate / decade": s["change_per_decade"], "95% CI low": s["ci_low_decade"], "95% CI high": s["ci_high_decade"],
            "Kendall tau": s["tau"], "p-value": s["p_value"], "Significant": s["is_significant"],
            "Direction": s["tendency"],
            "Points up": up if pts else None, "Points down": down if pts else None,
            "Points unclear": (len(pts) - up - down) if pts else None,
        })
    out = pd.DataFrame(rows)
    out["Holds up after multiple-test correction"] = (
        benjamini_hochberg(out["p-value"].to_numpy()) & out["Significant"].to_numpy())
    out["_abs_tau"] = out["Kendall tau"].abs()
    out = out.sort_values(["Significant", "_abs_tau"], ascending=[False, False]).drop(columns="_abs_tau")
    return out.reset_index(drop=True)
