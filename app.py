"""
Customer Insight Synthesizer — Streamlit app.
Single-page, five sections, no API calls required.
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Customer Insight Synthesizer — Lidl Plus vs. REWE",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global styles ─────────────────────────────────────────────────────────────
st.markdown('<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;700&family=IBM+Plex+Mono:wght@100;300;700&display=swap" rel="stylesheet">', unsafe_allow_html=True)

st.markdown("""
<style>
/* ── Color tokens — light mode ── */
:root {
  --bg:           #F8FAFC;
  --surface:      #FFFFFF;
  --subtle:       #F1F5F9;
  --border:       #E2E8F0;
  --bdr-mid:      #CBD5E1;
  --t1:           #0F172A;
  --t2:           #1E293B;
  --t3:           #334155;
  --t4:           #475569;
  --t5:           #64748B;
  --t6:           #94A3B8;
  --t7:           #CBD5E1;
  /* Severity */
  --sev-crit-bg:  #FEF2F2; --sev-crit-bdr: #FECACA; --sev-crit-txt: #DC2626;
  --sev-ser-bg:   #FFFBEB; --sev-ser-bdr:  #FDE68A; --sev-ser-txt:  #D97706;
  --sev-mod-bg:   #FEFCE8; --sev-mod-bdr:  #FEF08A; --sev-mod-txt:  #CA8A04;
  /* Footnote chips */
  --fp-pro-bg:    #EFF6FF; --fp-pro-txt:   #1D4ED8;
  --fp-risk-bg:   #FEF2F2; --fp-risk-txt:  #DC2626;
  --fp-first-bg:  #F0FDF4; --fp-first-txt: #16A34A;
  /* Effort badges */
  --eff-lo-bg:    #F1F5F9; --eff-lo-txt:   #94A3B8;
  --eff-md-bg:    #CBD5E1; --eff-md-txt:   #334155;
  --eff-hi-bg:    #334155; --eff-hi-txt:   #F1F5F9;
  /* Rank badge */
  --rank-bg:      #DBEAFE; --rank-txt:     #2563EB;
}
/* ── Color tokens — dark mode ── */
html[data-theme="dark"] {
  --bg:           #0F172A;
  --surface:      #1E293B;
  --subtle:       #162032;
  --border:       #334155;
  --bdr-mid:      #475569;
  --t1:           #F1F5F9;
  --t2:           #E2E8F0;
  --t3:           #CBD5E1;
  --t4:           #94A3B8;
  --t5:           #64748B;
  --t6:           #475569;
  --t7:           #334155;
  --sev-crit-bg:  rgba(220,38,38,.15); --sev-crit-bdr: rgba(220,38,38,.4); --sev-crit-txt: #F87171;
  --sev-ser-bg:   rgba(217,119,6,.15); --sev-ser-bdr:  rgba(217,119,6,.4); --sev-ser-txt:  #FBB740;
  --sev-mod-bg:   rgba(202,138,4,.15); --sev-mod-bdr:  rgba(202,138,4,.4); --sev-mod-txt:  #FCD34D;
  --fp-pro-bg:    rgba(29,78,216,.15);  --fp-pro-txt:   #60A5FA;
  --fp-risk-bg:   rgba(220,38,38,.15);  --fp-risk-txt:  #F87171;
  --fp-first-bg:  rgba(22,163,74,.15);  --fp-first-txt: #4ADE80;
  --eff-lo-bg:    #1E293B; --eff-lo-txt:   #64748B;
  --eff-md-bg:    #334155; --eff-md-txt:   #94A3B8;
  --eff-hi-bg:    #475569; --eff-hi-txt:   #CBD5E1;
  --rank-bg:      rgba(37,99,235,.2);   --rank-txt:     #60A5FA;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg:           #0F172A;
    --surface:      #1E293B;
    --subtle:       #162032;
    --border:       #334155;
    --bdr-mid:      #475569;
    --t1:           #F1F5F9;
    --t2:           #E2E8F0;
    --t3:           #CBD5E1;
    --t4:           #94A3B8;
    --t5:           #64748B;
    --t6:           #475569;
    --t7:           #334155;
    --sev-crit-bg:  rgba(220,38,38,.15); --sev-crit-bdr: rgba(220,38,38,.4); --sev-crit-txt: #F87171;
    --sev-ser-bg:   rgba(217,119,6,.15); --sev-ser-bdr:  rgba(217,119,6,.4); --sev-ser-txt:  #FBB740;
    --sev-mod-bg:   rgba(202,138,4,.15); --sev-mod-bdr:  rgba(202,138,4,.4); --sev-mod-txt:  #FCD34D;
    --fp-pro-bg:    rgba(29,78,216,.15);  --fp-pro-txt:   #60A5FA;
    --fp-risk-bg:   rgba(220,38,38,.15);  --fp-risk-txt:  #F87171;
    --fp-first-bg:  rgba(22,163,74,.15);  --fp-first-txt: #4ADE80;
    --eff-lo-bg:    #1E293B; --eff-lo-txt:   #64748B;
    --eff-md-bg:    #334155; --eff-md-txt:   #94A3B8;
    --eff-hi-bg:    #475569; --eff-hi-txt:   #CBD5E1;
    --rank-bg:      rgba(37,99,235,.2);   --rank-txt:     #60A5FA;
  }
}

/* Page background */
.stApp { background: var(--bg) !important; }
header[data-testid="stHeader"] { background: transparent !important; box-shadow: none !important; }
[data-testid="stDecoration"] { display: none !important; }
.block-container {
    padding-top: 2.5rem !important;
    padding-bottom: 4rem !important;
    padding-left: 4rem !important;
    padding-right: 4rem !important;
    max-width: 1100px !important;
}

/* Typography */
html, body, p, h1, h2, h3, h4, h5, h6,
[class*="css"], [data-testid="stAppViewContainer"],
button, input, select, textarea, label {
    font-family: 'IBM Plex Sans', sans-serif !important;
}
h1 { font-size: 3.5rem !important; font-weight: 300 !important; letter-spacing: -0.03em !important; color: var(--t1) !important; }
h2 { font-size: 1.5rem !important; font-weight: 600 !important; letter-spacing: -0.02em !important; color: var(--t1) !important; margin-top: 0 !important; }
h3 { font-size: 1.15rem !important; font-weight: 300 !important; color: var(--t1) !important; }

/* Dividers */
hr { border-color: var(--border) !important; margin: 2.5rem 0 !important; opacity: 1 !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-top: 3px solid #2563EB !important;
    border-radius: 10px !important;
    padding: 20px 24px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.07) !important;
}
[data-testid="stMetricValue"] { color: var(--t1) !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: var(--t5) !important; font-weight: 500 !important; }

/* Bordered containers */
[data-testid="stVerticalBlockBorderWrapper"] > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.07) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] { margin-bottom: 12px !important; }

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: var(--subtle) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 2px !important;
    border-bottom: none !important;
}
[data-baseweb="tab"] {
    border-radius: 7px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    color: var(--t5) !important;
    padding-left: 20px !important;
    padding-right: 20px !important;
}
[aria-selected="true"][data-baseweb="tab"] {
    background: var(--surface) !important;
    color: var(--t1) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.07) !important;
}
[data-testid="stTabs"] [data-baseweb="tab-panel"] { padding-top: 20px !important; }
[data-testid="stTabs"] [data-baseweb="tab-highlight"] { background: var(--t1) !important; }

/* Expanders */
[data-testid="stExpander"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.07) !important;
    margin-bottom: 10px !important;
}
[data-testid="stExpander"] summary:not([data-inner]),
[data-testid="stExpander"] summary:not([data-inner]) p,
[data-testid="stExpander"] summary:not([data-inner]) span,
[data-testid="stExpander"] summary:not([data-inner]) div {
    font-weight: 300 !important;
    font-size: 1.2rem !important;
    color: var(--t1) !important;
}
[data-testid="stExpander"] summary:not([data-inner]) {
    padding: 14px 18px !important;
}
[data-testid="stExpander"] summary[data-inner] {
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    color: var(--t2) !important;
    padding: 4px 0 !important;
}

/* Selectbox */
[data-testid="stSelectbox"] > div > div {
    border-color: var(--border) !important;
    border-radius: 10px !important;
    background: var(--surface) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.07) !important;
}

/* Captions */
[data-testid="stCaptionContainer"] p { color: var(--t6) !important; font-size: 0.82rem !important; }

/* Timer iframe */
[data-testid="stCustomComponentV1"] { margin-top: -1.8rem !important; margin-bottom: 0 !important; }

/* Severity / effort / fp CSS classes used in inline HTML */
.sev-badge   { padding:2px 10px;border-radius:4px;font-size:0.72rem;font-weight:300;letter-spacing:.04em;white-space:nowrap;flex-shrink:0;margin-left:12px; }
.sev-crit    { background:var(--sev-crit-bg);color:var(--sev-crit-txt); }
.sev-ser     { background:var(--sev-ser-bg); color:var(--sev-ser-txt); }
.sev-mod     { background:var(--sev-mod-bg); color:var(--sev-mod-txt); }
.quote-block { border-radius:6px;padding:10px 16px;margin-bottom:14px; }
.quote-crit  { background:var(--sev-crit-bg);border-left:3px solid var(--sev-crit-bdr); }
.quote-ser   { background:var(--sev-ser-bg); border-left:3px solid var(--sev-ser-bdr); }
.quote-mod   { background:var(--sev-mod-bg); border-left:3px solid var(--sev-mod-bdr); }
.review-card { border-radius:8px;padding:10px 14px;margin-bottom:8px; }
.review-crit { background:var(--sev-crit-bg);border:1px solid var(--sev-crit-bdr); }
.review-ser  { background:var(--sev-ser-bg); border:1px solid var(--sev-ser-bdr); }
.review-mod  { background:var(--sev-mod-bg); border:1px solid var(--sev-mod-bdr); }
.review-txt  { color:var(--sev-crit-txt); }
.review-ser-txt  { color:var(--sev-ser-txt); }
.review-mod-txt  { color:var(--sev-mod-txt); }
.fp-chip     { padding:2px 10px;border-radius:999px;font-size:0.75rem;font-weight:700;white-space:nowrap;flex-shrink:0; }
.fp-pro      { background:var(--fp-pro-bg);   color:var(--fp-pro-txt); }
.fp-risk     { background:var(--fp-risk-bg);  color:var(--fp-risk-txt); }
.fp-first    { background:var(--fp-first-bg); color:var(--fp-first-txt); }
.eff-badge   { padding:2px 10px;border-radius:4px;font-size:0.72rem;font-weight:300;letter-spacing:.04em;white-space:nowrap;flex-shrink:0;margin-left:12px; }
.eff-lo      { background:var(--eff-lo-bg);color:var(--eff-lo-txt); }
.eff-md      { background:var(--eff-md-bg);color:var(--eff-md-txt); }
.eff-hi      { background:var(--eff-hi-bg);color:var(--eff-hi-txt); }
.rank-badge  { width:24px;height:24px;background:var(--rank-bg);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.8rem;color:var(--rank-txt);flex-shrink:0;margin-top:10px; }

/* Logo animation keyframes */
@keyframes spin-cw  { from{transform:rotate(0deg)}   to{transform:rotate(360deg)}  }
@keyframes spin-ccw { from{transform:rotate(0deg)}   to{transform:rotate(-360deg)} }
@keyframes logo-pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.05)} }
</style>
""", unsafe_allow_html=True)



# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    data_dir    = Path(__file__).parent / "data"
    briefing    = json.loads((data_dir / "pm_briefing.json").read_text())
    themes_list = json.loads((data_dir / "themes_report.json").read_text())
    df          = pd.read_csv(data_dir / "reviews_enriched.csv")
    return briefing, themes_list, df


briefing, themes_list, df = load_data()
themes_by_name = {t["theme"]: t for t in themes_list}
df_sub = df[df["content_quality"] == "substantive"].copy()

ph   = briefing["product_health"]
cp   = briefing["competitive_position"]
meta = briefing["report_meta"]

def _clean_ab(text: str) -> str:
    """Strip redundant 'A/B: ' / 'A/B test: ' prefixes from ab_test fields."""
    for pfx in ("A/B test: ", "A/B: "):
        if text.startswith(pfx):
            return text[len(pfx):]
    return text

# Theme explorer ordering — health-ranked themes first
_health_rank = {iss["theme"]: iss["rank"] for iss in ph["critical_issues"]}

def _theme_display(name):
    return name

_sorted_themes     = sorted(themes_by_name.keys())
_display_options   = _sorted_themes
_display_to_actual = {n: n for n in _sorted_themes}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Header + Executive Summary
# ═══════════════════════════════════════════════════════════════════════════════

components.html("""<script>
var e=window.parent.document.getElementById('cis-logo');if(e)e.remove();
// Read Streamlit's own --background-color CSS variable to detect dark mode
// and mirror it as data-theme on <html> so our CSS selectors fire.
function _applyTheme(){
  try{
    var doc=window.parent.document;
    var bg=window.parent.getComputedStyle(doc.documentElement)
              .getPropertyValue('--background-color').trim();
    var isDark=false;
    if(bg.startsWith('#')&&bg.length>=7){
      var r=parseInt(bg.slice(1,3),16);
      var g=parseInt(bg.slice(3,5),16);
      var b=parseInt(bg.slice(5,7),16);
      isDark=(r*299+g*587+b*114)/1000 < 128;
    } else if(bg.startsWith('rgb')){
      var m=bg.match(/\\d+/g);
      if(m) isDark=(parseInt(m[0])*299+parseInt(m[1])*587+parseInt(m[2])*114)/1000 < 128;
    }
    doc.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
  }catch(ex){}
}
_applyTheme();
setInterval(_applyTheme, 600);
</script>""", height=0, scrolling=False)

st.markdown(f"""
<div style="display:inline-flex;align-items:center;gap:0px;margin-bottom:4px;">
  <h1 style="margin:0;">Customer Insights</h1>
  <svg width="18" height="18" viewBox="0 0 72 72" xmlns="http://www.w3.org/2000/svg"
       style="flex-shrink:0;margin-left:-8px;">
    <g style="transform-origin:36px 36px;animation:spin-cw 14s linear infinite;">
      <circle cx="36" cy="36" r="34" fill="none" style="stroke:var(--t1)" stroke-width="1.5" stroke-dasharray="9 5"/>
    </g>
    <g style="transform-origin:36px 36px;animation:spin-ccw 9s linear infinite;">
      <circle cx="36" cy="36" r="27" fill="none" style="stroke:var(--t1)" stroke-width="1" stroke-dasharray="3 7" opacity="0.35"/>
    </g>
    <g style="transform-origin:36px 36px;animation:logo-pulse 3.5s ease-in-out infinite;">
      <circle cx="36" cy="36" r="20" style="fill:var(--t1)"/>
    </g>
  </svg>
  <span style="color:var(--t1);font-size:0.72rem;font-weight:500;
        white-space:nowrap;flex-shrink:0;letter-spacing:.03em;
        margin-left:5px;">Powered by Claude</span>
</div>
""", unsafe_allow_html=True)

_gen_at = meta.get("generated_at", "2026-05-26T00:00:00+00:00")
components.html(f"""<!DOCTYPE html>
<html><head>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@100;300;700&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:'IBM Plex Mono',monospace;overflow:hidden;background:var(--bg);}}
:root{{--bg:#F8FAFC;--txt:#0F172A;--muted:#94A3B8;--sep:#CBD5E1;}}
@media(prefers-color-scheme:dark){{
  :root{{--bg:#0F172A;--txt:#CBD5E1;--muted:#475569;--sep:#334155;}}
}}
.row{{display:flex;align-items:center;gap:0;white-space:nowrap;padding-left:6px;}}
.seg{{font-size:0.78rem;font-weight:300;letter-spacing:.04em;}}
.muted{{color:var(--muted);}}
.dk{{color:var(--txt);}}
.sep{{color:var(--sep);margin:0 8px;}}
.timer{{font-size:0.78rem;font-weight:400;color:var(--txt);letter-spacing:.04em;}}
</style></head><body>
<div class="row">
  <span class="seg muted">synced</span>
  <span class="sep">·</span>
  <span class="seg dk" id="dt">—</span>
  <span class="sep">·</span>
  <span class="timer" id="tmr">—</span>
  <span class="seg muted" style="margin-left:5px;">ago</span>
</div>
<script>
var t0 = new Date("{_gen_at}");
document.getElementById('dt').innerText = t0.toLocaleDateString('en-GB', {{
  day: '2-digit', month: 'short', year: 'numeric'
}});
function tick() {{
  var s = Math.max(0, Math.floor((new Date() - t0) / 1000));
  var d = Math.floor(s / 86400);
  var h = Math.floor((s % 86400) / 3600);
  var m = Math.floor((s % 3600) / 60);
  var sc = s % 60;
  var parts = [];
  if (d > 0) parts.push(d + ' ' + (d === 1 ? 'day' : 'days'));
  if (d > 0 || h > 0) parts.push(h + ' ' + (h === 1 ? 'hour' : 'hours'));
  parts.push(m + ' ' + 'minutes');
  document.getElementById('tmr').innerText = parts.join(' ');
}}
tick(); setInterval(tick, 1000);
function syncTheme(){{
  try{{
    var doc=window.parent.document;
    var bg=window.parent.getComputedStyle(doc.documentElement)
              .getPropertyValue('--background-color').trim();
    var dark=false;
    if(bg.startsWith('#')&&bg.length>=7){{
      var r2=parseInt(bg.slice(1,3),16);
      var g2=parseInt(bg.slice(3,5),16);
      var b2=parseInt(bg.slice(5,7),16);
      dark=(r2*299+g2*587+b2*114)/1000<128;
    }}else if(bg.startsWith('rgb')){{
      var m=bg.match(/\\d+/g);
      if(m) dark=(parseInt(m[0])*299+parseInt(m[1])*587+parseInt(m[2])*114)/1000<128;
    }}
    var r=document.documentElement;
    if(dark){{
      r.style.setProperty('--bg','#0F172A');
      r.style.setProperty('--txt','#CBD5E1');
      r.style.setProperty('--muted','#475569');
      r.style.setProperty('--sep','#334155');
    }}else{{
      r.style.removeProperty('--bg');r.style.removeProperty('--txt');
      r.style.removeProperty('--muted');r.style.removeProperty('--sep');
    }}
  }}catch(e){{}}
}}
syncTheme(); setInterval(syncTheme,800);
</script>
</body></html>""", height=40, scrolling=False)

st.markdown(f"""
<p style="margin:-0.75rem 0 12px;font-size:1.1rem;font-family:'IBM Plex Sans',sans-serif;
   color:var(--t1);font-weight:300;letter-spacing:-0.01em;">
  Competitive Product Analysis
</p>
<p style="margin:0 0 4px;font-size:0.82rem;font-family:'IBM Plex Mono',monospace;
   color:var(--t1);font-weight:300;letter-spacing:.01em;">
  <span style="color:var(--t6);">APPS</span>&nbsp;&nbsp;·&nbsp;&nbsp;lidl-plus  /  rewe-app  ·  DE grocery  ·  432 reviews
</p>
<p style="margin:0 0 28px;font-size:0.82rem;font-family:'IBM Plex Mono',monospace;
   color:var(--t1);font-weight:300;letter-spacing:.01em;">
  <span style="color:var(--t6);">OUTPUT</span>&nbsp;&nbsp;·&nbsp;&nbsp;13 themes  ·  5 critical issues  ·  9 competitive signals  ·  5 sprint recommendations
</p>
<p style="margin:0 0 6px;font-size:0.72rem;font-weight:500;letter-spacing:.01em;
   color:var(--t6);">Executive Summary</p>
<p style="margin:0;font-size:0.9rem;color:var(--t4);line-height:1.75;">
  {briefing['executive_summary']}
</p>
""", unsafe_allow_html=True)

st.markdown(
    f"<p style='font-size:0.78rem;color:var(--t6);line-height:1.6;margin-top:16px;'>"
    f"<strong style='color:var(--t4);'>Methodology</strong> — "
    f"{briefing['methodology'].replace('content-quality filtering', 'content-quality filtering (216 per app)')}</p>",
    unsafe_allow_html=True,
)

st.write("")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Comparative Theme Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="display:flex;align-items:center;gap:14px;margin-bottom:6px;">

  <div>
    <h2 style="margin:0;">What Users Are Talking About</h2>
    <p style="margin:4px 0 0;color:var(--t5);font-size:0.88rem;">
      Substantive reviews only — vague single-word reviews excluded from counts.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)
st.write("")

# Chart data
theme_counts = (
    df_sub.groupby(["primary_theme", "app"])
    .size()
    .reset_index(name="Reviews")
)
theme_counts["App"] = theme_counts["app"].map({"lidl-plus": "Lidl Plus", "rewe": "REWE"})

theme_order_asc = (
    theme_counts.groupby("primary_theme")["Reviews"]
    .sum()
    .sort_values(ascending=True)
    .index.tolist()
)

fig = px.bar(
    theme_counts,
    x="Reviews", y="primary_theme", color="App",
    barmode="group", orientation="h",
    category_orders={"App": ["Lidl Plus", "REWE"]},
    color_discrete_map={"Lidl Plus": "#2563EB", "REWE": "#EA580C"},
    labels={"primary_theme": "", "Reviews": "Substantive reviews"},
    height=490,
)
fig.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                font=dict(size=13)),
    margin=dict(l=0, r=20, t=40, b=0),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Sans, sans-serif", size=12, color="#64748B"),
    xaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.2)", gridwidth=1, zeroline=False,
               tickfont=dict(color="#64748B")),
    yaxis=dict(showgrid=False, tickfont=dict(size=12, color="#64748B")),
    bargap=0.25, bargroupgap=0.08,
)
fig.update_traces(marker_line_width=0, marker_cornerradius=3)
fig.update_yaxes(categoryorder="array", categoryarray=theme_order_asc)
st.plotly_chart(fig, use_container_width=True)

st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Product Health + Competitive Position
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="display:flex;align-items:center;gap:14px;margin-bottom:6px;">

  <h2 style="margin:0;">Product Health &amp; Competitive Position</h2>
</div>
""", unsafe_allow_html=True)
st.write("")

tab_health, tab_competitive = st.tabs(["Product Health", "Competitive Position"])

# ── Tab 1: Product Health ─────────────────────────────────────────────────────
with tab_health:
    # Verdict + positive signal
    st.markdown(f"""
<div style="background:var(--subtle);border:1px solid var(--border);border-radius:10px;
     padding:16px 20px;margin-bottom:20px;">
  <p style="margin:0 0 4px;font-size:0.72rem;font-weight:700;letter-spacing:.06em;
     color:var(--t6);">Overall verdict</p>
  <p style="margin:0;font-size:0.9rem;color:var(--t2);font-weight:500;line-height:1.5;">
    {ph['overall_verdict']}
  </p>
</div>
""", unsafe_allow_html=True)

    # Issue cards — collapsible
    sev_cls = {
        "critical": "sev-crit",
        "serious":  "sev-ser",
        "moderate": "sev-mod",
    }
    effort_colors = {"low": "#16A34A", "medium": "#CA8A04", "high": "#DC2626"}
    sprint_by_rank = {r["priority_rank"]: r for r in briefing["sprint_recommendations"]}
    # Synthetic sprint for Search & navigation — displaced from the top-5 by strategic bets
    sprint_by_rank[6] = {
        "action":          "Replace current search with unified product + receipt + category bar pinned to home; restore receipt search.",
        "ab_test":         "Unified search bar vs. current: target 25% lift in search-to-click rate and reduction in 'cannot find' complaints within 4 weeks.",
        "expected_impact": "Removes a top-5 UX complaint. Search failure currently trains users to stop opening the app for anything beyond coupons.",
        "rationale":       "No competitive timing pressure, but a straightforward core fix with directly measurable impact — schedule after the auth and stability hotfixes land.",
    }
    # Explicit theme → sprint priority_rank mapping (sprint ranks don't align 1:1 with issue ranks)
    _theme_sprint_map = {
        "Authentication & login":    1,  # email magic-link auth
        "Onboarding & registration": 1,  # same fix covers both auth + onboarding
        "Performance & stability":   2,  # hotfix post-update regression
        "Coupons & discounts":       4,  # auto-activate coupons
        "Search & navigation":       6,  # synthetic — not in top-5 sprint recs
    }

    for issue in ph["critical_issues"]:
        sc = sev_cls.get(issue["severity"], "sev-mod")
        sprint_rec = sprint_by_rank.get(_theme_sprint_map.get(issue["theme"]))
        if sprint_rec:
            sr_html = (
                f'<details style="margin-top:4px;">'
                f'<summary style="cursor:pointer;font-weight:600;font-size:0.9rem;'
                f'color:var(--t2);padding:4px 0;">Sprint Recommendation</summary>'
                f'<div style="padding:10px 0 4px 0;margin-top:6px;">'
                f'<p style="margin:0 0 6px;font-size:0.9rem;color:var(--t4);">'
                f'<span style="font-weight:600;color:var(--t2);">Action: </span>{sprint_rec["action"]}</p>'
                f'<p style="margin:0 0 6px;font-size:0.9rem;color:var(--t4);">'
                f'<span style="font-weight:600;color:var(--t2);">A/B test: </span>{_clean_ab(sprint_rec["ab_test"])}</p>'
                f'<p style="margin:0 0 6px;font-size:0.9rem;color:var(--t4);">'
                f'<span style="font-weight:600;color:var(--t2);">Expected impact: </span>{sprint_rec["expected_impact"]}</p>'
                f'<p style="margin:0;font-size:0.82rem;color:var(--t6);">{sprint_rec["rationale"]}</p>'
                f'</div></details>'
            )
        else:
            sr_html = (
                f'<p style="margin:0;font-size:0.9rem;color:var(--t4);">'
                f'<span style="font-weight:600;color:var(--t2);">Recommended fix: </span>'
                f'{issue["recommended_fix"]}</p>'
            )
        st.markdown(f"""
<div style="background:var(--surface);border:1px solid var(--border);border-radius:10px;
     padding:10px 18px;margin-bottom:8px;">
  <details>
    <summary style="cursor:pointer;list-style:none;display:flex;align-items:center;
         justify-content:space-between;padding:14px 0;font-size:1.2rem;font-weight:300;color:var(--t1);">
      <span>{issue['theme']}</span>
      <span class="sev-badge {sc}">{issue['severity'].upper()}</span>
    </summary>
    <div style="padding:10px 0 6px 0;margin-top:6px;border-top:1px solid var(--subtle);">
      <p style="margin:0 0 6px;font-size:0.9rem;color:var(--t4);">
        <span style="font-weight:600;color:var(--t2);">What's happening: </span>{issue['what_is_happening']}
      </p>
      <p style="margin:0 0 12px;font-size:0.9rem;color:var(--t4);">
        <span style="font-weight:600;color:var(--t2);">Business impact: </span>{issue['business_impact']}
      </p>
      <div class="quote-block quote-{sc.replace('sev-', '')}">
        <p style="margin:0;font-style:italic;font-size:0.88rem;color:var(--t3);">
          &ldquo;{issue['user_voice_de']}&rdquo;
        </p>
      </div>
      {sr_html}
    </div>
  </details>
</div>""", unsafe_allow_html=True)

    st.markdown(f"""
<p style="font-size:0.78rem;color:var(--t6);margin-top:16px;line-height:1.6;">
  <strong style="color:var(--t4);">How issues are ranked:</strong>
  (1) Severity — whether the issue blocks core functionality entirely or degrades the experience;
  (2) Funnel position — auth and onboarding failures rank above mid-funnel issues because they
  prevent any loyalty value from reaching the user;
  (3) Lidl Plus review volume at that severity level, as a proxy for the number of users actively affected.
</p>
""", unsafe_allow_html=True)

# ── Tab 2: Competitive Position ───────────────────────────────────────────────
with tab_competitive:
    def cp_row(area, body, footnote, footnote_prefix, sprint_rec=None):
        fp_cls = {
            "Protect:":          "fp-pro",
            "Risk:":             "fp-risk",
            "First mover wins:": "fp-first",
        }
        fpc = fp_cls.get(footnote_prefix, "fp-pro")
        if sprint_rec:
            sprint_html = (
                f'<div style="margin-top:12px;">'
                f'<details>'
                f'<summary data-inner style="cursor:pointer;">Sprint Recommendation '
                f'<span style="font-weight:400;color:var(--t6);font-size:0.9rem;">'
                f'(time-sensitive competitive move)</span></summary>'
                f'<div style="padding:10px 0 4px 0;margin-top:6px;">'
                f'<p style="margin:0 0 6px;font-size:0.88rem;color:var(--t4);">'
                f'<span style="font-weight:600;color:var(--t2);">Action: </span>{sprint_rec["action"]}</p>'
                f'<p style="margin:0 0 6px;font-size:0.88rem;color:var(--t4);">'
                f'<span style="font-weight:600;color:var(--t2);">A/B test: </span>{_clean_ab(sprint_rec["ab_test"])}</p>'
                f'<p style="margin:0 0 6px;font-size:0.88rem;color:var(--t4);">'
                f'<span style="font-weight:600;color:var(--t2);">Expected impact: </span>{sprint_rec["expected_impact"]}</p>'
                f'<p style="margin:0;font-size:0.82rem;color:var(--t6);">{sprint_rec["rationale"]}</p>'
                f'</div></details>'
                f'</div>'
            )
        else:
            sprint_html = ""
        st.markdown(f"""
<div style="padding:14px 0;border-bottom:1px solid var(--border);">
  <p style="margin:0 0 6px;font-weight:700;font-size:0.9rem;color:var(--t1);">{area}</p>
  <p style="margin:0 0 10px;font-size:0.88rem;color:var(--t4);line-height:1.55;">{body}</p>
  <div style="display:flex;align-items:flex-start;gap:8px;">
    <span class="fp-chip {fpc}">{footnote_prefix}</span>
    <p style="margin:0;font-size:0.82rem;color:var(--t5);line-height:1.5;">{footnote}</p>
  </div>
  {sprint_html}
</div>""", unsafe_allow_html=True)

    with st.expander("Where We Lead", expanded=True):
        for item in cp["where_we_lead"]:
            cp_row(item["area"], item["finding"], item["how_to_protect"], "Protect:")

    with st.expander("Where We Trail", expanded=True):
        for item in cp["where_we_trail"]:
            cp_row(item["area"], item["finding"], item["risk_if_ignored"], "Risk:")

    _battleground_sprint_map = {
        "Shopping list with voice and barcode": 3,
        "Multi-store map and switching":        5,
    }
    with st.expander("Battlegrounds — Neither app owns these yet", expanded=True):
        for item in cp["battlegrounds"]:
            sr = sprint_by_rank.get(_battleground_sprint_map.get(item["area"]))
            cp_row(item["area"], item["situation"], item["first_mover_advantage"], "First mover wins:", sprint_rec=sr)

st.divider()


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Sprint Recommendations
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="display:flex;align-items:center;gap:14px;margin-bottom:6px;">

  <div>
    <h2 style="margin:0;">Sprint Recommendations</h2>
    <p style="margin:4px 0 0;color:var(--t5);font-size:0.88rem;">
      Ranked by priority — ship in order.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)
st.write("")

effort_cls_sprint = {
    "low":    "eff-lo",
    "medium": "eff-md",
    "high":   "eff-hi",
}

_sprint_titles = {
    1: "Email magic-link auth + in-app OAuth",
    2: "Hotfix post-update regression",
    3: "Voice shopping list + barcode scanner",
    4: "Auto-activate coupons",
    5: "Multi-store map + store switching",
}

_sprint_recs = briefing["sprint_recommendations"]
for i, rec in enumerate(_sprint_recs):
    ec    = effort_cls_sprint.get(rec["effort"], "eff-lo")
    title = _sprint_titles.get(rec["priority_rank"], rec["action"])
    st.markdown(f"""
<div style="display:flex;gap:14px;align-items:flex-start;
     background:var(--surface);border:1px solid var(--border);border-radius:10px;
     padding:6px 18px;margin-bottom:4px;">
  <div class="rank-badge">{rec['priority_rank']}</div>
  <div style="flex:1;min-width:0;">
    <details>
      <summary style="cursor:pointer;list-style:none;display:flex;align-items:center;
           justify-content:space-between;padding:8px 0;font-size:1rem;font-weight:500;color:var(--t1);letter-spacing:-0.01em;">
        <span>{title}</span>
        <span class="eff-badge {ec}">{rec['effort'].upper()} EFFORT</span>
      </summary>
      <div style="padding:10px 0 6px 0;margin-top:6px;border-top:1px solid var(--subtle);">
        <p style="margin:0 0 6px;font-size:0.88rem;color:var(--t4);">
          <span style="font-weight:600;color:var(--t2);">Action: </span>{rec['action']}
        </p>
        <p style="margin:0 0 6px;font-size:0.88rem;color:var(--t4);">
          <span style="font-weight:600;color:var(--t2);">A/B test: </span>{_clean_ab(rec['ab_test'])}
        </p>
        <p style="margin:0 0 10px;font-size:0.88rem;color:var(--t4);">
          <span style="font-weight:600;color:var(--t2);">Expected impact: </span>{rec['expected_impact']}
        </p>
        <p style="margin:0;font-size:1.05rem;font-weight:400;color:var(--t2);
             line-height:1.7;">{rec['rationale']}</p>
      </div>
    </details>
  </div>
</div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Theme Explorer
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="border-top:1px dashed var(--bdr-mid);margin:4rem 0 24px;"></div>
<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
  <span style="font-size:1.5rem;font-weight:600;color:var(--t6);letter-spacing:-0.02em;">Theme Explorer</span>
  <span style="font-size:0.68rem;font-weight:500;letter-spacing:.06em;color:var(--t6);
       border:1px solid var(--bdr-mid);border-radius:4px;padding:1px 6px;">OPTIONAL</span>
</div>
<p style="margin:0 0 16px;color:var(--t7);font-size:0.82rem;">
  Select any theme to see full synthesis, app context, and sample quotes.
</p>
""", unsafe_allow_html=True)
st.write("")

selected_display = st.selectbox("Theme", _display_options, label_visibility="collapsed")
selected = _display_to_actual[selected_display]

if selected:
    t = themes_by_name[selected]

    action_colors = {
        "fix-stability-bug": "#DC2626",
        "redesign-flow":     "#7C3AED",
        "build-new-feature": "#16A34A",
        "clarify-comms":     "#CA8A04",
        "research-deeper":   "#0891B2",
    }
    ac = action_colors.get(t["pm_action"], "#64748B")

    strategic_html = (
        f"<p style='margin:0 0 4px;font-size:0.75rem;font-weight:500;letter-spacing:.01em;"
        f"color:var(--t6);'>Strategic note</p>"
        f"<p style='margin:0 0 28px;font-size:0.88rem;color:var(--t4);line-height:1.7;'>"
        f"{t['strategic_note']}</p>"
    ) if t.get("strategic_note") else ""

    st.markdown(f"""
<div style="margin-top:16px;">
  <div style="display:flex;align-items:center;justify-content:space-between;
       flex-wrap:wrap;gap:8px;margin-bottom:4px;">
    <div style="margin:0;font-size:1rem;font-weight:400;color:var(--t1);">{_theme_display(selected)}</div>
    <span style="background:{ac}1F;color:{ac};padding:2px 10px;border-radius:4px;
         font-size:0.72rem;font-weight:300;letter-spacing:.04em;flex-shrink:0;">
      {t['pm_action'].replace('-', ' ').upper()}</span>
  </div>
  <p style="margin:0 0 24px;font-size:0.88rem;color:var(--t6);line-height:1.65;">
    {t['theme_description']}</p>

  <p style="margin:0 0 4px;font-size:0.75rem;font-weight:500;letter-spacing:.01em;
     color:var(--t6);">Analysis</p>
  <p style="margin:0 0 28px;font-size:0.95rem;color:var(--t3);line-height:1.75;">
    {t['lidl_summary']}</p>

  {strategic_html}

  <p style="margin:0 0 4px;font-size:0.75rem;font-weight:500;letter-spacing:.01em;
     color:var(--t6);">Test hypothesis</p>
  <p style="margin:0 0 20px;font-size:0.88rem;color:var(--t4);line-height:1.65;">
    {t['ab_test_idea']}</p>
</div>
""", unsafe_allow_html=True)

    # Sample quotes — emojis kept here per spec
    st.write("")
    theme_df = df_sub[df_sub["primary_theme"] == selected]
    sev_styles = {
        "critical": {"text": "#DC2626", "bg": "#FEF2F2", "border": "#FECACA"},
        "serious":  {"text": "#D97706", "bg": "#FFFBEB", "border": "#FDE68A"},
        "moderate": {"text": "#CA8A04", "bg": "#FEFCE8", "border": "#FEF08A"},
        "high":     {"text": "#DC2626", "bg": "#FEF2F2", "border": "#FECACA"},
        "medium":   {"text": "#D97706", "bg": "#FFFBEB", "border": "#FDE68A"},
        "low":      {"text": "#CA8A04", "bg": "#FEFCE8", "border": "#FEF08A"},
    }
    rev_sev_cls = {"high": "sev-crit", "medium": "sev-ser", "low": "sev-mod",
                   "critical": "sev-crit", "serious": "sev-ser", "moderate": "sev-mod"}
    with st.expander("Sample reviews"):
        app_df = theme_df[theme_df["app"] == "lidl-plus"]
        st.markdown(
            f"<p style='font-size:0.82rem;font-weight:700;color:#2563EB;"
            f"letter-spacing:.01em;margin-bottom:8px;'>"
            f"Lidl Plus · {len(app_df)} reviews</p>",
            unsafe_allow_html=True,
        )
        if app_df.empty:
            st.markdown(
                "<p style='font-size:0.88rem;color:var(--t6);font-style:italic;'>"
                f"No substantive reviews.</p>",
                unsafe_allow_html=True,
            )
        else:
            shown = set()
            for sev in ["high", "medium", "low"]:
                rows = app_df[(app_df["severity"] == sev) & (~app_df.index.isin(shown))]
                if rows.empty:
                    continue
                row = rows.iloc[0]
                shown.add(rows.index[0])
                rc  = rev_sev_cls.get(sev, "sev-mod")
                txt = str(row["review"])[:240] + ("…" if len(str(row["review"])) > 240 else "")
                fr  = (f"<p style='margin:6px 0 0;font-size:0.78rem;color:var(--t6);'>"
                       f"→ {row['feature_request']}</p>"
                       if pd.notna(row.get("feature_request")) else "")
                st.markdown(f"""
<div class="review-card review-{rc.replace('sev-', '')}">
  <p style="margin:0 0 4px;font-size:0.75rem;" class="review-txt {rc.replace('sev-', '')}-txt">
    ★{row['rating']} &nbsp;·&nbsp; {sev.upper()}
  </p>
  <p style="margin:0;font-size:0.88rem;color:var(--t3);line-height:1.55;font-style:italic;">
    &ldquo;{txt}&rdquo;
  </p>{fr}
</div>""", unsafe_allow_html=True)
                if len(shown) >= 3:
                    break

st.markdown("""
<div style="margin-top:4rem;padding-top:1.5rem;border-top:1px solid var(--border);
     text-align:center;">
  <p style="margin:0;font-size:0.75rem;color:var(--t7);letter-spacing:.02em;">
    © 2026 All rights reserved.
  </p>
</div>
""", unsafe_allow_html=True)
