"""
Shared CSS for GreenPulse Admin panel.
Call inject_styles() at the top of every page (after set_page_config).
"""
import streamlit as st

_CSS = """
<style>
/* ── Fonts & base ─────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Sidebar branding ─────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #064e3b 0%, #065f46 100%);
}
[data-testid="stSidebar"] * { color: #d1fae5 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.1) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.2) !important;
}

/* ── Primary buttons ──────────────────────────────────────────────────────── */
[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"],
[data-testid="stMainBlockContainer"] .stButton > button[data-testid="baseButton-primary"] {
    background: #10b981 !important;
    border: none !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
[data-testid="stMainBlockContainer"] .stButton > button[kind="primary"]:hover {
    background: #059669 !important;
}

/* ── Spinner — replace with branded animation ─────────────────────────────── */
@keyframes gp-spin {
    0%   { transform: rotate(0deg);   }
    100% { transform: rotate(360deg); }
}
@keyframes gp-ripple {
    0%   { transform: scale(0.8); opacity: 0.7; }
    100% { transform: scale(2.0); opacity: 0;   }
}
@keyframes gp-dot {
    0%, 80%, 100% { transform: translateY(0);   opacity: 0.4; }
    40%           { transform: translateY(-6px); opacity: 1;   }
}

/* Hide the default Streamlit spinner SVG */
[data-testid="stSpinner"] > div > svg { display: none !important; }

/* Inject our own spinner before the text */
[data-testid="stSpinner"] > div {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    gap: 12px !important;
    padding: 24px !important;
}
[data-testid="stSpinner"] > div::before {
    content: '';
    display: block;
    width: 48px;
    height: 48px;
    border: 3px solid #d1fae5;
    border-top-color: #10b981;
    border-radius: 50%;
    animation: gp-spin 0.8s linear infinite;
}
[data-testid="stSpinner"] > div > p {
    color: #065f46 !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
}

/* ── Metric cards ─────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #f0fdf4;
    border: 1px solid #a7f3d0;
    border-radius: 12px;
    padding: 1rem 1.25rem;
}
[data-testid="stMetricValue"] { color: #065f46 !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #6b7280 !important; }

/* ── Tabs ─────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab"] { border-radius: 8px 8px 0 0; }
[data-testid="stTabs"] [aria-selected="true"] {
    color: #10b981 !important;
    border-bottom-color: #10b981 !important;
}

/* ── Code blocks ──────────────────────────────────────────────────────────── */
[data-testid="stCodeBlock"] { border-radius: 10px !important; }

/* ── Top progress bar on page load ───────────────────────────────────────── */
@keyframes gp-progress {
    0%  { left: -35%; width: 35%; }
    60% { left: 100%; width: 35%; }
    100%{ left: 100%; width: 0;   }
}
body::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 3px;
    z-index: 99999;
    background: #10b981;
    animation: gp-progress 1.2s cubic-bezier(0.4,0,0.2,1) 1 forwards;
}
</style>
"""


def inject_styles():
    """Call once per page, right after st.set_page_config()."""
    st.markdown(_CSS, unsafe_allow_html=True)
