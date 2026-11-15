# stats_engine.py
import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy.stats import kendalltau, norm, t as t_dist, theilslopes

METHODS = {
    "Seasonal Mann-Kendall (default)": "seasonal",
    "Hamed-Rao (autocorrelation-corrected)": "hamed_rao",
}


def add_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'anomaly' = value minus that calendar month's long-term mean (removes seasonal cycle)."""
    out = df.copy()
    out["anomaly"] = out["value"] - out.groupby(out["date"].dt.month)["value"].transform("mean")
    return out


def annual_anomalies(df: pd.DataFrame) -> pd.Series:
    if "anomaly" not in df:
        df = add_anomalies(df)
    return df.groupby(df["date"].dt.year)["anomaly"].mean()


def pettitt(values: np.ndarray, years: np.ndarray):
    """Pettitt change-point test. Returns (first year of the 'new regime', approx p-value)."""
    n = len(values)
    if n < 8:
        return None, 1.0
    # U_t = sum_{i<=t} sum_{j>t} sign(x_i - x_j)
    sgn = np.sign(values[:, None] - values[None, :])
    u = np.array([sgn[: t + 1, t + 1:].sum() for t in range(n - 1)])
    k = np.abs(u).max()
    p = float(min(1.0, 2.0 * np.exp(-6.0 * k**2 / (n**3 + n**2))))
    return int(years[int(np.abs(u).argmax()) + 1]), p


# ------------------------------------------------------------------ time to significance
def time_to_significance(annual_vals, years, alpha: float = 0.05, power: float = 0.8,
                         max_extra: int = 100):
    """How many MORE years of data would a not-yet-significant trend need to become significant?

    Assumes the current trend rate and year-to-year noise stay the same. Uses a linear
    regression on annual-mean anomalies, with the noise inflated for lag-1 autocorrelation.

      extra_50 : extra years until the trend is *expected* to cross the significance line
                 (roughly a 50% chance of a significant result)
      extra_80 : extra years for an ~80% chance of a significant result
    A value of None means "not within max_extra years".
    """
    y = np.asarray(annual_vals, dtype=float)
    x = np.asarray(years, dtype=float)
    n = len(y)
    if n < 8:
        return None
    b, a = np.polyfit(x, y, 1)
    resid = y - (a + b * x)
    sigma = max(float(resid.std(ddof=2)), 1e-12)
    r1 = float(np.corrcoef(resid[:-1], resid[1:])[0, 1])
    r1 = float(np.clip(r1 if np.isfinite(r1) else 0.0, 0.0, 0.8))
    inflate = np.sqrt((1 + r1) / (1 - r1))
    z_pow = norm.ppf(power)

    extra_50 = extra_80 = None
    for extra in range(1, max_extra + 1):
        m = n + extra
        sxx = m * (m**2 - 1) / 12.0                       # sum of squared year offsets
        snr = abs(b) / (sigma * inflate / np.sqrt(sxx))   # expected |t| statistic
        t_crit = t_dist.ppf(1 - alpha / 2, m - 2)
        if extra_50 is None and snr >= t_crit:
            extra_50 = extra
        if snr >= t_crit + z_pow:
            extra_80 = extra
            break
    last_year = int(x[-1])
    return {
        "extra_50": extra_50,
        "extra_80": extra_80,
        "year_50": last_year + extra_50 if extra_50 else None,
        "year_80": last_year + extra_80 if extra_80 else None,
        "max_extra": max_extra,
        "autocorr": r1,
        "slope_per_decade": float(b * 10),
    }


# ------------------------------------------------------------------ start-year sensitivity
def window_sensitivity(df: pd.DataFrame, alpha: float = 0.05, min_years: int = 10) -> pd.DataFrame:
    """Trend (Theil-Sen slope + Kendall tau test) for EVERY start/end-year window of at least
    `min_years`, using annual-mean anomalies. Shows whether a result depends on the years chosen."""
    annual = annual_anomalies(df)
    yrs = annual.index.to_numpy(dtype=float)
    vals = annual.to_numpy(dtype=float)
    n = len(vals)
    rows = []
    for i in range(n):
        for j in range(i + min_years - 1, n):
            xs, seg = yrs[i:j + 1], vals[i:j + 1]
            tau, p = kendalltau(xs, seg)
            slope = theilslopes(seg, xs)[0]
            rows.append({"start": int(xs[0]), "end": int(xs[-1]),
                         "slope_per_decade": float(slope) * 10.0,
                         "p_value": float(p) if np.isfinite(p) else 1.0,
                         "significant": bool(np.isfinite(p) and p < alpha)})
    return pd.DataFrame(rows)


def robustness_summary(sens: pd.DataFrame, full_slope: float) -> dict:
    """Condense the window grid into a plain-language verdict."""
    if sens is None or sens.empty:
        return {"n_windows": 0, "same_sign_share": None, "significant_share": None,
                "verdict": "unknown", "label": "Not enough years to test"}
    sign = np.sign(full_slope) if full_slope != 0 else 1.0
    same = np.sign(sens["slope_per_decade"]) == sign
    same_share = float(same.mean())
    sig_share = float((same & sens["significant"]).mean())
    if same_share >= 0.9 and sig_share >= 0.5:
        verdict, label = "robust", "Solid: the same story shows up for most choices of years"
    elif same_share >= 0.75:
        verdict, label = "fairly_consistent", "Fairly consistent direction, but strength varies with the years chosen"
    else:
        verdict, label = "fragile", "Fragile: the answer changes depending on which years you pick"
    return {"n_windows": int(len(sens)), "same_sign_share": same_share,
            "significant_share": sig_share, "verdict": verdict, "label": label}


# ------------------------------------------------------------------ many-tests correction
def benjamini_hochberg(pvals, alpha: float = 0.05) -> np.ndarray:
    """Benjamini-Hochberg false-discovery-rate control. Returns a boolean array: still
    significant after allowing for the fact that many tests were run at once."""
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    if n == 0:
        return np.array([], dtype=bool)
    order = np.argsort(p)
    passed = p[order] <= alpha * (np.arange(1, n + 1) / n)
    keep = np.zeros(n, dtype=bool)
    if passed.any():
        cutoff = np.max(np.where(passed)[0])
        keep[order[: cutoff + 1]] = True
    return keep


# ------------------------------------------------------------------ field significance
def field_significant(pvals, alpha_global: float = 0.05) -> bool:
    """Field (global) significance of a map of local tests, after Wilks (2016): the field as a
    whole is significant if Benjamini-Hochberg run at alpha_FDR = 2 * alpha_global rejects at
    least one local test. Guards against 'a few dots lit up by chance' being read as a regional signal."""
    p = np.asarray(pvals, dtype=float)
    if len(p) == 0:
        return False
    return bool(benjamini_hochberg(p, alpha=min(2.0 * alpha_global, 1.0)).any())


# ------------------------------------------------------------------ percent of mean
def pct_of_mean_per_decade(rate_per_decade: float, values, anomalies, min_mean_to_noise: float = 2.0):
    """Rate as a percentage of the long-term mean, or None when that number would be unstable.

    Suppressed when the mean is within `min_mean_to_noise` noise-SDs of zero (e.g. desert rainfall,
    where a tiny mean turns a small trend into '+400 %/decade'). The noise SD is that of the
    deseasonalised monthly anomalies, so the guard is unit-free."""
    v = np.asarray(values, dtype=float)
    a = np.asarray(anomalies, dtype=float)
    mean = float(np.mean(v))
    noise = float(np.std(a))
    if not np.isfinite(mean) or mean <= 0 or noise <= 0 or mean < min_mean_to_noise * noise:
        return None
    return 100.0 * rate_per_decade / mean


# ------------------------------------------------------------------ main trend test
def analyze_trend(df: pd.DataFrame, method: str = "seasonal", alpha: float = 0.05) -> dict:
    """Mann-Kendall significance + Sen's slope on a monthly series.

    method="seasonal":  Seasonal Mann-Kendall on raw values (slope is per YEAR).
    method="hamed_rao": Hamed-Rao modified MK on deseasonalized anomalies, which
                        corrects the p-value for autocorrelation (slope is per MONTH).
    """
    n_months = len(df)
    if n_months < 60:
        raise ValueError("Need at least 5 complete years (60 months) for a reliable trend test.")

    df = add_anomalies(df)
    values = df["value"].to_numpy(dtype=float)
    anomalies = df["anomaly"].to_numpy(dtype=float)

    if method == "seasonal":
        result = mk.seasonal_test(values, period=12, alpha=alpha)
        change_per_year = float(result.slope)            # slope is per 12-month period
    elif method == "hamed_rao":
        result = mk.hamed_rao_modification_test(anomalies, alpha=alpha)
        change_per_year = float(result.slope) * 12.0     # slope is per monthly step
    else:
        raise ValueError(f"Unknown method: {method}")

    total_years = n_months / 12.0
    monthly_slope = change_per_year / 12.0
    x = np.arange(n_months)
    intercept = float(np.median(anomalies - monthly_slope * x))   # Sen's intercept
    trend_line = intercept + monthly_slope * x

    # 95% confidence interval of the rate (Theil-Sen on annual-mean anomalies)
    annual = df.groupby(df["date"].dt.year)["anomaly"].mean()
    ts = theilslopes(annual.to_numpy(), annual.index.to_numpy(dtype=float), 1 - alpha)
    ci_low_decade, ci_high_decade = float(ts[2]) * 10.0, float(ts[3]) * 10.0
    annual_sen_decade = float(ts[0]) * 10.0
    # The headline rate (seasonal / Hamed-Rao Sen slope, monthly data) and the CI (Theil-Sen on annual
    # means) are different estimators. Report the annual-mean slope next to the CI and flag any mismatch.
    headline_decade = change_per_year * 10.0
    ci_consistent = bool(ci_low_decade <= headline_decade <= ci_high_decade)

    # Abrupt-shift check on the DETRENDED series, so a steady trend isn't mistaken for a jump
    yrs = annual.index.to_numpy(dtype=float)
    cp_year, cp_p = pettitt(annual.to_numpy() - float(ts[0]) * (yrs - yrs[0]), annual.index.to_numpy())

    p = float(result.p)
    is_significant = bool(p < alpha)
    tendency = "increasing" if change_per_year > 0 else "decreasing" if change_per_year < 0 else "flat"

    tts = None if is_significant else time_to_significance(annual.to_numpy(), yrs, alpha)

    return {
        "direction": result.trend if is_significant else "no trend",  # test verdict
        "tendency": tendency,                                         # sign of Sen's slope
        "p_value": p,
        "tau": float(result.Tau),
        "is_significant": is_significant,
        "confidence_label": (f"Statistically Significant (p < {alpha})" if is_significant
                             else "Not Significant (within natural variability)"),
        "change_per_decade": change_per_year * 10.0,
        "total_change": change_per_year * total_years,
        "years_analyzed": round(total_years, 1),
        "ci_low_decade": ci_low_decade,
        "ci_high_decade": ci_high_decade,
        "annual_sen_per_decade": annual_sen_decade,   # the slope the CI is actually centred on
        "ci_consistent": ci_consistent,              # headline rate lies inside the CI
        "pct_of_mean_per_decade": pct_of_mean_per_decade(headline_decade, values, anomalies),
        "change_point_year": cp_year,       # year the series shifts (Pettitt test)
        "change_point_p": cp_p,
        "time_to_significance": tts,        # None when already significant
        "method": method,
        "anomalies": anomalies,
        "trend_line": trend_line,
    }


if __name__ == "__main__":
    # Offline self-test: known trend of 0.01 per month = 0.12 per year = 1.2 per decade
    rng = np.random.default_rng(0)
    dates = pd.date_range("2000-01-01", periods=300, freq="MS")
    seasonal = np.tile(10 * np.sin(np.linspace(0, 2 * np.pi, 12, endpoint=False)), 25)
    demo = pd.DataFrame({"date": dates, "value": 0.01 * np.arange(300) + seasonal + rng.normal(0, 0.5, 300)})
    for m in METHODS.values():
        s = analyze_trend(demo, m)
        print(f"{m:10s} -> {s['change_per_decade']:+.3f} per decade (expect ~ +1.2), p={s['p_value']:.4g}, {s['direction']}")
