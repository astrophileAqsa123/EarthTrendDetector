# places.py
"""Countries, cities and sample points for the "City & country" page.

Data files (built once by tools/build_place_data.py, no internet needed at run time):
  data/cities.json     {iso2: [[name, lat, lon, population], ...]}  biggest cities first
  data/countries.json  [{"name", "iso2", "points": [[lat, lon], ...], "note"}]
"""
import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
DEFAULT_COUNTRY = "Pakistan"
DEFAULT_CITY = "Islamabad"


@lru_cache(maxsize=1)
def _countries() -> dict:
    rows = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
    return {r["name"]: r for r in rows}


@lru_cache(maxsize=1)
def _cities() -> dict:
    return json.loads((DATA / "cities.json").read_text(encoding="utf-8"))


def country_names() -> list:
    return list(_countries())


def country(name: str) -> dict:
    return _countries()[name]


def country_points(name: str, k: int) -> list:
    """The first k sample points of a country. They are ordered so any prefix is well spread out."""
    pts = _countries()[name]["points"]
    return [tuple(p) for p in pts[:max(1, k)]]


def cities_of(country_name: str) -> dict:
    """{label: {"name", "lat", "lon", "pop"}} biggest first. Duplicate names get their coordinates added."""
    rows = _cities().get(_countries()[country_name]["iso2"], [])
    counts = {}
    for r in rows:
        counts[r[0]] = counts.get(r[0], 0) + 1
    out = {}
    for name, lat, lon, pop in rows:
        label = name if counts[name] == 1 else f"{name} ({lat:.1f}°, {lon:.1f}°)"
        out[label] = {"name": name, "lat": lat, "lon": lon, "pop": pop}
    return out


def default_city(country_name: str) -> str:
    labels = list(cities_of(country_name))
    if country_name == DEFAULT_COUNTRY and DEFAULT_CITY in labels:
        return DEFAULT_CITY
    return labels[0] if labels else ""


def fmt_pop(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} million people"
    return f"{round(n, -3):,} people" if n >= 10_000 else f"{n:,} people"
