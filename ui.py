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


def _stripes(n: int = 64) -> str:
    """Decorative 'climate stripes' in the app's own rising/falling colours. Not tied to any data.
    They paint in left to right once when the landing page opens (see .stripes span in the CSS)."""
    rnd = random.Random(11)
    cells = []
    for i in range(n):
        v = -0.6 + 1.5 * (i / (n - 1)) ** 1.4 + rnd.uniform(-0.3, 0.3)
        cells.append(f'<span style="--i:{i};background:{_mix(v)}"></span>')
    return "".join(cells)


def hero(title: str, sub: str, eyebrow: str = "", chips: list | None = None):
    """Large banner for the landing page. eyebrow = small product-name label above the title,
    chips = short facts shown as pills under the text. (Built without blank lines on purpose:
    a blank line would end the HTML block and Markdown would render the rest as code.)"""
    eyebrow_html = f'<div class="hero-eyebrow">{eyebrow}</div>' if eyebrow else ""
    chips_html = ('<div class="hero-chips">' + "".join(f"<span>{c}</span>" for c in chips) + "</div>") if chips else ""
    st.markdown(
        '<div class="hero"><div class="hero-body">'
        f'{eyebrow_html}'
        f'<div class="hero-title" role="heading" aria-level="1">{title}</div>'
        f'<p class="hero-sub">{sub}</p>'
        f'{chips_html}'
        '</div>'
        f'<div class="stripes" aria-hidden="true">{_stripes()}</div></div>',
        unsafe_allow_html=True)


def section(title: str, sub: str = "", kicker: str = ""):
    """Section heading for the landing page: small label, big title, optional one-line intro."""
    k = f'<div class="kicker">{kicker}</div>' if kicker else ""
    s = f'<p class="section-sub">{sub}</p>' if sub else ""
    st.markdown(f'<div class="section-head">{k}<div class="section-title" role="heading" aria-level="2">{title}</div>{s}</div>',
                unsafe_allow_html=True)


def steps(items: list):
    """Numbered 'how it works' list. items = [(title, text), ...]."""
    html = "".join(f'<div class="step"><span class="step-n">{i}</span><div><b>{t}</b><p>{d}</p></div></div>'
                   for i, (t, d) in enumerate(items, 1))
    st.markdown(f'<div class="steps">{html}</div>', unsafe_allow_html=True)
def variable_groups(variables: dict, categories: list) -> str:
    """HTML list of every tracked variable, grouped by topic. Built from config so it never goes out of date."""
    blocks = []
    for cat in categories:
        items = "".join(f"<li>{v['plain_name'][:1].upper() + v['plain_name'][1:]}</li>"
                        for v in variables.values() if v["category"] == cat)
        blocks.append(f'<section class="group"><h4>{clean(cat)}</h4><ul>{items}</ul></section>')
    return f'<div class="groups">{"".join(blocks)}</div>'


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
.hero {{ background:var(--ink); color:#fff; border-radius:16px; overflow:hidden; margin-bottom:0; }}
.hero-body {{ padding:46px 48px 38px; }}
.hero-title {{ font-family:'Bricolage Grotesque', {FONT_STACK}; font-weight:700; font-size:3.5rem;
  line-height:1.02; letter-spacing:-0.03em; color:#fff; max-width:15ch; }}
.stApp .hero p.hero-sub {{ margin:1.1rem 0 0; max-width:58ch; color:#C3D1DD; font-size:1.1rem; line-height:1.55; }}
.stripes {{ display:flex; height:124px; }}
.stripes span {{ flex:1; transform-origin:bottom; animation:stripe-in .7s cubic-bezier(.2,.7,.2,1) both;
  animation-delay:calc(var(--i) * 14ms); }}
@keyframes stripe-in {{ from {{ transform:scaleY(0); }} to {{ transform:scaleY(1); }} }}
@media (prefers-reduced-motion: reduce) {{ .stripes span {{ animation:none; }} }}
.page-head {{ margin:.2rem 0 1.2rem; }}
.page-title {{ font-family:'Bricolage Grotesque', {FONT_STACK}; font-weight:700; font-size:2rem; letter-spacing:-0.02em; line-height:1.1; color:var(--ink); }}
.stApp .page-head p.page-desc {{ margin:.5rem 0 0; color:var(--muted); font-size:1rem; max-width:70ch; }}

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
[class*="st-key-casecard-"], .st-key-builder, .st-key-casefile {{ background:#fff; border:1px solid var(--line) !important;
  border-radius:12px; padding:18px 20px; }}
[class*="st-key-casecard-"] h4 {{ margin:0 0 .35rem; }}
[class*="st-key-casecard-"] p {{ margin-bottom:.4rem; }}
.st-key-casefile {{ border-left:5px solid var(--accent) !important; }}
[class*="st-key-casecard-"] {{ min-height:340px; }}

/* ---- landing page: finder panel that sits on the stripes */
.st-key-finder {{ position:relative; z-index:2; width:calc(100% - 56px); margin:-4.9rem 28px 0; background:#fff; border:1px solid var(--line);
  border-radius:14px; padding:20px 24px 22px; box-shadow:0 14px 34px rgba(16,36,58,.16); }}
.st-key-finder h4 {{ margin:0 0 .1rem; font-size:1.2rem; }}
.st-key-finder-note p {{ color:var(--muted); font-size:.93rem; margin:.2rem 0 0 28px; }}

/* ---- landing page: what is tracked, reliability strip, ways in */
.groups {{ display:grid; grid-template-columns:1fr 1fr; gap:22px 34px; }}
.group h4 {{ margin:0 0 .4rem; padding-top:10px; border-top:2px solid var(--ink); font-size:1.02rem; }}
.stApp .group ul {{ list-style:none; margin:0; padding:0; }}
.stApp .group li {{ padding:5px 0; margin:0; border-bottom:1px solid var(--line); font-size:.96rem; }}
.group li:last-child {{ border-bottom:0; }}
[class*="st-key-promise-"] {{ border-left:3px solid var(--line); padding:2px 0 2px 18px; }}
[class*="st-key-promise-"] p {{ margin-bottom:.25rem; }}
[class*="st-key-way-"] {{ border-top:1px solid var(--line); padding:12px 0 6px; }}
.st-key-way-last {{ border-bottom:1px solid var(--line); }}
[class*="st-key-way-"] h4 {{ margin:0; font-size:1.05rem; }}
[class*="st-key-way-"] p {{ margin:0; color:var(--muted); font-size:.95rem; }}

/* ---- city & country page */
.st-key-picker {{ background:#fff; border:1px solid var(--line); border-radius:12px; padding:16px 20px 12px; margin-bottom:.6rem; }}
[class*="st-key-vcard-"] {{ background:#fff; border:1px solid var(--line); border-top:4px solid var(--neutral);
  border-radius:12px; padding:14px 16px 10px; gap:.35rem; }}
[class*="st-key-vcard-up-"] {{ border-top-color:var(--up); }}
[class*="st-key-vcard-down-"] {{ border-top-color:var(--down); }}

.state-pill {{ display:inline-block; font-weight:600; font-size:.8rem; padding:2px 10px; border-radius:999px;
  background:#E4EAEF; color:var(--ink); margin-right:8px; }}
.state-up {{ background:#ECE6F5; color:#3F2670; }}
.state-down {{ background:#FDEBDD; color:#8F3B00; }}

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
/* ---- landing page v2: hero label + chips, section headings, tool cards, steps */
.hero-eyebrow {{ display:inline-block; font-size:.78rem; font-weight:600; letter-spacing:.12em; text-transform:uppercase;
  color:#9FC3D6; border:1px solid rgba(159,195,214,.38); border-radius:999px; padding:4px 12px; margin-bottom:1.1rem; }}
.hero-title {{ max-width:17ch; }}
.hero-chips {{ display:flex; flex-wrap:wrap; gap:8px 10px; margin-top:1.4rem; }}
.hero-chips span {{ font-size:.88rem; font-weight:500; color:#DCE6EE; background:rgba(255,255,255,.08);
  border:1px solid rgba(255,255,255,.16); border-radius:999px; padding:5px 14px; }}

.section-head {{ margin:2.4rem 0 1rem; }}
.kicker {{ font-size:.78rem; font-weight:600; letter-spacing:.12em; text-transform:uppercase; color:var(--accent); margin-bottom:.2rem; }}
.section-title {{ font-family:'Bricolage Grotesque', {FONT_STACK}; font-weight:700; font-size:1.75rem;
  letter-spacing:-0.02em; line-height:1.15; color:var(--ink); }}
.stApp .section-head p.section-sub {{ margin:.5rem 0 0; color:var(--muted); font-size:1rem; max-width:62ch; }}

[data-testid="stColumn"]:has([class*="st-key-tool-"]) > [data-testid="stVerticalBlock"] {{ height:100%; }}
[class*="st-key-tool-"] {{ background:#fff; border:1px solid var(--line); border-radius:14px; padding:20px 22px 18px;
  height:100%; min-height:236px; gap:.3rem; transition:border-color .15s, box-shadow .15s, transform .15s; }}
[class*="st-key-tool-"]:hover {{ border-color:var(--accent); box-shadow:0 10px 26px rgba(16,36,58,.10); transform:translateY(-2px); }}
/* Streamlit gives each markdown block a -1rem bottom offset that cancels the paragraph's 1rem margin,
   so keep margin-bottom at 1rem here (setting it to 0 makes the blocks collapse and overlap the button). */
[class*="st-key-tool-"] [data-testid="stMarkdownContainer"] h4 {{ margin:0 0 1rem; padding:0; font-size:1.2rem; }}
[class*="st-key-tool-"] [data-testid="stMarkdownContainer"] p {{ margin:0 0 1rem; color:var(--muted); font-size:.95rem; }}
.stApp [class*="st-key-tool-"] [data-testid="stMarkdownContainer"] p.tool-q {{ color:var(--accent); font-weight:600; font-size:.9rem; margin:0 0 1rem; }}
[class*="st-key-tool-"] button [data-testid="stMarkdownContainer"] p {{ margin:0; font-size:inherit; color:inherit; }}
[class*="st-key-tool-"] > * {{ flex-shrink:0; }}
.stElementContainer[class*="st-key-go_tool_"] {{ margin-top:auto; }}
@media (prefers-reduced-motion: reduce) {{ [class*="st-key-tool-"] {{ transition:none; }} [class*="st-key-tool-"]:hover {{ transform:none; }} }}

.steps {{ display:flex; flex-direction:column; gap:20px; }}
.step {{ display:flex; gap:16px; align-items:flex-start; }}
.step-n {{ flex:none; width:34px; height:34px; border-radius:50%; background:var(--ink); color:#fff; display:flex;
  align-items:center; justify-content:center; font-family:'Bricolage Grotesque', {FONT_STACK}; font-weight:700; }}
.step b {{ font-family:'Bricolage Grotesque', {FONT_STACK}; font-size:1.1rem; color:var(--ink); }}
.stApp .step p {{ margin:.15rem 0 0; color:var(--muted); font-size:.96rem; }}
.sample-tag {{ font-size:.75rem; font-weight:600; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin-bottom:.3rem; }}
/* ---- colour key */
.key {{ display:flex; flex-wrap:wrap; gap:6px 18px; font-size:.85rem; color:var(--muted); margin:.2rem 0 .6rem; }}
.key i {{ display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; }}

@media (max-width:640px) {{
  .hero-body {{ padding:26px 22px 22px; }}
  .hero-title {{ font-size:2.1rem; }}
  .stripes {{ height:80px; }}
  .st-key-finder {{ width:calc(100% - 16px); margin:-3.2rem 8px 0; padding:16px 16px 18px; }}
  .groups {{ grid-template-columns:1fr; }}
  .st-key-nav label {{ padding:7px 12px; }}
  .section-title {{ font-size:1.4rem; }}
  .hero-title {{ max-width:none; }}
  [class*="st-key-tool-"] {{ min-height:0; }}
}}
</style>
"""


def inject_css():
    register_chart_theme()
    st.markdown(_CSS, unsafe_allow_html=True)
