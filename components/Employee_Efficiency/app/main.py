"""Enterprise Service Operations Performance Intelligence Platform
Streamlit Application for Employee Efficiency and Monitoring AI Agent.
SLIIT Data Science Research Component: J26-DS-351 | IT23366268
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import altair as alt
import pandas as pd
import streamlit as st

from src.config import RAW_DIR
from src.database.models import init_db
from src.schemas.kpi import ROLE_LABELS, ROLE_KPIS, Role
from src.services import review
from src.services.data_access import available_periods, load_bundle
from src.services.evaluation import evaluate, evaluate_recovery_case
from src.services.llm_narrator import (
    CAUSE_LABELS,
    CATEGORY_LABELS,
    evidence_strength,
    narrate,
    team_narrative,
)
from src.services.trajectory import determine_phase
from src.services.preprocessing.pipeline import run_preprocessing
from src.workflow.graph import run_assessment, run_team
from app.ui_theme import get_brand_header_html

# ------------------------------------------------------------------------------
# THEME CONFIGURATION & DESIGN SYSTEM
# ------------------------------------------------------------------------------
def get_theme_css() -> str:
    """Generate the fixed light Metropolitan theme CSS."""
    canvas = "#f8fafc"
    surface = "#ffffff"
    surface_card = "#ffffff"
    surface_subtle = "#f1f5f9"
    surface_hover = "#f8fafc"
    border_subtle = "#e2e8f0"
    border_strong = "#cbd5e1"
    border_accent = "rgba(37, 99, 235, 0.35)"
    ink_primary = "#0f172a"
    ink_secondary = "#334155"
    ink_tertiary = "#64748b"
    ink_muted = "#94a3b8"
    brand_primary = "#2563eb"
    brand_secondary = "#db0d1b"
    brand_glow = "rgba(37, 99, 235, 0.16)"
    brand_gradient = "#2563eb"
    sidebar_bg = "#0f172a"
    sidebar_surface = "#1e293b"
    sidebar_border = "#1e293b"
    card_shadow = "0 1px 2px rgba(15, 23, 42, 0.04)"
    card_shadow_hover = "0 1px 3px rgba(15, 23, 42, 0.08)"
    card_bg = "#ffffff"
    card_border = "#e2e8f0"
    exec_card_bg = "#ffffff"
    chip_bg = "#f1f5f9"
    chip_border = "#e2e8f0"
    input_bg = "#f8fafc"
    input_border = "#cbd5e1"

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Manrope:wght@500;600;700;800&family=JetBrains+Mono:wght@500;600&display=swap');

    :root {{
        --canvas: {canvas};
        --surface: {surface};
        --surface-card: {surface_card};
        --surface-subtle: {surface_subtle};
        --surface-hover: {surface_hover};
        --border-subtle: {border_subtle};
        --border-strong: {border_strong};
        --border-accent: {border_accent};
        --ink-primary: {ink_primary};
        --ink-secondary: {ink_secondary};
        --ink-tertiary: {ink_tertiary};
        --ink-muted: {ink_muted};
        --brand-primary: {brand_primary};
        --brand-secondary: {brand_secondary};
        --brand-glow: {brand_glow};
        --brand-gradient: {brand_gradient};
        --sidebar-bg: {sidebar_bg};
        --sidebar-surface: {sidebar_surface};
        --sidebar-border: {sidebar_border};
        --card-shadow: {card_shadow};
        --card-shadow-hover: {card_shadow_hover};
        --card-bg: {card_bg};
        --card-border: {card_border};
        --exec-card-bg: {exec_card_bg};
        --chip-bg: {chip_bg};
        --chip-border: {chip_border};
        --input-bg: {input_bg};
        --input-border: {input_border};
        --accent-emerald: #10b981;
        --accent-amber: #f59e0b;
        --accent-rose: #f43f5e;
        --accent-indigo: #6366f1;
    }}

    html, body, [class*="css"], .stApp {{
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        background-color: var(--canvas) !important;
        color: var(--ink-primary) !important;
    }}

    [data-testid="stHeader"] {{
        background: transparent !important;
    }}

    [data-testid="stMainBlockContainer"] {{
        width: 100%;
        max-width: none;
        padding-top: 1.5rem;
        padding-bottom: 4rem;
    }}

    /* Global Typography overrides */
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Manrope', sans-serif !important;
        color: var(--ink-primary) !important;
        letter-spacing: -0.025em !important;
    }}

    p, span, label, div {{
        color: var(--ink-primary);
    }}

    /* Top Utility Status Bar */
    .top-system-strip {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        padding: 0.6rem 1rem;
        background: var(--surface-card);
        border: 1px solid var(--border-subtle);
        border-radius: 0.75rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--card-shadow);
    }}

    .strip-badges {{
        display: flex;
        align-items: center;
        gap: 0.6rem;
        flex-wrap: wrap;
    }}

    .strip-pill {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.74rem;
        font-weight: 600;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        background: var(--surface-subtle);
        border: 1px solid var(--border-subtle);
        color: var(--ink-secondary);
    }}

    .strip-pill-active {{
        background: rgba(37, 99, 235, 0.12);
        color: var(--brand-primary);
        border-color: var(--brand-primary);
    }}

    /* Sidebar Customization */
    [data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid var(--sidebar-border) !important;
    }}

    [data-testid="stSidebar"] > div:first-child {{
        padding: 1.3rem 1.1rem 2rem;
    }}

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {{
        color: #cbd5e1 !important;
    }}

    .brand-header {{
        display: flex;
        flex-direction: column;
        gap: 0.85rem;
        padding: 0.2rem 0.1rem 1.25rem;
        border-bottom: 1px solid var(--sidebar-border);
        margin-bottom: 1.15rem;
    }}

    .brand-logo-card {{
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0.35rem 0.65rem;
        border-radius: 0.75rem;
        background: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.12);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
    }}

    .brand-logo-img {{
        display: block;
        width: 100%;
        max-width: 13rem;
        max-height: 4rem;
        object-fit: contain;
    }}

    .brand-details {{
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }}

    .brand-title {{
        color: #f8fafc !important;
        font: 800 1.02rem 'Manrope', sans-serif;
        letter-spacing: -0.025em;
        line-height: 1.2;
    }}

    .brand-subtitle {{
        color: #94a3b8 !important;
        font-size: 0.74rem;
        margin-top: 0.15rem;
        font-weight: 500;
    }}

    .brand-tags-row {{
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
        margin-top: 0.35rem;
    }}

    .brand-tag-blue,
    .brand-tag-red {{
        display: inline-block;
        font-size: 0.63rem;
        font-weight: 700;
        padding: 0.18rem 0.5rem;
        border-radius: 0.35rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }}

    .brand-tag-blue {{
        background: rgba(37, 99, 235, 0.12);
        color: var(--brand-primary);
        border: 1px solid var(--brand-primary);
    }}

    .brand-tag-red {{
        background: rgba(219, 13, 27, 0.12);
        color: var(--brand-secondary);
        border: 1px solid var(--brand-secondary);
    }}

    /* Sidebar Navigation Radios */
    [data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {{
        gap: 0.35rem;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label {{
        min-height: 2.65rem;
        padding: 0.55rem 0.85rem;
        border-radius: 0.65rem;
        border: 1px solid transparent;
        background: transparent;
        color: #94a3b8 !important;
        font-weight: 500;
        font-size: 0.88rem;
        transition: all 150ms ease;
        display: flex;
        align-items: center;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
        background: var(--sidebar-surface);
        color: #f8fafc !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
        background: var(--sidebar-surface);
        border-color: var(--brand-primary);
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {{
        color: #ffffff !important;
        font-weight: 700;
    }}

    /* Sidebar Status Card */
    .sidebar-status-card {{
        margin-top: 1.5rem;
        padding: 1rem;
        border: 1px solid var(--sidebar-border);
        border-radius: 0.85rem;
        background: var(--sidebar-surface);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }}

    .sidebar-status-kicker {{
        color: var(--brand-primary);
        font-size: 0.66rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }}

    .sidebar-status-val {{
        margin-top: 0.35rem;
        color: #f8fafc;
        font: 700 0.95rem 'Manrope', sans-serif;
    }}

    .sidebar-status-sub {{
        margin-top: 0.2rem;
        color: #94a3b8;
        font-size: 0.75rem;
    }}

    /* Page Header */
    .page-kicker {{
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        margin-bottom: 0.35rem;
        color: var(--brand-primary);
        font-size: 0.74rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }}

    .kicker-dot {{
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: var(--brand-primary);
        box-shadow: 0 0 8px var(--brand-primary);
    }}

    .page-title {{
        font: 800 clamp(1.75rem, 2.6vw, 2.25rem) 'Manrope', sans-serif !important;
        color: var(--ink-primary) !important;
        letter-spacing: -0.035em !important;
        line-height: 1.2;
        margin: 0 0 0.45rem 0 !important;
    }}

    .page-desc {{
        color: var(--ink-secondary) !important;
        font-size: 0.94rem;
        line-height: 1.55;
        margin-bottom: 1.45rem;
        max-width: 950px;
    }}

    /* Executive Synthesis Card (Flagship AI Element) */
    .exec-synthesis-card {{
        background: var(--exec-card-bg);
        border: 1px solid var(--card-border);
        border-left: 5px solid var(--brand-primary);
        border-radius: 0.95rem;
        padding: 1.45rem 1.6rem;
        box-shadow: var(--card-shadow);
        margin-bottom: 1.8rem;
        position: relative;
        overflow: hidden;
    }}

    .exec-synthesis-card::before {{
        content: "";
        position: absolute;
        top: 0;
        right: 0;
        width: 140px;
        height: 140px;
        background: radial-gradient(circle, var(--brand-glow) 0%, transparent 70%);
        pointer-events: none;
    }}

    .exec-synthesis-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.85rem;
        flex-wrap: wrap;
        gap: 0.5rem;
    }}

    .exec-synthesis-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        background: rgba(37, 99, 235, 0.12);
        color: var(--brand-primary);
        border: 1px solid var(--brand-primary);
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 0.28rem 0.75rem;
        border-radius: 9999px;
    }}

    @keyframes pulseGlow {{
        0% {{ transform: scale(0.92); opacity: 0.8; box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.7); }}
        70% {{ transform: scale(1.08); opacity: 1; box-shadow: 0 0 0 7px rgba(37, 99, 235, 0); }}
        100% {{ transform: scale(0.92); opacity: 0.8; box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }}
    }}

    .pulse-dot {{
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: var(--brand-primary);
        animation: pulseGlow 2s infinite;
    }}

    .exec-synthesis-text {{
        font-size: 0.98rem;
        line-height: 1.72;
        color: var(--ink-primary);
        font-weight: 450;
    }}

    /* Modern Employee Profile Ribbon */
    .emp-profile-ribbon {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.35rem;
        background: var(--card-bg);
        padding: 0.85rem 1.25rem;
        border-radius: 0.85rem;
        border: 1px solid var(--card-border);
        box-shadow: var(--card-shadow);
    }}

    .emp-avatar-badge {{
        display: grid;
        place-items: center;
        width: 2.3rem;
        height: 2.3rem;
        border-radius: 0.65rem;
        background: var(--brand-gradient);
        color: white;
        font: 700 0.88rem 'Manrope', sans-serif;
    }}

    .emp-code-title {{
        font: 700 1.05rem 'Manrope', sans-serif;
        color: var(--ink-primary);
    }}

    .emp-tag {{
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        background: var(--surface-subtle);
        border: 1px solid var(--border-subtle);
        padding: 0.25rem 0.65rem;
        border-radius: 0.45rem;
        font-size: 0.78rem;
        font-weight: 600;
        color: var(--ink-secondary);
    }}

    /* Semantic Status Badges */
    .badge-ontrack {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: rgba(16, 185, 129, 0.12);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.35);
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.25rem 0.65rem;
        border-radius: 0.45rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    .badge-deviating {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: rgba(244, 63, 94, 0.12);
        color: #f43f5e;
        border: 1px solid rgba(244, 63, 94, 0.35);
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.25rem 0.65rem;
        border-radius: 0.45rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    .badge-context {{
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: rgba(37, 99, 235, 0.12);
        color: var(--brand-primary);
        border: 1px solid var(--brand-primary);
        font-size: 0.75rem;
        font-weight: 700;
        padding: 0.25rem 0.65rem;
        border-radius: 0.45rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    /* Metric Cards Enhancement */
    [data-testid="stMetric"] {{
        padding: 1.15rem 1.25rem !important;
        border: 1px solid var(--card-border) !important;
        border-radius: 0.85rem !important;
        background: var(--card-bg) !important;
        box-shadow: var(--card-shadow) !important;
        transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease !important;
    }}

    [data-testid="stMetric"]:hover {{
        transform: translateY(-2px);
        box-shadow: var(--card-shadow-hover) !important;
        border-color: var(--border-accent) !important;
    }}

    [data-testid="stMetricLabel"] {{
        color: var(--ink-tertiary) !important;
        font-size: 0.76rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        margin-bottom: 0.35rem !important;
    }}

    [data-testid="stMetricValue"] {{
        color: var(--ink-primary) !important;
        font-family: 'Manrope', sans-serif !important;
        font-size: 1.75rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.025em !important;
    }}

    [data-testid="stMetricDelta"] {{
        font-size: 0.76rem !important;
        font-weight: 600 !important;
    }}

    /* Streamlit Containers & Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: var(--card-bg) !important;
        border: 1px solid var(--card-border) !important;
        border-radius: 0.85rem !important;
        box-shadow: var(--card-shadow) !important;
        padding: 0.85rem !important;
    }}

    /* Dataframe & Tables */
    [data-testid="stDataFrame"], [data-testid="stTable"] {{
        border: 1px solid var(--card-border) !important;
        border-radius: 0.85rem !important;
        overflow: hidden !important;
        background: var(--card-bg) !important;
        box-shadow: var(--card-shadow) !important;
    }}

    /* Primary and Secondary Action Buttons */
    [data-testid="stButton"] button[kind="primary"] {{
        border: 0 !important;
        border-radius: 0.65rem !important;
        background: var(--brand-gradient) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-family: 'Manrope', sans-serif !important;
        padding: 0.6rem 1.35rem !important;
        box-shadow: 0 4px 14px var(--brand-glow) !important;
        transition: all 160ms cubic-bezier(0.16, 1, 0.3, 1) !important;
    }}

    [data-testid="stButton"] button[kind="primary"]:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px var(--brand-glow) !important;
        opacity: 0.95 !important;
    }}

    [data-testid="stButton"] button {{
        border-radius: 0.65rem !important;
        font-weight: 600 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: var(--surface-subtle) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--ink-primary) !important;
        transition: all 160ms ease !important;
    }}

    [data-testid="stButton"] button:hover {{
        background-color: var(--surface-hover) !important;
        border-color: var(--border-strong) !important;
        transform: translateY(-1px);
    }}

    /* Input Controls, Selectboxes, Text Areas */
    [data-baseweb="select"] > div {{
        background-color: var(--input-bg) !important;
        border-color: var(--input-border) !important;
        color: var(--ink-primary) !important;
        border-radius: 0.65rem !important;
    }}

    [data-baseweb="popover"], [data-baseweb="menu"] {{
        background-color: var(--surface-card) !important;
        border: 1px solid var(--border-strong) !important;
        border-radius: 0.65rem !important;
    }}

    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {{
        background-color: var(--input-bg) !important;
        border: 1px solid var(--input-border) !important;
        color: var(--ink-primary) !important;
        border-radius: 0.65rem !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }}

    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {{
        border-color: var(--brand-primary) !important;
        box-shadow: 0 0 0 2px var(--brand-glow) !important;
    }}

    /* Alerts and Callouts */
    [data-testid="stAlert"] {{
        border-radius: 0.85rem !important;
        border-width: 1px !important;
        border-style: solid !important;
        background-color: var(--surface-subtle) !important;
        box-shadow: var(--card-shadow) !important;
    }}

    /* Custom Scrollbar */
    ::-webkit-scrollbar {{
        width: 7px;
        height: 7px;
    }}
    ::-webkit-scrollbar-track {{
        background: var(--canvas);
    }}
    ::-webkit-scrollbar-thumb {{
        background: var(--border-strong);
        border-radius: 9999px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: var(--brand-primary);
    }}

    /* Flat, consistent surfaces and accessible controls */
    .top-system-strip,
    .emp-profile-ribbon,
    .sidebar-status-card,
    [data-testid="stMetric"],
    div[data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stDataFrame"],
    [data-testid="stTable"],
    [data-testid="stAlert"] {{
        border-radius: 0.5rem !important;
        box-shadow: none !important;
    }}

    .exec-synthesis-card {{
        background: #ffffff;
        border: 1px solid var(--border-subtle);
        border-left: 4px solid var(--brand-primary);
        border-radius: 0.5rem;
        box-shadow: none;
        padding: 1.25rem 1.4rem;
    }}

    .exec-synthesis-card::before {{
        display: none;
    }}

    .exec-synthesis-header {{
        justify-content: flex-start;
    }}

    .exec-synthesis-badge {{
        background: transparent;
        border: 0;
        color: var(--ink-primary);
        border-radius: 0;
        padding: 0;
        font-size: 0.9rem;
        letter-spacing: 0;
        text-transform: none;
    }}

    .pulse-dot {{
        display: none;
    }}

    .exec-synthesis-text {{
        font-size: 0.95rem;
        line-height: 1.65;
    }}

    .strip-pill {{
        border-radius: 0.375rem;
    }}

    .emp-avatar-badge {{
        background: #1d4ed8;
        border-radius: 0.5rem;
        width: 4rem;
        font-size: 0.68rem;
    }}

    .emp-tag,
    .badge-ontrack,
    .badge-deviating,
    .badge-context {{
        border-radius: 0.375rem;
    }}

    .badge-ontrack {{
        background: #ecfdf5;
        border-color: #a7f3d0;
        color: #047857;
    }}

    .badge-deviating {{
        background: #fff1f2;
        border-color: #fecdd3;
        color: #be123c;
    }}

    .badge-context {{
        background: #eff6ff;
        border-color: #bfdbfe;
        color: #1d4ed8;
    }}

    [data-testid="stMetric"] {{
        padding: 1rem 1.1rem !important;
        border: 1px solid var(--border-subtle) !important;
        background: #ffffff !important;
        transition: border-color 150ms ease !important;
    }}

    [data-testid="stMetric"]:hover {{
        transform: none;
        border-color: var(--border-strong) !important;
    }}

    [data-testid="stMetricLabel"] {{
        color: #475569 !important;
        font-size: 0.7rem !important;
        letter-spacing: 0.07em !important;
    }}

    [data-testid="stMetricValue"] {{
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        letter-spacing: -0.03em !important;
    }}

    [data-testid="stMetricDelta"] {{
        color: #475569 !important;
    }}

    [data-testid="stButton"] button[kind="primary"] {{
        border-radius: 0.5rem !important;
        background: #2563eb !important;
        color: #ffffff !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
        padding: 0.55rem 1rem !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.12) !important;
    }}

    [data-testid="stButton"] button[kind="primary"],
    [data-testid="stButton"] button[kind="primary"] *,
    .st-key-reset-team-filters button,
    .st-key-reset-team-filters button * {{
        color: #ffffff !important;
    }}

    [data-testid="stButton"] button[kind="primary"]:hover {{
        background: #1d4ed8 !important;
        color: #ffffff !important;
        transform: none !important;
    }}

    [data-testid="stFormSubmitButton"] button {{
        border: 1px solid #1d4ed8 !important;
        border-radius: 0.5rem !important;
        background: #1d4ed8 !important;
        color: #ffffff !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-weight: 600 !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.12) !important;
    }}

    [data-testid="stFormSubmitButton"] button *,
    [data-testid="stFormSubmitButton"] button p {{
        color: #ffffff !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }}

    [data-testid="stFormSubmitButton"] button:hover {{
        border-color: #1e40af !important;
        background: #1e40af !important;
        color: #ffffff !important;
    }}

    [data-testid="stButton"] button {{
        border-radius: 0.5rem !important;
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #334155 !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
    }}

    [data-testid="stButton"] button:hover {{
        background: #f8fafc !important;
        border-color: #94a3b8 !important;
        transform: none !important;
    }}

    [data-testid="stButton"] button:focus-visible,
    [data-baseweb="select"] > div:focus-within {{
        outline: none !important;
        border-color: #2563eb !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.25) !important;
    }}

    [data-baseweb="select"] > div {{
        background-color: #ffffff !important;
        border-color: #cbd5e1 !important;
        border-radius: 0.5rem !important;
    }}

    [data-testid="stMultiSelect"] [data-tag] {{
        background: #2563eb !important;
        border: 1px solid #1d4ed8 !important;
        color: #ffffff !important;
        border-radius: 0.375rem !important;
    }}

    [data-testid="stMultiSelect"] [data-tag] span,
    [data-testid="stMultiSelect"] [data-tag] button,
    [data-testid="stMultiSelect"] [data-tag] svg {{
        color: #ffffff !important;
        fill: #ffffff !important;
    }}

    [data-testid="stMultiSelect"] [data-tag] path {{
        stroke: #ffffff !important;
    }}

    [data-testid="stButton"] button[kind="secondary"][aria-label="Reset filters"],
    .st-key-reset-team-filters button {{
        background: #2563eb !important;
        border-color: #2563eb !important;
        color: #ffffff !important;
    }}

    .st-key-reset-team-filters button:hover {{
        background: #1d4ed8 !important;
        border-color: #1d4ed8 !important;
        color: #ffffff !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label {{
        min-height: 2.4rem;
        border-radius: 0.375rem;
        color: #94a3b8 !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
        background: rgba(30, 41, 59, 0.8);
        border: 0;
        border-left: 4px solid #3b82f6;
        border-radius: 0.375rem;
        color: #ffffff !important;
        padding-left: 0.65rem;
        box-shadow: none;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
        background: rgba(30, 41, 59, 0.4);
        color: #e2e8f0 !important;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {{
        color: #ffffff !important;
        font-weight: 600;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label[data-testid="stRadioOption"] > div > div:first-child {{
        display: none;
    }}

    [data-testid="stDataFrame"] {{
        --gdg-cell-horizontal-padding: 16px;
        --gdg-cell-vertical-padding: 12px;
    }}

    .st-key-employee-selector-bar {{
        position: sticky;
        top: 0;
        z-index: 10;
        padding: 0.9rem 1rem;
        margin: 0 -1rem 1.25rem;
        background: rgba(255, 255, 255, 0.97);
        border: 1px solid #e2e8f0;
        border-radius: 0.75rem;
        border-bottom: 1px solid #e2e8f0;
        backdrop-filter: blur(8px);
    }}

    .st-key-employee-selector-bar label {{
        color: #334155 !important;
        font-size: 0.875rem !important;
        font-weight: 600 !important;
    }}

    .st-key-employee-selector-bar [role="group"] {{
        min-height: 3.25rem;
        background: #ffffff !important;
        border: 1px solid #94a3b8 !important;
        border-radius: 0.5rem !important;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
        transition: border-color 150ms ease, box-shadow 150ms ease;
    }}

    .st-key-employee-selector-bar [role="group"]:hover {{
        border-color: #64748b !important;
    }}

    .st-key-employee-selector-bar [role="group"]:focus-within {{
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2) !important;
    }}

    .st-key-employee-selector-bar input[role="combobox"] {{
        min-height: 3.1rem;
        padding: 0.75rem 0.75rem 0.75rem 2.8rem !important;
        background-color: #ffffff !important;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 24 24' fill='none' stroke='%2364758b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='11' cy='11' r='7'/%3E%3Cpath d='m20 20-4-4'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: 0.9rem center;
        color: #0f172a !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        opacity: 1 !important;
    }}

    .st-key-employee-selector-bar input[role="combobox"]::placeholder {{
        color: #64748b !important;
        opacity: 1 !important;
    }}

    .st-key-employee-selector-bar [role="group"] button {{
        min-width: 2.75rem;
        color: #475569 !important;
        background: #ffffff !important;
    }}

    .st-key-employee-selector-bar [role="group"] button:hover {{
        color: #1d4ed8 !important;
        background: #eff6ff !important;
    }}

    </style>
    """


def configure_altair_theme(chart: alt.Chart) -> alt.Chart:
    """Apply the fixed light Metropolitan theme to an Altair chart."""
    axis_color = "#475569"
    title_color = "#0f172a"
    grid_color = "#e2e8f0"

    return (
        chart.configure_view(strokeOpacity=0)
        .configure_axis(
            domain=False,
            labelColor=axis_color,
            titleColor=title_color,
            gridColor=grid_color,
            labelFont="Plus Jakarta Sans, -apple-system, sans-serif",
            titleFont="Plus Jakarta Sans, -apple-system, sans-serif",
            titleFontWeight="bold",
            labelFontSize=11,
            titleFontSize=12,
        )
        .configure_legend(
            labelColor=axis_color,
            titleColor=title_color,
            labelFont="Plus Jakarta Sans, -apple-system, sans-serif",
            titleFont="Plus Jakarta Sans, -apple-system, sans-serif",
            titleFontWeight="bold",
            labelFontSize=11,
            titleFontSize=12,
        )
        .configure_title(
            color=title_color,
            font="Manrope, sans-serif",
            fontWeight="bold",
            fontSize=14,
        )
    )


# ------------------------------------------------------------------------------
# PAGE INITIALIZATION
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Employee Efficiency & Monitoring AI Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(get_theme_css(), unsafe_allow_html=True)

init_db()


@st.cache_resource(show_spinner="Loading employee performance data...")
def get_bundle(as_of: str):
    return load_bundle(as_of)


periods = available_periods()
if not periods:
    st.info(
        "No employee KPI data is available. From the Employee_Efficiency folder, "
        "run `uv run python -m src.services.preprocessing.pipeline` to load the company dataset, "
        "then refresh this page."
    )
    st.stop()

pages = [
    "Team overview",
    "Employee analysis",
    "Review queue",
    "Intervention tracking",
    "Evaluation",
]

phase_labels = {
    "pre_mid_year": (
        "Pre Mid-Year Phase",
        "Mid-year and annual figures are estimated from the recent trend (not yet confirmed)",
    ),
    "post_mid_year": (
        "Mid-Year Confirmed",
        "Mid-year figure confirmed; annual figure estimated from the recent trend (not yet confirmed)",
    ),
    "post_full_year": (
        "Annual Cycle Confirmed",
        "All annual milestones and targets confirmed",
    ),
}

# ------------------------------------------------------------------------------
# SIDEBAR NAVIGATION & STATE
# ------------------------------------------------------------------------------
st.sidebar.markdown(get_brand_header_html(), unsafe_allow_html=True)

st.sidebar.caption("DECISION WORKSPACES")
page = st.sidebar.radio("Workspaces", pages, label_visibility="collapsed")
st.sidebar.divider()

st.sidebar.caption("ACTIVE REPORTING CYCLE")
as_of = st.sidebar.selectbox(
    "Active Reporting Cycle",
    periods,
    index=len(periods) - 1,
    format_func=lambda val: pd.Period(val, freq="M").strftime("%B %Y"),
    label_visibility="collapsed",
)
bundle = get_bundle(as_of)


phase_name, phase_note = phase_labels[determine_phase(as_of).value]
st.sidebar.markdown(
    f"""
    <div class="sidebar-status-card">
      <div class="sidebar-status-kicker">Reporting Horizon State</div>
      <div class="sidebar-status-val">{phase_name}</div>
      <div class="sidebar-status-sub">Closed cycle data through {pd.Period(as_of, freq="M").strftime("%b %Y")}</div>
      <div class="sidebar-status-sub" style="margin-top:0.4rem; color:#94a3b8; font-size:0.72rem; line-height:1.4;">{phase_note}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


def render_system_strip(active_period: str) -> None:
    """Render top enterprise system status bar."""
    period_label = pd.Period(active_period, freq="M").strftime("%B %Y")
    st.markdown(
        f"""
        <div class="top-system-strip">
          <div class="strip-badges">
            <span class="strip-pill">Reporting period: <strong>{period_label}</strong></span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(kicker: str, title: str, description: str) -> None:
    st.markdown(
        f'<div class="page-kicker"><span class="kicker-dot"></span> ⚡ {kicker}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<h1 class="page-title">{title}</h1>', unsafe_allow_html=True)
    st.markdown(f'<div class="page-desc">{description}</div>', unsafe_allow_html=True)


def status_badge_text(report) -> str:
    if report.insufficient_data:
        return "Insufficient data"
    if not report.deviation.is_deviating:
        return "On target"
    return f"Clear drop - {report.deviation.severity}"


def manager_attribution(report) -> str:
    if report.insufficient_data:
        return "Insufficient data"
    if not report.diagnosis:
        return "No concern identified"
    if report.diagnosis.employee_controllable == "no":
        return "Wider system or market conditions"
    if report.diagnosis.employee_controllable == "partly":
        return "Partly management-assigned workload"
    if report.diagnosis.employee_controllable == "yes":
        return "Possible skills or training support"
    return "Not clear from the available information"


def render_manager_review(bundle, employee_id: int, report) -> None:
    """Show the latest recorded management review next to the current assessment."""
    st.markdown("### Manager's review vs current assessment")
    if bundle.hr_reviews.empty:
        st.info("No manager review is recorded for this employee.")
        return
    employee_reviews = bundle.hr_reviews[bundle.hr_reviews["employee_id"] == employee_id].copy()
    if employee_reviews.empty:
        st.info("No manager review is recorded for this employee.")
        return
    latest = employee_reviews.sort_values("review_cycle").iloc[-1]
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Latest review cycle:** {latest['review_cycle']}")
        st.markdown(
            f"**Manager rating:** {latest['rating']}/5"
            if pd.notna(latest["rating"]) else "**Manager rating:** Not recorded"
        )
        st.markdown(f"**Manager comment:** {latest['manager_comment'] or 'No comment recorded.'}")
        st.markdown(f"**Action taken:** {latest['action_taken'] or 'No action recorded.'}")
    with right:
        st.markdown(
            f"**Current assessment:** {status_badge_text(report)} · "
            f"{report.diagnosis.verdict if report.diagnosis else 'No cause identified.'}"
        )
        if (
            report.diagnosis
            and report.diagnosis.primary_cause in {"process", "external"}
            and pd.notna(latest["rating"])
            and int(latest["rating"]) <= 2
        ):
            st.warning(
                "The recorded manager rating is low, while the current evidence points to "
                "process or market conditions. Review the context before attributing the result to the employee."
            )


# ==============================================================================
# 1. TEAM OVERVIEW
# ==============================================================================
if page == "Team overview":
    render_system_strip(as_of)
    render_page_header(
        "WORKFORCE PERFORMANCE INTELLIGENCE",
        "Enterprise Service Workforce Overview",
        "Monitoring service results across roles and highlighting clear drops that may need a manager's attention.",
    )

    reports = run_team(bundle)
    df = pd.DataFrame(
        [
            {
                "Employee": report.employee_code,
                "Role": report.role,
                "Performance Score": None if report.insufficient_data else report.overall_score,
                "Change vs Usual Level": None if report.insufficient_data else report.trajectory.delta_vs_baseline,
                "Data through": report.data_through or "No complete month",
                "Status": status_badge_text(report),
                "Attributed Factor": (
                    CAUSE_LABELS.get(report.diagnosis.primary_cause, "No clear cause identified")
                    if report.diagnosis
                    else "No clear drop"
                ),
                "Attribution": manager_attribution(report),
            }
            for report in reports
        ]
    )

    total_emps = len(df)
    dev_count = int(df["Status"].str.startswith("Clear drop").sum())
    insufficient_count = int(df["Status"].eq("Insufficient data").sum())
    on_track_count = total_emps - dev_count - insufficient_count
    context_count = int(
        df["Attribution"]
        .isin(["Wider system or market conditions", "Partly management-assigned workload"])
        .sum()
    )
    on_track_percent = on_track_count / total_emps if total_emps else 0

    # Executive Workforce Performance Synthesis Card
    workforce_paragraph = team_narrative(reports, as_of)
    st.markdown(
        f"""
        <div class="exec-synthesis-card">
          <div class="exec-synthesis-header">
            <span class="exec-synthesis-badge">Executive workforce summary</span>
            <span style="color:var(--ink-tertiary); font-size:0.8rem; font-weight:500;">Reporting period: {pd.Period(as_of, freq="M").strftime("%B %Y")}</span>
          </div>
          <div class="exec-synthesis-text">{workforce_paragraph}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(5)
    metric_cols[0].metric("Total Personnel", total_emps)
    metric_cols[1].metric(
        "Stable / On Track",
        on_track_count,
        f"{on_track_percent:.0%} of workforce",
    )
    metric_cols[2].metric(
        "Flagged for Review",
        dev_count,
        f"{dev_count} employees need review",
        delta_color="inverse",
    )
    metric_cols[3].metric(
        "Context-Attributed",
        context_count,
        "Wider service conditions or assigned workload",
        delta_color="off",
    )
    metric_cols[4].metric("Insufficient data", insufficient_count, "No performance conclusion")

    st.markdown("### Employee results and changes from usual levels")
    roles = sorted(df["Role"].unique())
    statuses = sorted(df["Status"].unique())
    role_state_key = "team-role-filter"
    status_state_key = "team-status-filter"
    for state_key, options in (
        (role_state_key, roles),
        (status_state_key, statuses),
    ):
        if state_key not in st.session_state:
            st.session_state[state_key] = options
        else:
            st.session_state[state_key] = [
                selected for selected in st.session_state[state_key] if selected in options
            ]

    def reset_team_filters() -> None:
        st.session_state[role_state_key] = roles
        st.session_state[status_state_key] = statuses

    role_filter = st.multiselect(
        "Operational role",
        roles,
        key=role_state_key,
    )
    status_filter = st.multiselect(
        "Performance status",
        statuses,
        key=status_state_key,
    )
    st.button(
        "Reset filters",
        on_click=reset_team_filters,
        key="reset-team-filters",
    )

    filtered = df[
        (df["Role"].isin(role_filter)) & (df["Status"].isin(status_filter))
    ].sort_values("Change vs Usual Level", ascending=True, na_position="last")

    st.dataframe(
        filtered,
        width="stretch",
        hide_index=True,
        column_config={
            "Performance Score": st.column_config.NumberColumn(
                "Performance score (out of 100)", format="%.1f"
            ),
            "Change vs Usual Level": st.column_config.NumberColumn(
                "Change vs own usual score", format="%+.1f"
            ),
            "Data through": st.column_config.TextColumn("Complete data through"),
            "Status": st.column_config.TextColumn("Performance status"),
        },
    )
    st.caption(
        "A performance score is out of 100; 75 means in line with the company's usual level. "
        "Text labels show whether results are on target or need a manager's review."
    )

    # Role-wise Aggregation Chart
    st.markdown("### Average performance score by role")
    role_summary = (
        filtered.dropna(subset=["Performance Score"]).groupby("Role")
        .agg({"Performance Score": "mean", "Employee": "count"})
        .reset_index()
    )
    role_summary.columns = ["Role", "Average Score", "Personnel Count"]

    role_chart_color = "#2563eb"
    role_chart = (
        alt.Chart(role_summary)
        .mark_bar(cornerRadiusEnd=6, color=role_chart_color)
        .encode(
            x=alt.X(
                "Average Score:Q",
                scale=alt.Scale(domain=[0, 100]),
                title="Average performance score (out of 100)",
            ),
            y=alt.Y("Role:N", title=None, sort="-x"),
            tooltip=[
                alt.Tooltip("Role:N"),
                alt.Tooltip("Average Score:Q", format=".1f"),
                alt.Tooltip("Personnel Count:Q", title="Staff Count"),
            ],
        )
        .properties(height=190)
    )
    if not role_summary.empty:
        st.altair_chart(configure_altair_theme(role_chart), width="stretch")

    st.markdown("### Monthly performance trend by role")
    role_monthly = bundle.monthly.copy()
    role_monthly = role_monthly[
        (role_monthly["period"] <= as_of) & role_monthly["overall"].notna()
    ].copy()
    if not role_monthly.empty:
        role_monthly["Role"] = role_monthly["role"].map(
            lambda value: ROLE_LABELS[Role(value)]
        )
        role_trend = (
            role_monthly.groupby(["period", "Role"])
            .agg(
                **{
                    "Average score": ("overall", "mean"),
                    "Employees with complete data": ("employee_id", "nunique"),
                }
            )
            .reset_index()
        )
        ordered_periods = sorted(role_trend["period"].unique())
        interval = max(1, (len(ordered_periods) + 7) // 8)
        period_ticks = ordered_periods[::interval]
        if ordered_periods and period_ticks[-1] != ordered_periods[-1]:
            period_ticks.append(ordered_periods[-1])
        trend_roles = sorted(role_trend["Role"].unique())
        trend_chart = (
            alt.Chart(role_trend)
            .mark_line(point=alt.OverlayMarkDef(size=55, filled=True), strokeWidth=2.5)
            .encode(
                x=alt.X(
                    "period:N",
                    title="Month",
                    axis=alt.Axis(
                        values=period_ticks,
                        labelAngle=0,
                        labelOverlap=True,
                        labelLimit=90,
                    ),
                ),
                y=alt.Y(
                    "Average score:Q",
                    title="Average performance score (out of 100)",
                    scale=alt.Scale(domain=[0, 100]),
                ),
                color=alt.Color(
                    "Role:N",
                    title="Operational role",
                    scale=alt.Scale(
                        domain=trend_roles,
                        range=["#2563eb", "#0f766e", "#475569", "#7c3aed", "#b45309", "#0891b2"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("period:N", title="Month"),
                    alt.Tooltip("Role:N"),
                    alt.Tooltip("Average score:Q", format=".1f"),
                    alt.Tooltip(
                        "Employees with complete data:Q",
                        title="Employees with complete data",
                    ),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart(configure_altair_theme(trend_chart), width="stretch")
        st.caption(
            "Each monthly point averages employees with complete KPI coverage for that month; "
            "the employee count can vary over time."
        )
    else:
        st.info("No complete monthly performance scores are available for this reporting period.")

    st.markdown("### Employee score distribution by role")
    score_distribution = filtered.dropna(subset=["Performance Score"])
    if not score_distribution.empty:
        distribution_chart = (
            alt.Chart(score_distribution)
            .mark_boxplot(extent="min-max")
            .encode(
                x=alt.X(
                    "Performance Score:Q",
                    title="Performance score (out of 100)",
                    scale=alt.Scale(domain=[0, 100]),
                ),
                y=alt.Y("Role:N", title=None, sort="-x"),
                color=alt.Color("Role:N", legend=None),
                tooltip=[
                    alt.Tooltip("Role:N"),
                    alt.Tooltip("Employee:N"),
                    alt.Tooltip("Performance Score:Q", format=".1f"),
                ],
            )
            .properties(height=220)
        )
        st.altair_chart(configure_altair_theme(distribution_chart), width="stretch")
        st.caption(
            "Boxes summarize the median and middle half of employee scores; whiskers show the "
            "observed range. Interpret role comparisons cautiously when staff counts are small."
        )
    else:
        st.info("No employee scores match the selected filters.")


# ==============================================================================
# 2. EMPLOYEE ANALYSIS
# ==============================================================================
elif page == "Employee analysis":
    render_system_strip(as_of)
    render_page_header(
        "INDIVIDUAL PERFORMANCE INTELLIGENCE",
        "Employee Performance Analysis",
        "Multi-agent diagnostic evaluation synthesizing role-specific KPIs, trajectory horizons, operating context, and explainable root-cause diagnosis.",
    )

    emp_list = bundle.employees["code"].tolist()
    with st.container(key="employee-selector-bar"):
        code = st.selectbox(
            "Select Employee for Diagnostic Evaluation",
            emp_list,
            format_func=lambda val: (
                f"{val} · {ROLE_LABELS[Role(bundle.emp(val)['role'])]} · "
                f"{bundle.emp(val)['team']} · {bundle.emp(val)['status']}"
            ),
            help="Search by employee ID, role, team, or employment status.",
        )

    with st.form(key=f"assessment-context-form-{code}-{as_of}"):
        st.markdown("### Add manager context to this assessment")
        manager_factors = st.multiselect(
            "Manager-reported context factors",
            options=list(review.MANAGER_CONTEXT_FACTORS),
            format_func=review.MANAGER_CONTEXT_FACTORS.get,
            key=f"assessment-context-factors-{code}-{as_of}",
        )
        manager_note = st.text_area(
            "Additional manager context (optional)",
            placeholder="Add relevant work-related context that may help explain this reporting period...",
            max_chars=2000,
            key=f"assessment-context-note-{code}-{as_of}",
        )
        st.form_submit_button("Apply context and reassess", type="primary")

    report = run_assessment(
        bundle,
        code,
        manager_factors=manager_factors,
        manager_note=manager_note,
    )
    emp_meta = bundle.emp(code)
    render_manager_review(bundle, int(emp_meta["id"]), report)

    status_class = (
        "badge-ontrack"
        if not report.deviation.is_deviating or report.insufficient_data
        else "badge-deviating"
    )
    status_icon = "●" if not report.deviation.is_deviating else "▲"

    # Modern Employee Profile Ribbon
    st.markdown(
        f"""
        <div class="emp-profile-ribbon">
          <div class="emp-avatar-badge">{code}</div>
          <div>
            <div class="emp-code-title">{code}</div>
            <div style="font-size:0.75rem; color:var(--ink-tertiary);">Employee Personnel Profile</div>
          </div>
          <div class="emp-tag">🏢 {report.role}</div>
          <div class="emp-tag">📍 Region: {emp_meta['team']}</div>
          <div class="emp-tag">📅 Service Tenure: Since {emp_meta['hire_year']}</div>
          <div class="emp-tag">Data through: {report.data_through or 'No complete month'}</div>
          <div style="margin-left:auto;" class="{status_class}">
            {status_icon} {status_badge_text(report).upper()}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Summary")
    if report.insufficient_data:
        st.warning(
            f"Insufficient data through {report.data_through or 'the selected period'}: "
            f"{report.insufficient_reason}. No performance conclusion is made."
        )
        st.markdown(report.narrative)
        st.stop()
    st.caption(
        f"Performance score: {report.overall_score:.1f} out of 100 "
        f"({report.trajectory.delta_vs_baseline:+.1f} points compared with this employee's own usual "
        f"level in 2024, {report.trajectory.baseline_score:.1f})."
    )
    st.markdown(report.narrative if report.narrative else narrate(report))

    # Performance Snapshot KPI Metrics
    score_cols = st.columns(4)
    score_cols[0].metric(
        "Performance score",
        f"{report.overall_score:.1f}",
        f"{report.trajectory.delta_vs_baseline:+.1f} vs this employee's usual level in 2024",
    )
    score_cols[1].metric(
        "Usual performance score in 2024",
        f"{report.trajectory.baseline_score:.1f}",
        "Employee's own usual level",
        delta_color="off",
    )
    score_cols[2].metric(
        "Mid-Year Checkpoint",
        (
            "—"
            if report.trajectory.mid_year.score is None
            else f"{report.trajectory.mid_year.score:.1f}"
        ),
        (
            "Confirmed"
            if report.trajectory.mid_year.status == "confirmed"
            else "Estimated from recent trend (not yet confirmed)"
            if report.trajectory.mid_year.status == "projected"
            else "Partly confirmed; remaining months estimated from recent trend (not yet confirmed)"
        ),
        delta_color="off",
    )
    score_cols[3].metric(
        "Full-Year Horizon",
        (
            "—"
            if report.trajectory.full_year.score is None
            else f"{report.trajectory.full_year.score:.1f}"
        ),
        (
            "Confirmed"
            if report.trajectory.full_year.status == "confirmed"
            else "Estimated from recent trend (not yet confirmed)"
            if report.trajectory.full_year.status == "projected"
            else "Partly confirmed; remaining months estimated from recent trend (not yet confirmed)"
        ),
        delta_color="off",
    )

    # Trajectory Horizon Chart
    st.markdown("### Performance score over time")
    points = pd.DataFrame([pt.model_dump() for pt in report.trajectory.points])
    points["status"] = points["status"].astype(str).str.replace(
        "DataStatus.", "", regex=False
    ).map({
        "confirmed": "Confirmed",
        "projected": "Estimated (not yet confirmed)",
    })

    conf_color = "#183b83"
    proj_color = "#db0d1b"
    baseline_color = "#64748b"

    trajectory_chart = (
        alt.Chart(points)
        .mark_line(
            point=alt.OverlayMarkDef(size=60, filled=True), strokeWidth=3
        )
        .encode(
            x=alt.X(
                "period:N",
                title=None,
                axis=alt.Axis(labelAngle=0, tickSize=0),
            ),
            y=alt.Y(
                "score:Q",
                title="Performance score (out of 100)",
                scale=alt.Scale(domain=[0, 100]),
            ),
            color=alt.Color(
                "status:N",
                title="Figure status",
                scale=alt.Scale(
                    domain=["Confirmed", "Estimated (not yet confirmed)"],
                    range=[conf_color, proj_color],
                ),
            ),
            strokeDash=alt.StrokeDash(
                "status:N",
                scale=alt.Scale(
                    domain=["Confirmed", "Estimated (not yet confirmed)"], range=[[1, 0], [5, 4]]
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("period:N", title="Operational Period"),
                alt.Tooltip("score:Q", title="Performance score", format=".1f"),
                alt.Tooltip("status:N", title="Figure status"),
            ],
        )
        .properties(height=280)
    )

    baseline_rule = (
        alt.Chart(pd.DataFrame({"score": [report.trajectory.baseline_score]}))
        .mark_rule(color=baseline_color, strokeDash=[4, 4], strokeWidth=1.5)
        .encode(y="score:Q")
    )

    st.altair_chart(
        configure_altair_theme(trajectory_chart + baseline_rule),
        width="stretch",
    )

    st.markdown("### Service-area performance trends")
    employee_kpis = bundle.kpi[
        (bundle.kpi["employee_id"] == int(emp_meta["id"]))
        & (bundle.kpi["period"] <= as_of)
    ].copy()
    if not employee_kpis.empty:
        recent_periods = sorted(employee_kpis["period"].astype(str).unique())[-12:]
        category_trend = (
            employee_kpis[employee_kpis["period"].astype(str).isin(recent_periods)]
            .groupby(["period", "category"], as_index=False)["index"]
            .mean()
            .rename(columns={"period": "Month", "category": "Service area", "index": "Score"})
        )
        category_chart = (
            alt.Chart(category_trend)
            .mark_line(point=alt.OverlayMarkDef(size=50, filled=True), strokeWidth=2)
            .encode(
                x=alt.X("Month:N", title="Month", sort=recent_periods),
                y=alt.Y(
                    "Score:Q",
                    title="Average performance score (out of 100)",
                    scale=alt.Scale(domain=[0, 100]),
                ),
                color=alt.Color("Service area:N", title="Service area"),
                tooltip=[
                    alt.Tooltip("Month:N"),
                    alt.Tooltip("Service area:N"),
                    alt.Tooltip("Score:Q", format=".1f"),
                ],
            )
            .properties(height=280)
        )
        st.altair_chart(configure_altair_theme(category_chart), width="stretch")
        st.caption(
            "Monthly service-area scores average the employee's available, matured KPI records. "
            "Recent months may be absent for KPIs with a maturity delay."
        )
    else:
        st.info("No matured KPI records are available to chart for this employee.")

    # Category Breakdown & Operational Context
    col_cat, col_ctx = st.columns([1, 1])

    with col_cat:
        st.markdown("### Service areas")
        cat_df = pd.DataFrame(
            [
                {"Category": CATEGORY_LABELS.get(k, k), "Score": v}
                for k, v in report.category_scores.items()
            ]
        )
        cat_chart_color = "#183b83"
        cat_chart = (
            alt.Chart(cat_df)
            .mark_bar(cornerRadiusEnd=6, color=cat_chart_color)
            .encode(
                x=alt.X(
                    "Score:Q",
                    title=None,
                    scale=alt.Scale(domain=[0, 100]),
                ),
                y=alt.Y("Category:N", title=None, sort="-x"),
                tooltip=[
                    alt.Tooltip("Category:N"),
                    alt.Tooltip("Score:Q", format=".1f"),
                ],
            )
            .properties(height=max(160, 38 * len(cat_df)))
        )
        st.altair_chart(
            configure_altair_theme(cat_chart), width="stretch"
        )

    with col_ctx:
        st.markdown("### Work conditions and context")
        ctx_row1 = st.columns(2)
        ctx_row1[0].metric(
            "Assigned work compared with own usual level",
            f"{report.context.workload_ratio:.2f}x",
            (
                "High Volume Strain"
                if report.context.workload_ratio >= 1.2
                else "Normal Volume"
            ),
            delta_color=(
                "inverse" if report.context.workload_ratio >= 1.2 else "off"
            ),
        )
        ctx_row1[1].metric(
            "Monthly Overtime",
            f"{report.context.overtime_hours:.0f} hrs",
            (
                "Elevated Overtime"
                if report.context.overtime_hours >= 15
                else "Standard Range"
            ),
            delta_color=(
                "inverse" if report.context.overtime_hours >= 15 else "off"
            ),
        )

        ctx_row2 = st.columns(2)
        ctx_row2[0].metric(
            "Same-role peers also showing a drop",
            f"{report.context.peer_deviation_share:.0%}",
            "Same-role peers declining",
            delta_color="off",
        )
        ctx_row2[1].metric(
            "Feedback Sentiment",
            f"{report.context.sentiment:+.2f}",
            (
                "Favorable"
                if report.context.sentiment > 0.1
                else (
                    "Adverse"
                    if report.context.sentiment < -0.1
                    else "Neutral"
                )
            ),
            delta_color=(
                "normal"
                if report.context.sentiment > 0.1
                else (
                    "inverse"
                    if report.context.sentiment < -0.1
                    else "off"
                )
            ),
        )
        ctx_row3 = st.columns(2)
        ctx_row3[0].metric(
            "Jobs with parts waits",
            f"{report.context.parts_wait_share_delta:+.0%}",
            "Change from this employee's usual level",
            delta_color="inverse",
        )
        ctx_row3[1].metric(
            "Incomplete incoming records",
            f"{report.context.incomplete_input_delta:+.0%}",
            "Change from this employee's usual level",
            delta_color="inverse",
        )

        if report.context.notes:
            st.markdown("**Contextual Environmental Telemetry:**")
            for note in report.context.notes:
                st.markdown(f"- {note}")

    # Role-Specific Indicator Scorecard
    st.subheader("KPI table")
    st.caption(
        "Each row uses the real KPI name. The usual value is this employee's average in 2024; "
        "the performance score is out of 100, where 75 means in line with the company's usual level."
    )
    kpi_df = pd.DataFrame([item.model_dump() for item in report.kpis])
    st.dataframe(
        kpi_df[
            [
                "name",
                "category",
                "unit",
                "recent_avg",
                "baseline_avg",
                "index_recent",
                "delta",
                "label",
            ]
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "name": st.column_config.TextColumn("KPI Indicator"),
            "category": st.column_config.TextColumn("Service area"),
            "unit": st.column_config.TextColumn("Measure"),
            "recent_avg": st.column_config.NumberColumn(
                "Recent 3-month average", format="%.2f"
            ),
            "baseline_avg": st.column_config.NumberColumn(
                "Employee's usual value in 2024", format="%.2f"
            ),
            "index_recent": st.column_config.NumberColumn(
                "Performance score (out of 100)", format="%.1f"
            ),
            "delta": st.column_config.NumberColumn(
                "Change vs own usual score", format="%+.1f"
            ),
            "label": st.column_config.TextColumn("Assessment label"),
        },
    )

    st.markdown("### KPI change from the employee's usual level")
    kpi_change = kpi_df[["name", "delta"]].dropna().copy()
    if not kpi_change.empty:
        change_limit = max(5.0, float(kpi_change["delta"].abs().max()))
        change_chart = (
            alt.Chart(kpi_change)
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                x=alt.X(
                    "delta:Q",
                    title="Change in performance score (points)",
                    scale=alt.Scale(domain=[-change_limit, change_limit]),
                ),
                y=alt.Y(
                    "name:N",
                    title=None,
                    sort=alt.SortField(field="delta", order="ascending"),
                ),
                color=alt.condition(
                    alt.datum.delta >= 0,
                    alt.value("#183b83"),
                    alt.value("#db0d1b"),
                ),
                tooltip=[
                    alt.Tooltip("name:N", title="KPI"),
                    alt.Tooltip("delta:Q", title="Change from usual level", format="+.1f"),
                ],
            )
            .properties(height=max(180, 30 * len(kpi_change)))
        )
        zero_rule = (
            alt.Chart(pd.DataFrame({"delta": [0]}))
            .mark_rule(color="#64748b", strokeDash=[4, 4])
            .encode(x="delta:Q")
        )
        st.altair_chart(
            configure_altair_theme(change_chart + zero_rule),
            width="stretch",
        )
        st.caption(
            "Positive bars indicate a higher normalized KPI score than the employee's 2024 "
            "usual level; negative bars indicate a lower score. KPI direction is normalized "
            "so higher scores always indicate better performance."
        )

    # Diagnostic Findings & Action Plan
    st.subheader("Diagnosis")
    if report.diagnosis:
        with st.container(border=True):
            cause_cols = st.columns([1, 1, 2])
            cause_cols[0].metric(
                "Most likely explanation",
                CAUSE_LABELS.get(report.diagnosis.primary_cause, "No clear cause identified"),
            )
            cause_cols[1].metric(
                "Strength of evidence",
                evidence_strength(report.diagnosis.confidence),
            )
            cause_cols[2].metric(
                "Responsibility",
                manager_attribution(report),
            )

            st.markdown(f"**What the evidence suggests:** {report.diagnosis.verdict}")
            st.markdown("**Evidence by possible explanation:**")
            for cs in report.diagnosis.ranked:
                if cs.evidence:
                    cause_name = CAUSE_LABELS.get(cs.cause, "Other possible explanation")
                    st.markdown(
                        f"- **{cause_name} — strength of evidence: {evidence_strength(cs.score)}:** "
                        + " · ".join(cs.evidence)
                    )

        st.markdown("#### What we recommend")
        for rec in report.recommendations:
            with st.container(border=True):
                st.markdown(f"**{rec.headline}**")
                st.caption(
                    f"Priority: {rec.priority.title()} · Re-check after {rec.review_after_months} closed months"
                )
                for act in rec.actions:
                    st.markdown(f"- {act}")
                watch_names = [
                    next((item.name for item in report.kpis if item.code == code), code)
                    for code in rec.monitor_kpis
                ]
                if watch_names:
                    st.markdown(f"- **Afterwards, watch:** {', '.join(watch_names)}.")

        if st.button("Submit to Manager Review Queue", type="primary"):
            sub_ids = review.submit_for_review(report, bundle)
            if sub_ids:
                st.success(
                    f"Intervention plan routed to Manager Review Queue with reference ID: {', '.join(map(str, sub_ids))}"
                )
            elif page == "Data & preprocessing":
                st.info("Intervention proposal has already been submitted.")
    else:
        st.info(
            "No clear drop in performance is currently identified. Routine monitoring continues; "
            "the employee's strongest and weakest KPIs are named in the summary above."
        )


# ==============================================================================
# 3. MANAGER REVIEW QUEUE
# ==============================================================================
elif page == "Review queue":
    render_system_strip(as_of)
    render_page_header(
        "HUMAN-IN-THE-LOOP GOVERNANCE",
        "Manager Decision & Review Workspace",
        "Authoritative supervisory checkpoint: review, calibrate, approve or decline agent-formulated intervention plans before operational deployment.",
    )

    queue = review.pending_queue()
    if not queue.empty:
        queue = queue[queue["as_of"] <= as_of].reset_index(drop=True)
    if queue.empty:
        st.markdown(
            """
            <div style="text-align:center; padding:3.2rem 1.5rem; background:var(--card-bg); border:1px solid var(--card-border); border-radius:0.95rem; margin-top:1rem; box-shadow:var(--card-shadow);">
              <div style="font-size:2.8rem; margin-bottom:0.8rem;">✨</div>
              <h3 style="margin-bottom:0.4rem;">Manager Review Queue Clear</h3>
              <p style="color:var(--ink-secondary); font-size:0.92rem; max-width:520px; margin:0 auto;">
                No intervention proposals are currently awaiting review. Submit a proposed plan from Performance Analysis to add it to the queue.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.caption(
            f"{len(queue)} intervention proposal{'s' if len(queue) != 1 else ''} awaiting supervisory decision"
        )
        code_of = dict(zip(bundle.employees["id"], bundle.employees["code"]))

        for _, row in queue.iterrows():
            with st.container(border=True):
                st.markdown(f"### {row.headline}")
                st.markdown(
                    f"**Employee:** `{code_of.get(row.employee_id, 'EMP')}` · "
                    f"**Most likely explanation:** `{CAUSE_LABELS.get(row.cause, 'No clear cause identified')}` · "
                    f"**Priority:** `{row.priority.title()}` · "
                    f"**Period:** `{pd.Period(row.as_of, freq='M').strftime('%B %Y')}`"
                )
                if row.summary:
                    st.info(f"**Diagnostic Summary:** {row.summary}")
                action_key = f"act_{row.id}"
                if action_key not in st.session_state:
                    st.session_state[action_key] = "\n".join(row.actions)
                edited_actions = st.text_area(
                    "Review-adjusted action steps (one per line)",
                    key=action_key,
                    height=120,
                )

                col_appr, col_decl, _ = st.columns([1.5, 1.5, 5])
                if col_appr.button(
                    "Approve Plan", key=f"app_{row.id}", type="primary"
                ):
                    lines = [
                        l.strip()
                        for l in edited_actions.splitlines()
                        if l.strip()
                    ]
                    is_modified = lines != list(row.actions)
                    review.decide(
                        row.id,
                        "modified" if is_modified else "approved",
                        modified_actions=lines if is_modified else None,
                    )
                    st.rerun()

                if col_decl.button("Decline Plan", key=f"dec_{row.id}"):
                    review.decide(row.id, "rejected")
                    st.rerun()


# ==============================================================================
# 4. INTERVENTION TRACKING
# ==============================================================================
elif page == "Intervention tracking":
    render_system_strip(as_of)
    render_page_header(
        "CLOSED-LOOP GOVERNANCE",
        "Intervention Outcomes & Follow-up Tracking",
        "Track post-intervention efficiency trajectories and empirically validate outcomes over closed evaluation cycles.",
    )

    track_df = review.track_interventions(bundle)
    if track_df.empty:
        st.info("No approved interventions are currently tracked for this cycle.")
    else:
        improved_cnt = int((track_df["outcome"] == "improved").sum())
        eval_cnt = int((track_df["outcome"] == "too_early").sum())
        stable_cnt = int((track_df["outcome"] == "no_change").sum())

        m_cols = st.columns(4)
        m_cols[0].metric("Total Interventions", len(track_df))
        m_cols[1].metric("Verified Improved", improved_cnt, "Delta >= +3.0 pts")
        m_cols[2].metric("Maintained / Stable", stable_cnt)
        m_cols[3].metric("Evaluating (<2 months)", eval_cnt)

        st.dataframe(
            track_df,
            width="stretch",
            hide_index=True,
            column_config={
                "employee": st.column_config.TextColumn("Employee"),
                "started": st.column_config.TextColumn("Start Cycle"),
                "headline": st.column_config.TextColumn("Approved Initiative"),
                "score_at_start": st.column_config.NumberColumn(
                    "Score at Start", format="%.1f"
                ),
                "score_now": st.column_config.NumberColumn(
                    "Current Score", format="%.1f"
                ),
                "change": st.column_config.NumberColumn(
                    "Net Trajectory Shift", format="%+.1f"
                ),
                "outcome": st.column_config.TextColumn("Outcome Classification"),
            },
        )
        st.caption(
            "Outcomes measure the 3-month trailing efficiency score post-intervention against the initial approval baseline. "
            "Evaluations require a minimum of two closed reporting cycles to confirm empirical trends."
        )


# ==============================================================================
# 5. EVALUATION
# ==============================================================================
elif page == "Evaluation":
    render_system_strip(as_of)
    render_page_header(
        "SYSTEM DIAGNOSTIC VALIDATION",
        "Evaluation and performance checks",
        "Compare assessments with generated development labels or verified outcome labels, and inspect processing latency and agreement with the rule-based comparison.",
    )

    label_mode = st.radio(
        "Outcome labels",
        ("Synthetic scenario labels (development benchmark)", "Verified outcomes"),
        horizontal=True,
    )
    use_synthetic_truth = label_mode.startswith("Synthetic")
    evaluation_key = f"evaluation_{as_of}_{'synthetic' if use_synthetic_truth else 'verified'}"
    if st.button("Run evaluation", type="primary"):
        with st.spinner("Running assessments for the selected reporting month..."):
            st.session_state[evaluation_key] = evaluate(
                bundle,
                use_synthetic_truth=use_synthetic_truth,
            )
    result = st.session_state.get(evaluation_key)
    if result is None:
        st.info("Run the evaluation to calculate employee-level results and latency.")
    else:
        st.metric("Assessment latency", f"{result['avg_latency_s']:.3f} s average",
                  f"Max: {result['max_latency_s']:.3f} s")
        if not result["labels_available"]:
            st.warning(
                f"{result['label_message']} "
                "F1, precision, recall, and cause-accuracy metrics are therefore not calculated."
            )
            if result["agent_baseline_agreement"] is not None:
                st.metric("Agent / rule-based agreement",
                          f"{result['agent_baseline_agreement']:.1%}",
                          "Agreement is not a measure of accuracy")
        else:
            st.caption(f"Outcome label source: {result['label_source']}")
            agent_result = result["agent"]
            baseline_result = result["rule_based_baseline"]
            metrics = st.columns(6)
            metrics[0].metric("Agent accuracy", f"{agent_result['accuracy']:.1%}")
            metrics[1].metric("Agent F1", f"{agent_result['f1']:.3f}",
                              f"Precision: {agent_result['precision']:.3f}")
            metrics[2].metric("Rule-based F1", f"{baseline_result['f1']:.3f}",
                              f"Recall: {baseline_result['recall']:.3f}")
            metrics[3].metric("Cause accuracy", f"{result['root_cause_accuracy']:.1%}")
            metrics[4].metric("Context fairness",
                              f"{result['context_driven_correctly_not_blamed']:.1%}")
            metrics[5].metric("Employees evaluated", result["n_evaluable"],
                              f"of {result['n']} with labels")
            st.markdown("### Cause comparison")
            st.dataframe(result["confusion_matrix"], width="stretch")
            if not result["per_scenario"].empty:
                st.markdown("### Scenario results")
                st.dataframe(result["per_scenario"], width="stretch", hide_index=True)
            if not result["disagreements"].empty:
                st.markdown("### Diagnoses differing from verified labels")
                st.dataframe(result["disagreements"], width="stretch", hide_index=True)

        if st.button("Check a verified recovery case"):
            recovery = evaluate_recovery_case()
            if recovery["available"]:
                st.success(recovery["message"])
            else:
                st.info(recovery["message"])
        st.markdown("### Employee-level assessment results")
        st.dataframe(result["detail"], width="stretch", hide_index=True)

# ==============================================================================
# 6. DATA & PREPROCESSING
# ==============================================================================
else:
    render_system_strip(as_of)
    render_page_header(
        "DATA OPERATIONS",
        "Data & preprocessing",
        "Inspect source-file coverage, preprocessing actions, and completeness of employee-month performance data.",
    )
    st.info(
        "Company operational export: 34 pseudonymized employees, 33 months from January 2024 "
        "through September 2026. Export snapshot: 2 October 2026."
    )

    raw_files = []
    for source in sorted(RAW_DIR.glob("*.csv")):
        raw_rows = len(pd.read_csv(source, dtype=str, keep_default_na=False, usecols=[0]))
        raw_files.append({"Source file": source.name, "Rows in current export": raw_rows})
    st.markdown("### Source file row counts")
    st.dataframe(pd.DataFrame(raw_files), width="stretch", hide_index=True)

    st.markdown("### Latest preprocessing actions")
    if bundle.quality_log.empty:
        st.info("No preprocessing log is stored for the current database.")
    else:
        st.dataframe(
            bundle.quality_log.sort_values(["source_file", "stage", "rule"]),
            width="stretch",
            hide_index=True,
            column_config={
                "source_file": st.column_config.TextColumn("Source file"),
                "rule": st.column_config.TextColumn("Rule"),
                "rows_before": st.column_config.NumberColumn("Rows before"),
                "rows_after": st.column_config.NumberColumn("Rows after"),
                "rows_affected": st.column_config.NumberColumn("Rows affected"),
                "action": st.column_config.TextColumn("Action"),
            },
        )

    st.markdown("### KPI completeness by role and month")
    if bundle.monthly.empty:
        st.info("No monthly KPI coverage is available.")
    else:
        role_names = {
            Role(role).value: ROLE_LABELS[Role(role)]
            for role in bundle.employees["role"].unique()
        }
        coverage_rows = []
        role_counts = bundle.employees.groupby("role")["id"].nunique().to_dict()
        for (role, period), group in bundle.monthly.groupby(["role", "period"]):
            expected = len(ROLE_KPIS[Role(role)])
            complete = int(group["overall"].notna().sum())
            coverage_rows.append({
                "Role": role_names[role],
                "Month": period,
                "Complete employees": f"{complete}/{role_counts[role]}",
                "Average KPI coverage": f"{group['kpi_count'].mean() / expected:.0%}",
                "Complete month available": "Yes" if complete else "No",
            })
        st.dataframe(pd.DataFrame(coverage_rows), width="stretch", hide_index=True)

    st.warning(
        "Re-running preprocessing rebuilds the local SQLite database, including locally stored "
        "manager decisions and intervention tracking."
    )
    if st.button("Re-run preprocessing", type="primary"):
        with st.spinner("Rebuilding the employee performance database from source files..."):
            run_preprocessing()
        st.cache_resource.clear()
        st.rerun()
