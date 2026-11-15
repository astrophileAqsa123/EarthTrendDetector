# ui.py
"""Visual layer for the Earth System Trend Detective: theme CSS, hero banner, result cards, chart template.

Nothing in here does any statistics. app.py calls these helpers so all styling lives in one place.
"""
import random
import re

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---------------------------------------------------------------- design tokens
INK = "#10243A"        # deep sea navy: text and hero
MIST = "#F3F6F8"       # page background
LINE = "#D8E0E7"       # hairlines and borders
MUTED = "#5A6B7B"      # secondary text
ACCENT = "#17607D"     # interface accent (buttons, links, focus)
UP = "#5E3C99"         # significant increase  (colour-blind-safe pair)
DOWN = "#E66101"       # significant decrease
NEUTRAL = "#8A96A3"    # no clear change

FONT_STACK = "'Instrument Sans', 'Segoe UI', system-ui, -apple-system, Roboto, Arial, sans-serif"

# ---------------------------------------------------------------- text helpers
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2139\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200d]+\\s?")


def clean(text: str) -> str:
    """Remove emoji from display text (the data catalog keeps them; the interface doesn't show them)."""
    return _EMOJI.sub("", text).strip()


# ---------------------------------------------------------------- chart template
def register_chart_theme():
    pio.templates["trend"] = go.layout.Template(layout=dict(
        font=dict(family=FONT_STACK, size=13, color=INK),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=[ACCENT, UP, DOWN, NEUTRAL],
        xaxis=dict(gridcolor="#E6ECF0", linecolor=LINE, zeroline=False, ticks="outside", tickcolor=LINE, automargin=True,
                   title_font=dict(size=12, color=MUTED)),
        yaxis=dict(gridcolor="#E6ECF0", linecolor=LINE, zeroline=False, automargin=True,
                   title_font=dict(size=12, color=MUTED)),
        legend=dict(font=dict(size=12, color=MUTED), bgcolor="rgba(0,0,0,0)"),
        bargap=0.3,
        hoverlabel=dict(bgcolor=INK, font=dict(color="white", family=FONT_STACK, size=12), bordercolor=INK),
    ))
    pio.templates.default = "trend"


# ---------------------------------------------------------------- hero
_STOPS = [(-1.0, "#C2510A"), (-0.5, "#F1A340"), (0.0, "#F4F0EC"), (0.5, "#B2ABD2"), (1.0, "#5E3C99")]


def _mix(v: float) -> str:
    v = max(-1.0, min(1.0, v))
    for (a, ca), (b, cb) in zip(_STOPS, _STOPS[1:]):
        if a <= v <= b:
            t = (v - a) / (b - a)
            ra, rb = [int(ca[i:i + 2], 16) for i in (1, 3, 5)], [int(cb[i:i + 2], 16) for i in (1, 3, 5)]
            return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ra, rb))
    return _STOPS[-1][1]


def _stripes(n: int = 72) -> str:
    """Decorative 'climate stripes' in the app's own rising/falling colours. Not tied to any data."""
    rnd = random.Random(11)
    cells = []
    for i in range(n):
        v = -0.6 + 1.5 * (i / (n - 1)) ** 1.4 + rnd.uniform(-0.3, 0.3)
        cells.append(f'<span style="background:{_mix(v)}"></span>')
    return "".join(cells)


def hero(title: str, sub: str):
    """Large banner for the landing page."""
    st.markdown(
        f"""
<div class="hero">
  <div class="hero-body">
    <div class="hero-title" role="heading" aria-level="1">{title}</div>
    <p class="hero-sub">{sub}</p>
  </div>
  <div class="stripes" aria-hidden="true">{_stripes()}</div>
</div>
""", unsafe_allow_html=True)


def page_header(title: str, desc: str):
    """Compact title block for every other page."""
    st.markdown(f'<div class="page-head"><div class="page-title" role="heading" aria-level="1">{title}</div>'
                f'<p class="page-desc">{desc}</p></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- result cards
def verdict(pin: str, state: str, headline_md: str, conf_short: str, conf_sentence: str):
    """Headline answer card. state: 'up' | 'down' | 'none' decides the colour of the left edge."""
    with st.container(key=f"verdict-{state}-{pin}"):
        st.markdown(clean(headline_md))
        st.markdown(f'<div class="conf-line"><span class="conf-pill">{conf_short}</span><span class="conf-text">{conf_sentence}</span></div>',
                    unsafe_allow_html=True)


def legend_key():
    st.markdown(
        f'<div class="key"><span><i style="background:{UP}"></i>Significant increase</span>'
        f'<span><i style="background:{DOWN}"></i>Significant decrease</span>'
        f'<span><i style="background:{NEUTRAL}"></i>No clear change</span></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- CSS
_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Instrument+Sans:wght@400;500;600&display=swap');

:root {{
  --ink:{INK}; --mist:{MIST}; --line:{LINE}; --muted:{MUTED}; --accent:{ACCENT};
  --up:{UP}; --down:{DOWN}; --neutral:{NEUTRAL};
}}

html, body, .stApp, [data-testid="stAppViewContainer"], .stApp button, .stApp input, .stApp textarea, .stApp select {{
  font-family:{FONT_STACK};
}}
.stApp {{ background:var(--mist); color:var(--ink); }}
[data-testid="stHeader"] {{ background:rgba(243,246,248,.94); border-bottom:1px solid var(--line); backdrop-filter:blur(6px); }}
.stAppDeployButton, #MainMenu, footer {{ display:none !important; }}
.block-container {{ max-width:1180px; padding-top:5.2rem; padding-bottom:3rem; }}

/* ---- type scale */
.stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
  font-family:'Bricolage Grotesque', {FONT_STACK}; color:var(--ink); letter-spacing:-0.01em; font-weight:700;
}}
.stApp h3 {{ font-size:1.45rem; margin-top:.4rem; }}
.stApp h4 {{ font-size:1.12rem; }}
.stApp [data-testid="stSubheader"], .stApp h2 {{ font-size:1.25rem; }}
.stApp p, .stApp li, .stApp label {{ line-height:1.55; }}
[data-testid="stCaptionContainer"] {{ color:var(--muted); opacity:1; }}
[data-testid="stColumn"]:has([class*="st-key-casecard-"]) > [data-testid="stVerticalBlock"] {{ height:100%; }}
[class*="st-key-casecard-"] {{ height:100%; }}
.stMarkdown p {{ max-width:75ch; }}

/* ---- hero */
.hero {{ background:var(--ink); color:#fff; border-radius:14px; overflow:hidden; margin-bottom:1.1rem; }}
.hero-body {{ padding:30px 34px 24px; }}
.hero-title {{ font-family:'Bricolage Grotesque', {FONT_STACK}; font-weight:700; font-size:2.5rem;
  line-height:1.05; letter-spacing:-0.025em; color:#fff; }}
.stApp .hero p.hero-sub {{ margin:.85rem 0 0; max-width:62ch; color:#C3D1DD; font-size:1.02rem; line-height:1.5; }}
.stripes {{ display:flex; height:30px; }}
.page-head {{ margin:.2rem 0 1.2rem; }}
.page-title {{ font-family:'Bricolage Grotesque', {FONT_STACK}; font-weight:700; font-size:2rem; letter-spacing:-0.02em; line-height:1.1; color:var(--ink); }}
.stApp .page-head p.page-desc {{ margin:.5rem 0 0; color:var(--muted); font-size:1rem; max-width:70ch; }}
.stripes span {{ flex:1; }}

/* ---- sidebar */
[data-testid="stSidebar"] {{ background:#fff; border-right:1px solid var(--line); }}
[data-testid="stSidebar"] h2 {{ font-size:1.02rem; margin:1.1rem 0 .3rem; padding-top:.9rem; border-top:1px solid var(--line); }}
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] + div h2:first-of-type {{ border-top:0; }}

/* ---- inputs */
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="base-input"] {{ border-radius:8px; }}
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
  border-radius:8px; font-weight:600; border:1px solid var(--line); background:#fff; color:var(--ink); transition:border-color .15s, background .15s;
}}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color:var(--accent); color:var(--accent); background:#fff; }}
.stButton > button[kind="primary"] {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
.stButton > button[kind="primary"]:hover {{ background:#0F4E67; border-color:#0F4E67; color:#fff; }}
.stApp :focus-visible {{ outline:2px solid var(--accent) !important; outline-offset:2px; }}

/* ---- metric cards */
[data-testid="stMetric"] {{ background:#fff; border:1px solid var(--line); border-radius:10px; padding:14px 16px; min-height:104px; height:100%; }}
[data-testid="stMetricLabel"] p {{ color:var(--muted); font-size:.85rem; font-weight:500; }}
[data-testid="stMetricValue"] {{ font-family:'Bricolage Grotesque', {FONT_STACK}; font-weight:700; font-size:1.2rem; letter-spacing:-0.01em; }}
[data-testid="stMetricValue"] *, [data-testid="stMetricLabel"] * {{ white-space:normal !important; overflow:visible !important; text-overflow:clip !important; }}

/* ---- verdict card */
[class*="st-key-verdict-"] {{ background:#fff; border:1px solid var(--line); border-left:5px solid var(--neutral);
  border-radius:10px; padding:16px 20px 18px; margin:.2rem 0 .8rem; gap:.5rem; }}
[class*="st-key-verdict-up-"] {{ border-left-color:var(--up); }}
[class*="st-key-verdict-down-"] {{ border-left-color:var(--down); }}
[class*="st-key-verdict-"] p {{ margin-bottom:0; }}
.conf-line {{ margin-top:6px; }}
.conf-pill {{ display:inline-block; font-weight:600; font-size:.82rem; padding:2px 10px; border-radius:999px;
  background:#E4EAEF; color:var(--ink); margin-right:10px; }}
.conf-text {{ color:var(--muted); font-size:.93rem; }}

/* ---- cards (story + builder) */
[class*="st-key-choice-"], [class*="st-key-step-"], [class*="st-key-casecard-"], .st-key-builder, .st-key-casefile {{ background:#fff; border:1px solid var(--line) !important;
  border-radius:12px; padding:18px 20px; }}
[class*="st-key-casecard-"] h4 {{ margin:0 0 .35rem; }}
[class*="st-key-casecard-"] p {{ margin-bottom:.4rem; }}
.st-key-casefile {{ border-left:5px solid var(--accent) !important; }}
[class*="st-key-choice-"] {{ padding:24px 26px; border-top:4px solid var(--accent) !important; }}
[class*="st-key-choice-"] h4 {{ font-size:1.35rem; margin-bottom:.4rem; }}
[class*="st-key-step-"] {{ background:transparent; border:0 !important; border-left:3px solid var(--line) !important; border-radius:0; padding:2px 0 2px 16px; }}
[class*="st-key-step-"] p {{ margin-bottom:.2rem; }}
[data-testid="stColumn"]:has([class*="st-key-choice-"]) > [data-testid="stVerticalBlock"] {{ height:100%; }}
[class*="st-key-choice-"] {{ min-height:250px; }}
[class*="st-key-casecard-"] {{ min-height:340px; }}

/* ---- tabs */
.stTabs [data-baseweb="tab-list"] {{ gap:6px; border-bottom:1px solid var(--line); }}
.stTabs [data-baseweb="tab"] {{ padding:8px 12px; }}
.stTabs [data-baseweb="tab"] p {{ font-weight:600; color:var(--muted); }}
.stTabs [aria-selected="true"] p {{ color:var(--ink); }}
.stTabs [data-baseweb="tab-highlight"] {{ background:var(--accent); height:3px; }}

/* ---- alerts, expanders, tables */
[data-testid="stAlertContainer"] {{ background:#fff !important; color:var(--ink); border:1px solid var(--line); border-left:4px solid var(--accent);
  border-radius:10px; }}
[data-testid="stAlertContainer"] p, [data-testid="stAlertContainer"] li {{ color:var(--ink); }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {{ border-left-color:#A16207; background:#FFFBF2 !important; }}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {{ border-left-color:#B42318; background:#FFF6F5 !important; }}
[data-testid="stExpander"] {{ background:#fff; border:1px solid var(--line); border-radius:10px; }}
[data-testid="stExpander"] summary p {{ font-weight:600; }}
[data-testid="stDataFrame"] {{ border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
hr {{ border-color:var(--line); margin:1.4rem 0; }}

/* ---- colour key */
.key {{ display:flex; flex-wrap:wrap; gap:6px 18px; font-size:.85rem; color:var(--muted); margin:.2rem 0 .6rem; }}
.key i {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; }}

@media (max-width:640px) {{
  .hero-body {{ padding:22px 20px 18px; }}
  .hero-title {{ font-size:1.8rem; }}
  .stripes {{ height:22px; }}
  .st-key-nav label {{ padding:7px 12px; }}
}}
</style>
"""


def inject_css():
    register_chart_theme()
    st.markdown(_CSS, unsafe_allow_html=True)
