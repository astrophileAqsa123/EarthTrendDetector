# data_fetcher.py
"""Fetch monthly point time series from the NASA POWER API (no key required)."""
import time

import numpy as np
import pandas as pd
import requests

POWER_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
FILL_VALUE = -999.0


class DataFetchError(RuntimeError):
    pass


def _request(params: dict) -> dict:
    last_err = "unknown error"
    for attempt in range(3):
        try:
            r = requests.get(
                POWER_URL, params=params, timeout=90,
                headers={"User-Agent": "earth-system-trend-detective/1.0"},
            )
        except requests.RequestException as e:
            last_err = str(e)
            time.sleep(2 * (attempt + 1))
            continue

        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504):  # transient -> retry
            last_err = f"HTTP {r.status_code}"
            time.sleep(2 * (attempt + 1))
            continue

        try:
            msg = "; ".join(r.json().get("messages", [])) or r.text[:200]
        except ValueError:
            msg = r.text[:200]
        raise DataFetchError(f"NASA POWER rejected the request (HTTP {r.status_code}): {msg}")

    raise DataFetchError(f"NASA POWER is not responding ({last_err}). Try again in a moment.")


def _series_to_df(series: dict) -> pd.DataFrame:
    """Turn one POWER parameter dict into a clean DataFrame[date, value, interpolated]
    containing only complete calendar years (Jan..Dec)."""
    rows = []
    for key, val in series.items():
        year, month = int(key[:4]), int(key[4:])
        if month == 13:  # POWER adds an annual-mean pseudo-month
            continue
        v = np.nan if val is None or float(val) <= FILL_VALUE + 1 else float(val)
        rows.append((pd.Timestamp(year, month, 1), v))

    df = pd.DataFrame(rows, columns=["date", "value"]).sort_values("date").reset_index(drop=True)
    if df.empty:
        raise DataFetchError("No data returned for this location/variable.")

    valid = df["value"].notna()
    if not valid.any():
        raise DataFetchError("This location/variable has no valid data (all values missing).")
    df = df.loc[valid.idxmax(): valid[::-1].idxmax()].reset_index(drop=True)

    counts = df.groupby(df["date"].dt.year)["date"].transform("count")
    df = df[counts == 12].reset_index(drop=True)
    if df.empty:
        raise DataFetchError("Fewer than one complete year of data is available.")

    df["interpolated"] = df["value"].isna()
    df["value"] = df["value"].interpolate(limit=6, limit_area="inside")
    if df["value"].isna().any():
        raise DataFetchError("Too many missing months in this series to analyze reliably.")
    return df


def _fetch_block(lat: float, lon: float, params: list, start_year: int, end_year: int) -> dict:
    data = _request({
        "parameters": ",".join(params),
        "community": "AG",
        "latitude": round(float(lat), 4),
        "longitude": round(float(lon), 4),
        "start": int(start_year),
        "end": int(end_year),
        "format": "JSON",
    })
    try:
        return data["properties"]["parameter"]
    except (KeyError, TypeError):
        raise DataFetchError("Unexpected response format from NASA POWER.")


def fetch_many(lat: float, lon: float, params: list, start_year: int, end_year: int) -> dict:
    """One API call for several parameters -> {param: DataFrame}.

    If POWER rejects the combined request (for example one parameter name is not offered
    for this community), fall back to requesting each parameter on its own so a single
    bad parameter cannot take the others down.
    """
    try:
        block = _fetch_block(lat, lon, params, start_year, end_year)
    except DataFetchError:
        if len(params) == 1:
            raise
        block = {}
        for p in params:
            try:
                block.update(_fetch_block(lat, lon, [p], start_year, end_year))
            except DataFetchError:
                continue
        if not block:
            raise

    out = {}
    for p in params:
        if p in block:
            try:
                out[p] = _series_to_df(block[p])
            except DataFetchError:
                pass  # skip a variable with no valid data; others may still work
    if not out:
        raise DataFetchError("No usable data returned for this location.")
    return out


def fetch_time_series(lat: float, lon: float, param: str,
                      start_year: int = 2000, end_year: int = 2025) -> pd.DataFrame:
    """Single-variable convenience wrapper."""
    result = fetch_many(lat, lon, [param], start_year, end_year)
    if param not in result:
        raise DataFetchError("No valid data for this location/variable.")
    return result[param]
