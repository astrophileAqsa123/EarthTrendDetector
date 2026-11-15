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
