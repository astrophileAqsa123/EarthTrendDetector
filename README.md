# 🌍 Earth System Trend Detective

Find **what** is changing, **where**, **how much**, and **whether it is statistically real**, using NASA data.

## Run
```bash
pip install -r requirements.txt
export GROQ_API_KEY=gsk_...        # or put it in a .env file (see .env.example)
streamlit run app.py
```
The app works without a Groq key. AI features fall back to built-in text and keyword matching.

## What's new
| Feature | Where |
|---|---|
| 12 variables with plain-language definitions | `config.py` |
| Guided **Start here**: 6 story cases, free-text question → variable suggestions, build-your-own | `app.py` (Start view) |
| **Beginner / Expert** display mode | sidebar |
| **Time to significance**: how many more years until an unclear trend becomes significant | `stats_engine.time_to_significance` |
| **Start-year robustness heatmap** (anti cherry-picking) | `stats_engine.window_sensitivity`, "Is it solid?" tab |
| **AI explanation** (Groq), 3 reading levels, single place or comparison | `ai_helper.py` |
| Multiple-test correction (Benjamini-Hochberg) in scanner and map | `stats_engine.benjamini_hochberg` |
| Colour-blind-safe palette (purple up, orange down) | `app.py` |
| **City & country trends**: every variable for any city or a whole country (average of up to 9 sample points) | `views/places.py`, `places.py`, `scanner.analyze_points` |
| Redesigned landing page with a place finder | `views/home.py`, `ui.py` |

## How the AI is kept honest
The AI never calculates. It receives only numbers already computed by `stats_engine.py`, is told to use
no other numbers, to call non-significant results "no real trend", and to phrase causes only as possibilities.

## Pages
| Page | File | For |
|---|---|---|
| Home (landing) | `views/home.py` | Where to start |
| Cases | `views/cases.py` | Six ready-made questions |
| Build your own | `views/build.py` | Guided form + question box |
| City & country | `views/places.py` | All variables for a city or a whole country |
| Results | `views/results.py` | Trend at one or two places |
| Trend scanner | `views/scanner.py` | Every variable at once |
| Regional map | `views/regional_map.py` | Trend test over a grid |
| How it works | `views/how_it_works.py` | Method and limits |

## Files
`app.py` entry point + navigation · `core.py` shared state and result blocks · `ui.py` theme and design · `.streamlit/config.toml` colours · `stats_engine.py` statistics · `scanner.py` variable ranking and regional grid ·
`data_fetcher.py` NASA POWER client · `ai_helper.py` Groq · `plain.py` plain-language text · `config.py` catalog and stories


## Place data
`data/cities.json` and `data/countries.json` are prebuilt (no internet needed). To rebuild: `pip install geonamescache "geopandas==0.14.4" shapely` then `python tools/build_place_data.py`.
