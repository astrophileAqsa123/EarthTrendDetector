"""One-off build script: creates data/cities.json and data/countries.json.

Needs (build time only, NOT needed to run the app):
    pip install geonamescache "geopandas==0.14.4" shapely

cities.json    {iso2: [[name, lat, lon, population], ...]}  top cities per country, biggest first
countries.json [{"name", "iso2", "points": [[lat, lon], ...], "note"}]  points are ordered so that
               the first k are always well spread over the country's main landmass.
"""
import json
import math
import warnings
from pathlib import Path

import geonamescache
import geopandas as gpd
from shapely.geometry import Point

warnings.filterwarnings("ignore")
OUT = Path(__file__).resolve().parent.parent / "data"
MAX_POINTS = 9
MAX_CITIES = 500
MIN_PART_SHARE = 0.10        # drop land parts smaller than 10% of the country's biggest part
EXCLUDE_BOXES = {            # (min_lat, max_lat, min_lon, max_lon): overseas pieces that the rule above keeps
    "FRA": [(-10, 10, -60, -45)],                              # French Guiana
    "USA": [(50, 75, -180, -125), (15, 25, -165, -150)],       # Alaska, Hawaii
}
NAME_FIX = {"Kosovo": "XKX", "France": "FRA", "Norway": "NOR"}

gc = geonamescache.GeonamesCache()
countries = gc.get_countries()                     # iso2 -> info
iso3_to_iso2 = {c["iso3"]: iso for iso, c in countries.items()}

# ---------------------------------------------------------------- cities
cities = {}
for c in gc.get_cities().values():
    cities.setdefault(c["countrycode"], []).append(
        [c["name"], round(c["latitude"], 3), round(c["longitude"], 3), int(c["population"])])
for iso, rows in cities.items():
    rows.sort(key=lambda r: -r[3])
    cities[iso] = rows[:MAX_CITIES]


# ---------------------------------------------------------------- countries
def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def spread(cands, k, start):
    """Farthest-point ordering: each new point is as far as possible from those already chosen."""
    chosen = [min(cands, key=lambda p: hav(p, start))]
    while len(chosen) < min(k, len(cands)):
        chosen.append(max((p for p in cands if p not in chosen), key=lambda p: min(hav(p, q) for q in chosen)))
    return chosen


world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
world = world[world["name"] != "Antarctica"]
world_m = world.to_crs(6933)
polys = {}
for (_, row), (_, row_m) in zip(world.iterrows(), world_m.iterrows()):
    iso3 = NAME_FIX.get(row["name"], row["iso_a3"])
    iso2 = iso3_to_iso2.get(iso3)
    if not iso2:
        continue
    parts = list(row.geometry.geoms) if row.geometry.geom_type == "MultiPolygon" else [row.geometry]
    parts_m = list(row_m.geometry.geoms) if row_m.geometry.geom_type == "MultiPolygon" else [row_m.geometry]
    big = max(p.area for p in parts_m)
    keep = [p for p, pm in zip(parts, parts_m) if pm.area >= MIN_PART_SHARE * big]
    polys[iso2] = (iso3, keep)

out = []
for iso2, info in countries.items():
    name = info["name"]
    top = cities.get(iso2, [])
    pts, note = [], ""
    if iso2 in polys:
        iso3, parts = polys[iso2]
        boxes = EXCLUDE_BOXES.get(iso3, [])
        keep = [p for p in parts if not any(b[0] <= p.representative_point().y <= b[1]
                                            and b[2] <= p.representative_point().x <= b[3] for b in boxes)]
        minx = min(p.bounds[0] for p in keep); miny = min(p.bounds[1] for p in keep)
        maxx = max(p.bounds[2] for p in keep); maxy = max(p.bounds[3] for p in keep)
        cands = []
        for step in (1.0, 0.5):          # MERRA-2 cells are ~0.5 deg, so 1 deg spacing avoids duplicate cells
            y = math.floor(miny)
            while y <= maxy:
                x = math.floor(minx)
                while x <= maxx:
                    if any(p.contains(Point(x, y)) for p in keep):
                        cands.append([round(y, 3), round(x, 3)])
                    x += step
                y += step
            if len(cands) >= 3:
                break
            cands = []
        cen = max(keep, key=lambda p: p.area).representative_point()
        if cands:
            pts = spread(cands, MAX_POINTS, (cen.y, cen.x))
        else:
            pts = [[round(cen.y, 3), round(cen.x, 3)]]
        note = "main landmass"
    elif top:
        for r in top:                       # largest cities, but never two in the same ~1 degree cell
            if all(abs(r[1] - q[0]) > 0.8 or abs(r[2] - q[1]) > 0.8 for q in pts):
                pts.append([r[1], r[2]])
            if len(pts) == 3:
                break
        note = "largest cities"
    if not pts:
        continue
    out.append({"name": name, "iso2": iso2, "points": pts, "note": note})

out.sort(key=lambda c: c["name"])
OUT.mkdir(exist_ok=True)
(OUT / "cities.json").write_text(json.dumps(cities, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
(OUT / "countries.json").write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
print(len(out), "countries;", sum(len(v) for v in cities.values()), "cities")
