"""
streamlit_app.py — TeachWise AI Streamlit Frontend
Reuses existing Flask agents, analytics and IBM Granite integration.
Run: streamlit run streamlit_app.py
"""
import os
import sys
import io
import json
import pandas as pd

# Ensure app package is importable from project root
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="TeachWise AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Luxury Editorial CSS — 60/30/10 Warm Champagne / Espresso / Amber ─────────
st.markdown("""
<style>
/* ── Google Fonts ───────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');

/* ── Global tokens ──────────────────────────────────────────────────────── */
:root {
  --champagne:   #D5C4AE;
  --ivory:       #F2EDE6;
  --espresso:    #1A120E;
  --walnut:      #3A2418;
  --bronze:      #A88462;
  --amber:       #D5851F;
  --amber-light: #E8A84A;
  --sage:        #87A968;
  --charcoal:    #4A4A46;
  --surface:     #EDE5D8;
  --border:      #C8B89A;
  --text-main:   #1A120E;
  --text-muted:  #6B5C4A;
  --text-light:  #9C8A72;
  --danger:      #C0392B;
  --danger-bg:   #FDF0EF;
}

/* ── App shell background ────────────────────────────────────────────────── */
.stApp {
  background-color: var(--ivory);
  font-family: 'Inter', system-ui, sans-serif;
  color: var(--text-main);
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--espresso) !important;
  border-right: 1px solid var(--walnut);
}
[data-testid="stSidebar"] > div:first-child {
  padding: 0;
}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
  color: var(--champagne) !important;
}
[data-testid="stSidebar"] hr {
  border-color: var(--walnut) !important;
  opacity: 0.6;
}
/* Radio buttons in sidebar */
[data-testid="stSidebar"] [data-testid="stRadio"] label {
  color: var(--champagne) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.88rem !important;
  font-weight: 400 !important;
  padding: 6px 0 !important;
  letter-spacing: 0.01em;
  transition: color 0.15s ease;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
  color: var(--amber) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] [data-baseweb="radio"] {
  accent-color: var(--amber) !important;
}

/* ── Headings ────────────────────────────────────────────────────────────── */
h1 {
  font-family: 'Playfair Display', Georgia, serif !important;
  font-size: 2rem !important;
  font-weight: 700 !important;
  color: var(--espresso) !important;
  letter-spacing: -0.02em;
  margin-bottom: 2px !important;
}
h2 {
  font-family: 'Playfair Display', Georgia, serif !important;
  font-size: 1.35rem !important;
  font-weight: 600 !important;
  color: var(--walnut) !important;
  letter-spacing: -0.01em;
}
h3 {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.95rem !important;
  font-weight: 600 !important;
  color: var(--charcoal) !important;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

/* ── KPI / metric cards ──────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 20px 14px !important;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}
[data-testid="stMetric"]:hover {
  box-shadow: 0 4px 16px rgba(26,18,14,0.08);
  border-color: var(--bronze);
}
[data-testid="stMetricLabel"] {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  color: var(--text-muted) !important;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
[data-testid="stMetricValue"] {
  font-family: 'Playfair Display', Georgia, serif !important;
  font-size: 2rem !important;
  font-weight: 700 !important;
  color: var(--espresso) !important;
}
[data-testid="stMetricDelta"] {
  font-size: 0.75rem !important;
  font-family: 'Inter', sans-serif !important;
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"] {
  background: var(--amber) !important;
  color: var(--espresso) !important;
  border: none !important;
  border-radius: 7px !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
  letter-spacing: 0.03em;
  padding: 10px 24px !important;
  transition: background 0.18s ease, box-shadow 0.18s ease;
}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover {
  background: var(--amber-light) !important;
  box-shadow: 0 3px 12px rgba(213,133,31,0.35) !important;
}
.stButton > button[kind="secondary"] {
  background: transparent !important;
  color: var(--walnut) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 7px !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 500 !important;
  font-size: 0.88rem !important;
  transition: border-color 0.18s, color 0.18s;
}
.stButton > button[kind="secondary"]:hover {
  border-color: var(--amber) !important;
  color: var(--amber) !important;
}
/* Download button */
[data-testid="stDownloadButton"] > button {
  background: transparent !important;
  color: var(--walnut) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 7px !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 500 !important;
  font-size: 0.85rem !important;
  transition: border-color 0.18s, color 0.18s;
}
[data-testid="stDownloadButton"] > button:hover {
  border-color: var(--amber) !important;
  color: var(--amber) !important;
}

/* ── Form inputs ─────────────────────────────────────────────────────────── */
.stTextInput input,
.stTextArea textarea,
.stSelectbox select,
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {
  background: #FFFFFF !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 7px !important;
  color: var(--text-main) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.88rem !important;
  transition: border-color 0.15s;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
  border-color: var(--amber) !important;
  box-shadow: 0 0 0 3px rgba(213,133,31,0.12) !important;
}
.stTextInput label,
.stTextArea label,
.stSelectbox label,
.stSlider label,
.stMultiSelect label,
.stCheckbox label,
[data-testid="stWidgetLabel"] {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.82rem !important;
  font-weight: 600 !important;
  color: var(--charcoal) !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* ── Dataframe / table ───────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  overflow: hidden;
}
.dvn-scroller {
  background: #FFFFFF !important;
}

/* ── Expanders ───────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
  background: #FFFFFF !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  margin-bottom: 8px;
}
[data-testid="stExpander"] summary {
  font-family: 'Inter', sans-serif !important;
  font-size: 0.88rem !important;
  font-weight: 500 !important;
  color: var(--walnut) !important;
  padding: 12px 16px !important;
}
[data-testid="stExpander"] summary:hover {
  background: var(--surface) !important;
}

/* ── Dividers ────────────────────────────────────────────────────────────── */
hr {
  border-color: var(--border) !important;
  opacity: 0.5;
  margin: 20px 0 !important;
}

/* ── Alerts and status ───────────────────────────────────────────────────── */
[data-testid="stAlert"][kind="error"],
.stAlert[data-baseweb="notification"][kind="negative"] {
  background: var(--danger-bg) !important;
  border-left: 3px solid var(--danger) !important;
  border-radius: 7px !important;
  color: var(--danger) !important;
}
[data-testid="stAlert"][kind="warning"] {
  background: #FDF8EE !important;
  border-left: 3px solid var(--amber) !important;
  border-radius: 7px !important;
}
[data-testid="stAlert"][kind="success"] {
  background: #F3F7EE !important;
  border-left: 3px solid var(--sage) !important;
  border-radius: 7px !important;
  color: #3D5E2A !important;
}
[data-testid="stAlert"][kind="info"] {
  background: var(--surface) !important;
  border-left: 3px solid var(--bronze) !important;
  border-radius: 7px !important;
  color: var(--walnut) !important;
}

/* ── Spinner ─────────────────────────────────────────────────────────────── */
[data-testid="stSpinner"] p {
  color: var(--bronze) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.85rem !important;
}

/* ── Progress bar ────────────────────────────────────────────────────────── */
[data-testid="stProgress"] > div > div {
  background: var(--amber) !important;
}

/* ── Caption / small text ────────────────────────────────────────────────── */
.stCaption, [data-testid="stCaptionContainer"] {
  color: var(--text-muted) !important;
  font-family: 'Inter', sans-serif !important;
  font-size: 0.8rem !important;
}

/* ── Selectbox ───────────────────────────────────────────────────────────── */
[data-baseweb="select"] > div {
  background: #FFFFFF !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 7px !important;
}

/* ── Slider ──────────────────────────────────────────────────────────────── */
[data-baseweb="slider"] [data-testid="stSliderThumb"] {
  background: var(--amber) !important;
  border-color: var(--amber) !important;
}
[data-baseweb="slider"] [role="progressbar"] {
  background: var(--amber) !important;
}

/* ── Custom components ───────────────────────────────────────────────────── */

/* Page header band */
.tw-page-header {
  border-bottom: 1px solid var(--border);
  padding-bottom: 14px;
  margin-bottom: 24px;
}
.tw-page-header h1 { margin-bottom: 2px !important; }
.tw-page-subtitle {
  font-family: 'Inter', sans-serif;
  font-size: 0.82rem;
  color: var(--text-muted);
  letter-spacing: 0.01em;
}

/* Section label */
.tw-section-label {
  font-family: 'Inter', sans-serif;
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-light);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}

/* Gap severity cards */
.gap-critical {
  border-left: 3px solid var(--danger);
  padding: 12px 16px;
  background: #FDF0EF;
  border-radius: 0 7px 7px 0;
  margin: 6px 0;
}
.gap-critical strong { color: var(--danger); }

.gap-significant {
  border-left: 3px solid var(--amber);
  padding: 12px 16px;
  background: #FDF8EE;
  border-radius: 0 7px 7px 0;
  margin: 6px 0;
}
.gap-significant strong { color: #9A5F0F; }

.gap-moderate {
  border-left: 3px solid var(--bronze);
  padding: 12px 16px;
  background: var(--surface);
  border-radius: 0 7px 7px 0;
  margin: 6px 0;
}
.gap-moderate strong { color: var(--walnut); }

.gap-meta {
  font-family: 'Inter', sans-serif;
  font-size: 0.78rem;
  color: var(--text-muted);
  margin-top: 2px;
}
.gap-intervention {
  font-family: 'Inter', sans-serif;
  font-size: 0.83rem;
  color: var(--charcoal);
  margin-top: 6px;
}

/* Advisory box */
.advisory-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 18px;
  font-family: 'Inter', sans-serif;
  font-size: 0.82rem;
  color: var(--text-muted);
  margin-top: 16px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

/* Resource link rows */
.res-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 7px;
  margin-bottom: 6px;
  font-family: 'Inter', sans-serif;
  font-size: 0.85rem;
  color: var(--walnut);
  text-decoration: none;
  transition: border-color 0.15s, background 0.15s;
}
.res-row:hover { border-color: var(--amber); background: #FDFAF4; }
.res-type {
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 2px 7px;
  border-radius: 4px;
  background: var(--surface);
  color: var(--text-muted);
}

/* Sidebar brand block */
.tw-sidebar-brand {
  padding: 24px 20px 18px;
  border-bottom: 1px solid rgba(58,36,24,0.5);
  margin-bottom: 8px;
}
.tw-sidebar-logo {
  font-family: 'Playfair Display', Georgia, serif;
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--champagne);
  letter-spacing: -0.01em;
}
.tw-sidebar-logo span { color: var(--amber); }
.tw-sidebar-tagline {
  font-family: 'Inter', sans-serif;
  font-size: 0.7rem;
  color: var(--bronze);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-top: 4px;
}

/* Sidebar nav label */
.tw-nav-label {
  font-family: 'Inter', sans-serif;
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--bronze);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  padding: 14px 20px 4px;
}

/* Status badge */
.tw-status-ok {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: 'Inter', sans-serif;
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--sage);
  padding: 5px 12px;
  background: rgba(135,169,104,0.12);
  border: 1px solid rgba(135,169,104,0.3);
  border-radius: 20px;
}
.tw-status-err {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: 'Inter', sans-serif;
  font-size: 0.78rem;
  font-weight: 500;
  color: #B85C38;
  padding: 5px 12px;
  background: rgba(192,57,43,0.08);
  border: 1px solid rgba(192,57,43,0.2);
  border-radius: 20px;
}

/* Granite badge in main content */
.tw-granite-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-family: 'Inter', sans-serif;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--bronze);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 3px 10px;
  vertical-align: middle;
  margin-left: 8px;
}

/* CO attainment level pill */
.co-attained    { color: #3D5E2A; background: rgba(135,169,104,0.15); border: 1px solid rgba(135,169,104,0.4); padding: 2px 8px; border-radius: 12px; font-size:0.75rem; font-weight:600; }
.co-partial     { color: #9A5F0F; background: rgba(213,133,31,0.12);  border: 1px solid rgba(213,133,31,0.35); padding: 2px 8px; border-radius: 12px; font-size:0.75rem; font-weight:600; }
.co-not         { color: var(--danger); background: rgba(192,57,43,0.08); border: 1px solid rgba(192,57,43,0.25); padding: 2px 8px; border-radius: 12px; font-size:0.75rem; font-weight:600; }

/* Checklist items in stage log */
.stage-ok  { color: var(--sage);    font-size:0.85rem; padding:2px 0; }
.stage-err { color: var(--danger);  font-size:0.85rem; padding:2px 0; }
.stage-run { color: var(--bronze);  font-size:0.85rem; padding:2px 0; }

</style>
""", unsafe_allow_html=True)

# ── Flask app initialization — module level, runs once per process ────────────
from app import create_app as _create_app, db as _db  # noqa: E402

_flask_app = _create_app()
_app_ctx = _flask_app.app_context()
_app_ctx.push()   # permanent context for the lifetime of this process

# ── Academic dataset seed — runs once on first startup ────────────────────────
import logging as _logging
_seed_log = _logging.getLogger("teachwise.seed")

_db_uri = _flask_app.config.get("SQLALCHEMY_DATABASE_URI", "<not set>")
_seed_log.info("TeachWise startup: DATABASE_URI=%s", _db_uri)

try:
    from seed_academic import seed_academic_data as _seed_academic
    _seeded = _seed_academic()
    if _seeded:
        from app.models import Student as _Stu, SyllabusUnit as _SU
        from app.models import CourseOutcome as _CO, AttendanceRecord as _AR
        _seed_log.info(
            "TeachWise seed SUCCESS: students=%d  units=%d  COs=%d  attendance=%d",
            _Stu.query.count(), _SU.query.count(), _CO.query.count(), _AR.query.count(),
        )
    else:
        from app.models import Student as _Stu, AttendanceRecord as _AR
        _seed_log.info(
            "TeachWise seed SKIPPED (data present): students=%d  attendance=%d",
            _Stu.query.count(), _AR.query.count(),
        )
except Exception as _seed_exc:
    _seed_log.error(
        "TeachWise seed FAILED — analytics will be empty until resolved.",
        exc_info=True,
    )

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_flask_app():
    return _flask_app


def db_analytics(course_id: int) -> dict:
    from app.analytics import compute_full_analytics
    return compute_full_analytics(course_id)


def get_courses() -> list[dict]:
    from app.models import Course
    return [{'id': c.id, 'name': c.name, 'code': c.code,
             'semester': c.semester} for c in Course.query.all()]


def granite_available() -> bool:
    return bool(os.getenv('WATSONX_API_KEY') and os.getenv('WATSONX_PROJECT_ID'))


# ── Helper: page header ───────────────────────────────────────────────────────
def _page_header(title: str, subtitle: str = ""):
    granite_badge = ""
    if subtitle and "Granite" in subtitle:
        subtitle_clean = subtitle.replace("· IBM Granite", "").replace("· IBM Granite", "").strip()
        granite_badge = '<span class="tw-granite-badge">⬡ IBM Granite</span>'
    else:
        subtitle_clean = subtitle
        granite_badge = ""
    st.markdown(f"""
    <div class="tw-page-header">
      <h1>{title}</h1>
      <div class="tw-page-subtitle">{subtitle_clean}{granite_badge}</div>
    </div>
    """, unsafe_allow_html=True)


def _section(label: str):
    st.markdown(f'<div class="tw-section-label">{label}</div>', unsafe_allow_html=True)


def _advisory(msg: str):
    st.markdown(f'<div class="advisory-box">⚑ {msg}</div>', unsafe_allow_html=True)


def _gap_card(sev: str, title: str, meta: str, intervention: str = ""):
    css = "gap-critical" if sev == "Critical" else ("gap-significant" if sev == "Significant" else "gap-moderate")
    interv_html = f'<div class="gap-intervention">{intervention}</div>' if intervention else ""
    st.markdown(f"""
    <div class="{css}">
      <strong>{title}</strong>
      <div class="gap-meta">{meta}</div>
      {interv_html}
    </div>""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
NAV_ICONS = {
    "Overview":           "◈",
    "Lesson Studio":      "✦",
    "Teaching Materials": "▤",
    "Assessment Studio":  "◎",
    "Student Analytics":  "◉",
    "CO & Analytics":     "◐",
    "Learning Support":   "◑",
}

with st.sidebar:
    st.markdown("""
    <div class="tw-sidebar-brand">
      <div class="tw-sidebar-logo">Teach<span>Wise</span> AI</div>
      <div class="tw-sidebar-tagline">Faculty Intelligence Platform</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="tw-nav-label">Navigation</div>', unsafe_allow_html=True)

    page = st.radio(
        "Navigate",
        ["Overview", "Lesson Studio", "Teaching Materials",
         "Assessment Studio", "Student Analytics", "CO & Analytics",
         "Learning Support"],
        label_visibility="collapsed",
        format_func=lambda x: f"{NAV_ICONS.get(x, '·')}  {x}",
    )

    st.divider()

    st.markdown('<div class="tw-nav-label">AI Status</div>', unsafe_allow_html=True)
    if granite_available():
        st.markdown('<div style="padding:4px 20px"><span class="tw-status-ok">● IBM Granite · Connected</span></div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div style="padding:4px 20px"><span class="tw-status-err">● IBM Granite · No credentials</span></div>',
                    unsafe_allow_html=True)
        st.caption("Set WATSONX_API_KEY and WATSONX_PROJECT_ID in .env")

    st.divider()
    st.markdown("""
    <div style="padding:0 20px 20px; font-family:'Inter',sans-serif; font-size:0.7rem;
                color:#7A6050; letter-spacing:0.04em; line-height:1.6;">
      Plan Better.<br>Teach Smarter.<br>Support Every Learner.
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ════════════════════════════════════════════════════════════════════════════════
if page == "Overview":
    _page_header("Faculty Overview", "Live analytics from the CS201 academic dataset")

    courses = get_courses()
    cs201 = next((c for c in courses if c['code'] == 'CS201'), None)

    if cs201:
        try:
            analytics = db_analytics(cs201['id'])
            att = analytics['attendance']
            co  = analytics['co_attainment']
            at_risk = analytics['at_risk_students']
            tp  = analytics['topic_performance']

            # ── KPI row ───────────────────────────────────────────────────────
            _section("Key Indicators")
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("Students", att['total_students'])
            with c2:
                avg_att = att['class_avg_pct']
                st.metric("Avg Attendance",
                          f"{avg_att}%" if avg_att is not None else "N/A",
                          delta=f"{avg_att - 75:.1f}% vs 75% threshold" if avg_att is not None else None)
            with c3:
                overall_att = co['overall_attainment_pct']
                st.metric("CO Attainment",
                          f"{overall_att}%" if overall_att is not None else "N/A",
                          delta=f"{co['attained_count']}/{len(co['outcomes'])} COs attained")
            with c4:
                st.metric("At-Risk Students", len(at_risk),
                          delta=f"{att['below_75_count']} below 75% attendance",
                          delta_color="inverse")
            with c5:
                critical = sum(1 for t in tp if t['gap_severity'] == 'Critical')
                st.metric("Critical Gaps", critical)

            st.divider()

            # ── Topic performance chart ────────────────────────────────────────
            _section("Topic Performance — CS201")
            chart_df = pd.DataFrame([
                {'Topic': t['title'],
                 'Combined Avg %': t['combined_avg_pct'],
                 'Severity': t['gap_severity']}
                for t in tp if t['combined_avg_pct'] is not None
            ])
            if not chart_df.empty:
                st.bar_chart(
                    chart_df.set_index('Topic')['Combined Avg %'],
                    color="#D5851F",
                    use_container_width=True,
                    height=240,
                )
            else:
                st.caption("No topic performance data yet. Seed the academic dataset to view this chart.")

            st.divider()

            # ── CO + at-risk side by side ──────────────────────────────────────
            col_left, col_right = st.columns(2, gap="large")
            with col_left:
                _section("Course Outcome Attainment")
                co_rows_ov = [
                    {'CO': o['co_code'], 'Attainment %': o['attainment_pct'],
                     'Level': o['level_label']}
                    for o in co['outcomes']
                ]
                if co_rows_ov:
                    st.dataframe(pd.DataFrame(co_rows_ov),
                                 use_container_width=True, hide_index=True)
                else:
                    st.caption("No CO attainment data available yet.")

            with col_right:
                _section("At-Risk Students (top 10)")
                if at_risk:
                    risk_df = pd.DataFrame([
                        {'Student': s['student_code'],
                         'Attendance %': s['attendance_pct'],
                         'Avg Score %': s['avg_score_pct'],
                         'Priority': s['priority']}
                        for s in at_risk[:10]
                    ])
                    st.dataframe(risk_df, use_container_width=True, hide_index=True)
                else:
                    st.success("No at-risk students detected.")

        except Exception as exc:
            st.error(f"Analytics error: {exc}")
    else:
        st.warning("CS201 course not found. Run `python seed_academic.py` first.")

    st.divider()
    _section("All Courses")
    if courses:
        st.dataframe(pd.DataFrame(courses)[['code', 'name', 'semester']],
                     use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: LESSON STUDIO
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Lesson Studio":
    _page_header("Lesson Studio",
                 "Generate structured lesson plans aligned with course outcomes · IBM Granite")

    if not granite_available():
        st.error("IBM Granite credentials not set. Add WATSONX_API_KEY and WATSONX_PROJECT_ID to .env")
        st.stop()

    with st.form("lesson_form"):
        col1, col2 = st.columns(2, gap="large")
        with col1:
            subject  = st.text_input("Subject / Course", value="Data Structures & Algorithms")
            topic    = st.text_input("Topic", value="Binary Search Trees")
            duration = st.selectbox("Duration", ["45 minutes", "60 minutes", "90 minutes", "120 minutes"])
        with col2:
            level    = st.selectbox("Student Level", ["Undergraduate", "Postgraduate", "Diploma"])
            outcomes = st.text_area("Course Outcomes",
                value="CO4: Construct and traverse tree data structures for hierarchical data.",
                height=80)
            approach = st.text_input("Teaching Approach", value="Interactive lecture with coding examples")

        submitted = st.form_submit_button("Generate Lesson Plan", use_container_width=True, type="primary")

    if submitted:
        if not subject.strip() or not topic.strip():
            st.error("Subject and Topic are required.")
        elif len(topic) > 200:
            st.error("Topic exceeds 200 characters.")
        else:
            with st.spinner("Generating lesson plan with IBM Granite..."):
                try:
                    from app.agents.lesson_planning import generate_lesson_plan
                    plan = generate_lesson_plan(subject, topic, outcomes, duration, level, approach)
                    st.session_state['lesson_plan'] = plan
                    st.session_state['lesson_approved'] = False
                except Exception as exc:
                    st.error(f"Granite unavailable: {exc}")

    if 'lesson_plan' in st.session_state:
        st.divider()
        _section("Generated Lesson Plan")
        st.markdown(st.session_state['lesson_plan'])

        if not st.session_state.get('lesson_approved'):
            _advisory("These recommendations are AI-generated. Review before use in class.")
            if st.button("Approve Lesson Plan", type="primary"):
                st.session_state['lesson_approved'] = True
                st.success("Lesson plan approved by faculty.")
                st.rerun()
        else:
            st.success("Approved by faculty.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: TEACHING MATERIALS
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Teaching Materials":
    _page_header("Teaching Materials",
                 "Generate lecture notes, worked examples, case studies and exercises · IBM Granite")

    if not granite_available():
        st.error("IBM Granite credentials not set.")
        st.stop()

    with st.form("material_form"):
        col1, col2 = st.columns(2, gap="large")
        with col1:
            course_name = st.text_input("Course", value="Data Structures & Algorithms")
            topic       = st.text_input("Topic", value="Graph Traversal: BFS and DFS")
            difficulty  = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        with col2:
            mat_type = st.selectbox("Material Type", [
                ("Lecture Notes",         "lecture_notes"),
                ("Worked Examples",       "examples"),
                ("Case Study",            "case_study"),
                ("Practice Exercises",    "exercises"),
                ("Discussion Questions",  "discussion"),
            ], format_func=lambda x: x[0])

        submitted = st.form_submit_button("Generate Material", use_container_width=True, type="primary")

    if submitted:
        if not topic.strip():
            st.error("Topic is required.")
        else:
            with st.spinner(f"Generating {mat_type[0]} with IBM Granite..."):
                try:
                    from app.agents.teaching_material import generate_material
                    content = generate_material(course_name, topic, difficulty, mat_type[1])
                    st.session_state['material'] = content
                    st.session_state['material_approved'] = False
                except Exception as exc:
                    st.error(f"Granite unavailable: {exc}")

    if 'material' in st.session_state:
        st.divider()
        _section("Generated Material")
        st.markdown(st.session_state['material'])
        if not st.session_state.get('material_approved'):
            _advisory("AI-generated content. Review for accuracy before use.")
            if st.button("Approve Material", type="primary"):
                st.session_state['material_approved'] = True
                st.success("Material approved.")
                st.rerun()
        else:
            st.success("Approved by faculty.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: ASSESSMENT STUDIO
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Assessment Studio":
    _page_header("Assessment Studio",
                 "Generate MCQs, short-answer and coding questions with answer keys · IBM Granite")

    if not granite_available():
        st.error("IBM Granite credentials not set.")
        st.stop()

    with st.form("assess_form"):
        col1, col2 = st.columns(2, gap="large")
        with col1:
            topic      = st.text_input("Topic", value="Linked Lists")
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
            num_q      = st.slider("Number of Questions", 2, 10, 4)
        with col2:
            q_types = st.multiselect("Question Types",
                ["MCQ", "Short", "Long", "Coding"],
                default=["MCQ", "Short"])
            co = st.text_input("Course Outcome (optional)",
                value="CO2: Implement and analyse linked list operations")

        show_answers = st.checkbox("Show answer key", value=True)
        submitted = st.form_submit_button("Generate Assessment", use_container_width=True, type="primary")

    if submitted:
        if not topic.strip():
            st.error("Topic is required.")
        elif not q_types:
            st.error("Select at least one question type.")
        else:
            with st.spinner("Generating assessment with IBM Granite..."):
                try:
                    from app.agents.assessment import generate_assessment
                    result = generate_assessment(topic, difficulty, q_types, num_q, co)
                    st.session_state['assessment'] = result
                    st.session_state['assess_approved'] = False
                except Exception as exc:
                    st.error(f"Granite unavailable: {exc}")

    if 'assessment' in st.session_state:
        result = st.session_state['assessment']
        st.divider()

        if result.get('error') and not result.get('questions'):
            st.error(f"Assessment parse error: {result['error']}")
        else:
            questions = result.get('questions', [])
            _section(f"{result.get('topic', topic)} — {result.get('difficulty', difficulty)}")
            st.caption(f"{len(questions)} questions · Total marks: {result.get('total_marks', 'N/A')}")

            for i, q in enumerate(questions, 1):
                with st.expander(
                    f"Q{i}.  [{q.get('type','')} · {q.get('marks','')} marks]  "
                    f"{q.get('question','')[:90]}…"
                ):
                    st.markdown(f"**{q.get('question', '')}**")
                    if q.get('options'):
                        for opt in q['options']:
                            st.markdown(f"&nbsp;&nbsp;&nbsp;{opt}")
                    if show_answers:
                        ans = q.get('answer') or q.get('correct_answer', '')
                        exp = q.get('explanation', '')
                        if ans:
                            st.success(f"Answer: {ans}")
                        if exp:
                            st.info(f"Explanation: {exp}")

            if not st.session_state.get('assess_approved'):
                _advisory("AI-generated. Verify technical accuracy before use.")
                if st.button("Approve Assessment", type="primary"):
                    st.session_state['assess_approved'] = True
                    st.success("Assessment approved by faculty.")
                    st.rerun()
            else:
                st.success("Approved by faculty.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: STUDENT ANALYTICS (CSV Pipeline)
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Student Analytics":
    _page_header("Student Analytics",
                 "Upload student CSV → 6-stage pipeline → Granite interpretation + gap detection")

    # Demo CSV download
    demo_path = os.path.join(os.path.dirname(__file__), 'data', 'demo_students.csv')
    if os.path.exists(demo_path):
        with open(demo_path, 'rb') as f:
            st.download_button("↓ Download Demo CSV", f.read(), "demo_students.csv",
                               mime="text/csv",
                               help="40-student synthetic dataset — required columns: student_id, attendance_pct")

    uploaded    = st.file_uploader("Upload student CSV", type=["csv"])
    course_name = st.text_input("Course Name", value="Data Structures & Algorithms", max_chars=200)

    if uploaded and st.button("Run Analysis Pipeline", type="primary"):
        try:
            df = pd.read_csv(uploaded)
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")
            st.stop()

        from app.pipeline import run_analysis_pipeline
        from app.agents.performance_analysis import validate_csv

        is_valid, err, warnings = validate_csv(df)
        if not is_valid:
            st.error(f"Validation failed: {err}")
            st.stop()
        if warnings:
            for w in warnings:
                st.warning(w)

        progress = st.progress(0, text="Stage 1/6: Validating data…")
        result = {}

        with st.spinner("Running 6-stage analysis pipeline…"):
            try:
                result = run_analysis_pipeline(df, course_name)
            except Exception as exc:
                st.error(f"Pipeline error: {exc}")
                st.stop()

        progress.progress(100, text="Pipeline complete")

        if result.get('error'):
            st.error(result['error'])
            st.stop()

        st.session_state['pipeline_result'] = result

    if 'pipeline_result' in st.session_state:
        result    = st.session_state['pipeline_result']
        perf      = result.get('performance') or {}
        gaps      = result.get('gaps') or []
        stage_log = result.get('stage_log') or []
        support   = result.get('support_plan') or {}

        # Stage log
        with st.expander("Pipeline Stage Log", expanded=True):
            for s in stage_log:
                if s['status'] == 'success':
                    icon, css = "✓", "stage-ok"
                elif s['status'] == 'failed':
                    icon, css = "✗", "stage-err"
                else:
                    icon, css = "⏳", "stage-run"
                msg = s.get('message') or s.get('error') or ''
                st.markdown(f'<div class="{css}">{icon} &nbsp;<strong>{s["stage"]}</strong> — {msg}</div>',
                            unsafe_allow_html=True)

        st.divider()

        # KPI row
        _section("Pipeline Results")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Students",      perf.get('num_students', 0))
        c2.metric("Avg Attendance", f"{perf.get('avg_attendance', 0)}%")
        c3.metric("Avg Score",     f"{perf.get('overall_avg_score', 0)}%")
        c4.metric("At-Risk",       len(perf.get('at_risk_students', [])))

        # Topic chart
        topic_stats = perf.get('topic_stats', {})
        if topic_stats:
            _section("Topic Performance")
            ts_df = pd.DataFrame([
                {'Topic': k.replace('quiz_', '').replace('_', ' ').title(),
                 'Mean %': v['mean'], 'Below 50%': v['below_50_pct']}
                for k, v in topic_stats.items()
            ])
            st.bar_chart(ts_df.set_index('Topic')['Mean %'],
                         color="#D5851F", height=220, use_container_width=True)

        # Gaps
        if gaps:
            _section(f"Learning Gaps Detected ({len(gaps)})")
            for g in gaps:
                sev = g.get('severity', '')
                meta = f"{sev} · {g['mean_score']}% avg · {g['below_50_pct']}% failing"
                _gap_card(sev, g['topic'], meta,
                          g.get('intervention') or g.get('priority_action') or '')

        # AI interpretation
        ai_interp = result.get('ai_interpretation')
        if ai_interp:
            with st.expander("⬡ Granite Performance Interpretation"):
                st.markdown(ai_interp)

        # Support plan
        if support and support.get('executive_summary'):
            _section("Learning Support Plan")
            st.info(support['executive_summary'])
            plans = support.get('topic_support_plans', [])
            if plans:
                for p in plans:
                    with st.expander(f"{p.get('topic', '')} — {p.get('severity', '')}"):
                        st.markdown(f"**Strategy:** {p.get('revision_strategy', '')}")
                        for act in p.get('practice_activities', []):
                            st.markdown(f"- {act}")
            _advisory("These recommendations are advisory. Faculty should review before sharing with students.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: CO & ANALYTICS
# ════════════════════════════════════════════════════════════════════════════════
elif page == "CO & Analytics":
    _page_header("CO & Analytics",
                 "DB-computed CO attainment, topic performance and attendance — CS201 (45 students)")

    if not granite_available():
        st.warning("Granite credentials not set — AI pipeline will not run. Analytics still available.")

    courses = get_courses()
    course_options = {f"{c['code']} — {c['name']}": c['id'] for c in courses}
    selected   = st.selectbox("Course", list(course_options.keys()))
    course_id  = course_options[selected]

    try:
        analytics = db_analytics(course_id)
    except Exception as exc:
        st.error(f"Analytics error: {exc}")
        st.stop()

    tp       = analytics['topic_performance']
    co       = analytics['co_attainment']
    att      = analytics['attendance']
    at_risk  = analytics['at_risk_students']

    # KPI row
    _section("Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Students", att['total_students'])
    _avg_att = att['class_avg_pct']
    c2.metric("Avg Attendance", f"{_avg_att}%" if _avg_att is not None else "N/A")
    _co_att = co['overall_attainment_pct']
    c3.metric("CO Attainment", f"{_co_att}%" if _co_att is not None else "N/A")
    c4.metric("At-Risk", len(at_risk))

    st.divider()
    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        _section("Topic Performance")
        if tp:
            tp_df = pd.DataFrame([{
                'Topic': t['title'],
                'Quiz Avg %': t['quiz_avg_pct'],
                'Assign Avg %': t['assignment_avg_pct'],
                'Combined %': t['combined_avg_pct'],
                'Severity': t['gap_severity'],
            } for t in tp])
            st.dataframe(tp_df, use_container_width=True, hide_index=True)
            tp_chart = tp_df[tp_df['Combined %'].notna()].set_index('Topic')['Combined %']
            if not tp_chart.empty:
                st.bar_chart(tp_chart, color="#D5851F", height=200, use_container_width=True)

    with col_right:
        _section("Course Outcome Attainment")
        co_rows = [{
            'CO': o['co_code'],
            'Bloom': o['bloom_level'],
            'Attainment %': o['attainment_pct'],
            'Level': o['level_label'],
        } for o in co['outcomes']]
        if co_rows:
            co_df = pd.DataFrame(co_rows)
            st.dataframe(co_df, use_container_width=True, hide_index=True)
            co_chart = co_df[co_df['Attainment %'].notna()].set_index('CO')['Attainment %']
            if not co_chart.empty:
                st.bar_chart(co_chart, color="#A88462", height=200, use_container_width=True)
        else:
            st.caption("No CO attainment data available.")

    # Attendance distribution
    _section("Attendance Distribution")
    dist = att.get('distribution', {})
    if dist:
        band_labels = {
            'below_60': '< 60%',
            '60_to_75': '60–75%',
            '75_to_90': '75–90%',
            'above_90': '> 90%',
        }
        dist_df = pd.DataFrame([
            {'Band': band_labels.get(k, k), 'Students': v}
            for k, v in dist.items()
        ])
        st.bar_chart(dist_df.set_index('Band'), color="#87A968", height=180, use_container_width=True)

    # At-risk table
    if at_risk:
        _section(f"At-Risk Students ({len(at_risk)})")
        st.caption("Criteria: attendance < 60% OR avg score < 50%. Review individually before action.")
        risk_df = pd.DataFrame([{
            'Student': s['student_code'],
            'Section': s['section'] or '',
            'Attendance %': s['attendance_pct'],
            'Avg Score %': s['avg_score_pct'],
            'Priority': s['priority'],
        } for s in at_risk])
        st.dataframe(risk_df, use_container_width=True, hide_index=True)

    # AI Pipeline
    st.divider()
    if granite_available():
        _section("AI Pipeline")
        st.caption("Runs gap detection, Granite interventions, support plan and CO interpretation")
        if st.button("Run Full AI Pipeline", type="primary"):
            with st.spinner("Running 6-stage AI pipeline… (may take 30–60 s)"):
                try:
                    from app.analytics import (compute_topic_performance,
                        compute_at_risk_students, compute_attendance_summary,
                        compute_co_attainment)
                    from app.agents.gap_detection import detect_gaps, ai_explain_gaps
                    from app.agents.learning_support import generate_support_plan
                    from app.agents.co_attainment import interpret_co_attainment

                    t_perf       = compute_topic_performance(course_id)
                    att_sum      = compute_attendance_summary(course_id)
                    at_risk_list = compute_at_risk_students(course_id)
                    topic_stats  = {
                        t['title']: {'mean': t['combined_avg_pct'], 'below_50_pct': 0,
                                     'below_40_pct': 0, 'median': t['combined_avg_pct'], 'std': 0}
                        for t in t_perf if t.get('combined_avg_pct') is not None
                    }
                    gaps = detect_gaps(topic_stats)
                    gaps = ai_explain_gaps(gaps, att_sum.get('total_students', 0))

                    overall_avg = (sum(t['combined_avg_pct'] for t in t_perf if t.get('combined_avg_pct') is not None)
                                   / max(1, sum(1 for t in t_perf if t.get('combined_avg_pct') is not None)))
                    perf_for_support = {
                        'num_students': att_sum.get('total_students', 0),
                        'avg_attendance': att_sum.get('class_avg_pct'),
                        'overall_avg_score': round(overall_avg, 1),
                        'at_risk_students': at_risk_list,
                    }
                    support_plan = generate_support_plan(
                        perf_for_support, gaps, selected.split('—')[-1].strip())

                    co_att   = compute_co_attainment(course_id)
                    co_interp = interpret_co_attainment(co_att, selected.split('—')[-1].strip())

                    st.session_state['ai_pipeline'] = {
                        'gaps': gaps, 'support_plan': support_plan,
                        'co_interp': co_interp,
                    }
                except Exception as exc:
                    st.error(f"Pipeline error: {exc}")

        if 'ai_pipeline' in st.session_state:
            pipeline  = st.session_state['ai_pipeline']
            gaps      = pipeline.get('gaps', [])
            sp        = pipeline.get('support_plan', {})
            co_interp = pipeline.get('co_interp', '')

            if gaps:
                _section("Detected Gaps")
                for g in gaps:
                    sev  = g.get('severity', '')
                    meta = f"{sev} · {g['mean_score']}%"
                    _gap_card(sev, g['topic'], meta, g.get('intervention', ''))

            if sp and sp.get('executive_summary'):
                _section("Learning Support Plan")
                st.info(sp['executive_summary'])
                for p in sp.get('topic_support_plans', []):
                    with st.expander(f"{p.get('topic', '')} — {p.get('severity', '')}"):
                        st.write(p.get('revision_strategy', ''))
                        for act in p.get('practice_activities', []):
                            st.markdown(f"- {act}")

            if co_interp:
                with st.expander("⬡ Granite CO Attainment Interpretation"):
                    st.markdown(co_interp)

            _advisory("All recommendations are advisory. Faculty approval required before action.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE: LEARNING SUPPORT
# ════════════════════════════════════════════════════════════════════════════════
elif page == "Learning Support":
    _page_header("Learning Support",
                 "Gap-matched resources and at-risk student support — CS201")

    courses = get_courses()
    cs201   = next((c for c in courses if c['code'] == 'CS201'), None)
    if not cs201:
        st.warning("CS201 not found. Run seed_academic.py first.")
        st.stop()

    # App context already active at module level
    from app.analytics import compute_topic_performance, compute_at_risk_students
    from app.models import LearningResource

    tp       = compute_topic_performance(cs201['id'])
    at_risk  = compute_at_risk_students(cs201['id'])
    weak     = [t for t in tp if t['gap_severity'] in ('Critical', 'Significant', 'Moderate')]

    # Fetch resources for weak units
    weak_resources = {}
    for t in weak:
        res = LearningResource.query.filter_by(
            course_id=cs201['id'], unit_id=t['unit_id']).all()
        weak_resources[t['unit_id']] = {
            'title': t['title'], 'severity': t['gap_severity'],
            'score': t['combined_avg_pct'],
            'resources': [{'title': r.title, 'type': r.resource_type, 'url': r.url_or_path}
                          for r in res],
        }

    # KPI row
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Topics",    len(tp))
    c2.metric("Topics Needing Attention", len(weak))
    c3.metric("At-Risk Students", len(at_risk))

    if weak:
        st.divider()
        _section("Topics Requiring Attention")
        for t in weak:
            sev   = t['gap_severity']
            info  = weak_resources.get(t['unit_id'], {})
            score = t.get('combined_avg_pct')
            label = f"Unit {t['unit_number']}: {t['title']}  ·  {sev}  ·  {score}% combined avg"

            with st.expander(label):
                sev_color = "#C0392B" if sev == "Critical" else ("#9A5F0F" if sev == "Significant" else "#6B5C4A")
                st.markdown(
                    f"<span style='color:{sev_color};font-weight:700;font-size:0.85rem;'>"
                    f"{'⬛' if sev=='Critical' else ('◈' if sev=='Significant' else '◉')} {sev}</span>"
                    f"&nbsp;&nbsp;Combined avg: <strong>{score}%</strong>",
                    unsafe_allow_html=True
                )
                resources = info.get('resources', [])
                if resources:
                    st.markdown(
                        "<div style='font-family:Inter,sans-serif;font-size:0.78rem;"
                        "font-weight:700;color:#9C8A72;text-transform:uppercase;"
                        "letter-spacing:0.08em;margin:12px 0 8px;'>Recommended Resources</div>",
                        unsafe_allow_html=True
                    )
                    type_icons = {"video": "▶", "link": "⬡", "textbook": "◈", "pdf": "◉"}
                    for r in resources:
                        icon   = type_icons.get(r['type'], "·")
                        rtype  = r['type'].upper()
                        if r['url']:
                            st.markdown(
                                f'<a class="res-row" href="{r["url"]}" target="_blank">'
                                f'<span style="font-size:1rem">{icon}</span>'
                                f'<span style="flex:1">{r["title"]}</span>'
                                f'<span class="res-type">{rtype}</span></a>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(
                                f'<div class="res-row">'
                                f'<span style="font-size:1rem">{icon}</span>'
                                f'<span style="flex:1">{r["title"]}</span>'
                                f'<span class="res-type">{rtype}</span></div>',
                                unsafe_allow_html=True
                            )
                else:
                    st.caption("No resources linked for this topic.")

    if at_risk:
        st.divider()
        _section(f"At-Risk Students ({len(at_risk)})")
        st.caption("Criteria: attendance < 60% OR avg score < 50%")
        risk_df = pd.DataFrame([{
            'Student': s['student_code'],
            'Attendance %': s['attendance_pct'],
            'Avg Score %': s['avg_score_pct'],
            'Priority': s['priority'],
        } for s in at_risk])
        st.dataframe(risk_df, use_container_width=True, hide_index=True)

    _advisory("Faculty should review each at-risk student individually before intervention.")
