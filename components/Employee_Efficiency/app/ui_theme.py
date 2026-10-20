"""Metropolitan Executive Theme & Design System for Employee Efficiency AI Agent.
Provides unified tokens, responsive Dark & Light Mode styling with Metropolitan Red and Blue palette,
black and white logo integration, Altair chart themes, and enterprise component renderers.

SLIIT Data Science Research Component: J26-DS-351 | IT23366268
Industry Partner / Context: Metropolitan Technologies (Pvt) Ltd - After-Sales Service Operations
"""
from __future__ import annotations

import base64
from pathlib import Path
import altair as alt

# Assets directory relative to this file
ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def get_logo_data_uri() -> str:
    """Return a data URI for the full-color logo on its high-contrast white background."""
    logo_path = ASSETS_DIR / "metropolitan_light.png"
    encoded = base64.b64encode(logo_path.read_bytes()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def get_symbol_icon_path(is_dark: bool = False) -> str:
    """Return filesystem path to Metropolitan emblem icon for favicon/tab icon."""
    filename = "metropolitan_symbol_light.png" if not is_dark else "metropolitan_symbol_dark.png"
    p = ASSETS_DIR / filename
    if p.exists():
        return str(p)
    return str(ASSETS_DIR / "metropolitan_light.png")


def get_brand_header_html() -> str:
    """Generate the Metropolitan-branded sidebar header."""
    logo_uri = get_logo_data_uri()
    img_html = f'<img src="{logo_uri}" alt="Metropolitan logo" class="brand-logo-img" />'

    return f"""
    <div class="brand-header">
      <div class="brand-logo-card">
        {img_html}
      </div>
      <div class="brand-details">
        <div class="brand-title">Metropolitan Technologies (Pvt) Ltd</div>
      </div>
    </div>
    """


def get_theme_css(is_dark: bool) -> str:
    """Generate high-contrast, executive CSS variables and overrides for Dark or Light mode.
    
    The color system is grounded in Metropolitan's brand identity:
    - Metropolitan Corporate Blue (#183b83 / #1e40af / #2563eb / #3b82f6)
    - Metropolitan Corporate Red (#db0d1b / #dc2626 / #ef4444)
    """
    if is_dark:
        # Dark Theme Palette (Deep Metropolitan Cyber-Obsidian with Royal Blue & Crimson Red)
        canvas = "#080c14"
        surface = "#0d1424"
        surface_card = "#111b2e"
        surface_subtle = "#16233b"
        surface_hover = "#1e2d4a"
        border_subtle = "rgba(255, 255, 255, 0.09)"
        border_strong = "rgba(255, 255, 255, 0.18)"
        border_accent = "rgba(59, 130, 246, 0.55)"

        ink_primary = "#f8fafc"
        ink_secondary = "#cbd5e1"
        ink_tertiary = "#94a3b8"
        ink_muted = "#64748b"

        # Metropolitan Primary Brand Colors
        brand_primary = "#3b82f6"       # Radiant Metropolitan Blue
        brand_secondary = "#ef4444"     # Radiant Metropolitan Red
        brand_blue = "#2563eb"
        brand_red = "#ef4444"
        brand_glow = "rgba(37, 99, 235, 0.35)"
        brand_red_glow = "rgba(239, 68, 68, 0.35)"
        brand_gradient = "linear-gradient(135deg, #1d4ed8 0%, #2563eb 50%, #dc2626 100%)"

        sidebar_bg = "#070b14"
        sidebar_surface = "#0f182b"
        sidebar_border = "rgba(255, 255, 255, 0.08)"
        sidebar_text = "#cbd5e1"

        brand_logo_bg = "#000000"
        brand_logo_border = "rgba(255, 255, 255, 0.12)"

        card_shadow = "0 4px 20px -2px rgba(0, 0, 0, 0.55)"
        card_shadow_hover = "0 12px 32px -4px rgba(0, 0, 0, 0.75)"
        card_bg = "#111b2e"
        card_border = "rgba(255, 255, 255, 0.08)"
        exec_card_bg = "linear-gradient(145deg, #111b2e 0%, #0a1120 100%)"

        chip_bg = "rgba(255, 255, 255, 0.04)"
        chip_border = "rgba(255, 255, 255, 0.1)"
        input_bg = "#131e33"
        input_border = "rgba(255, 255, 255, 0.12)"
    else:
        # Light Theme Palette (Executive Slate & Crisp Metropolitan Royal Blue & Crimson Red)
        canvas = "#f8fafc"
        surface = "#ffffff"
        surface_card = "#ffffff"
        surface_subtle = "#f1f5f9"
        surface_hover = "#eef2f6"
        border_subtle = "#e2e8f0"
        border_strong = "#cbd5e1"
        border_accent = "rgba(24, 59, 131, 0.45)"

        ink_primary = "#0f172a"
        ink_secondary = "#334155"
        ink_tertiary = "#64748b"
        ink_muted = "#94a3b8"

        # Metropolitan Primary Brand Colors
        brand_primary = "#183b83"       # Classic Metropolitan Royal Blue
        brand_secondary = "#db0d1b"     # Classic Metropolitan Crimson Red
        brand_blue = "#183b83"
        brand_red = "#db0d1b"
        brand_glow = "rgba(24, 59, 131, 0.22)"
        brand_red_glow = "rgba(219, 13, 27, 0.22)"
        brand_gradient = "linear-gradient(135deg, #183b83 0%, #1e40af 55%, #db0d1b 100%)"

        sidebar_bg = "#ffffff"
        sidebar_surface = "#f8fafc"
        sidebar_border = "#e2e8f0"
        sidebar_text = "#334155"

        brand_logo_bg = "#ffffff"
        brand_logo_border = "#e2e8f0"

        card_shadow = "0 1px 3px rgba(0, 0, 0, 0.04), 0 10px 25px -5px rgba(24, 59, 131, 0.06)"
        card_shadow_hover = "0 20px 30px -8px rgba(24, 59, 131, 0.12)"
        card_bg = "#ffffff"
        card_border = "#e2e8f0"
        exec_card_bg = "linear-gradient(145deg, #ffffff 0%, #f8faff 100%)"

        chip_bg = "#f1f5f9"
        chip_border = "#e2e8f0"
        input_bg = "#ffffff"
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
        --brand-blue: {brand_blue};
        --brand-red: {brand_red};
        --brand-glow: {brand_glow};
        --brand-red-glow: {brand_red_glow};
        --brand-gradient: {brand_gradient};
        --sidebar-bg: {sidebar_bg};
        --sidebar-surface: {sidebar_surface};
        --sidebar-border: {sidebar_border};
        --sidebar-text: {sidebar_text};
        --brand-logo-bg: {brand_logo_bg};
        --brand-logo-border: {brand_logo_border};
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
        --accent-rose: {brand_red};
        --accent-indigo: {brand_primary};
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
        max-width: 1480px;
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
        padding: 0.65rem 1.1rem;
        background: var(--surface-card);
        border: 1px solid var(--border-subtle);
        border-radius: 0.75rem;
        margin-bottom: 1.5rem;
        box-shadow: var(--card-shadow);
        border-left: 4px solid var(--brand-primary);
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
        gap: 0.4rem;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.22rem 0.65rem;
        border-radius: 9999px;
        background: var(--surface-subtle);
        border: 1px solid var(--border-subtle);
        color: var(--ink-secondary);
    }}

    .strip-pill-active {{
        background: rgba(37, 99, 235, 0.12);
        color: var(--brand-primary);
        border-color: var(--brand-primary);
        font-weight: 700;
    }}

    /* Sidebar Customization */
    [data-testid="stSidebar"] {{
        background-color: var(--sidebar-bg) !important;
        border-right: 1px solid var(--sidebar-border) !important;
        min-width: 18.5rem;
        max-width: 18.5rem;
    }}

    [data-testid="stSidebar"] > div:first-child {{
        padding: 1.2rem 1.1rem 2rem;
    }}

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span {{
        color: var(--sidebar-text) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
        color: var(--sidebar-text) !important;
    }}

    /* Metropolitan Brand Header in Sidebar */
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
        padding: 0.7rem 0.95rem;
        border-radius: 0.85rem;
        background: var(--brand-logo-bg);
        border: 1px solid var(--brand-logo-border);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        transition: transform 200ms ease, box-shadow 200ms ease, border-color 200ms ease;
    }}

    .brand-logo-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 22px var(--brand-glow);
        border-color: var(--brand-primary);
    }}

    .brand-logo-img {{
        max-width: 100%;
        height: auto;
        max-height: 52px;
        object-fit: contain;
        display: block;
    }}

    .brand-emblem-fallback {{
        font: 800 1.1rem 'Manrope', sans-serif;
        color: var(--brand-primary);
        letter-spacing: 0.05em;
    }}

    .brand-details {{
        display: flex;
        flex-direction: column;
        gap: 0.2rem;
    }}

    .brand-title {{
        color: var(--ink-primary) !important;
        font: 800 0.98rem 'Manrope', sans-serif;
        letter-spacing: -0.025em;
        line-height: 1.25;
    }}

    .brand-subtitle {{
        color: var(--ink-muted) !important;
        font-size: 0.73rem;
        font-weight: 500;
        line-height: 1.35;
    }}

    .brand-tags-row {{
        display: flex;
        gap: 0.4rem;
        flex-wrap: wrap;
        margin-top: 0.35rem;
    }}

    .brand-tag-blue {{
        display: inline-block;
        background: rgba(37, 99, 235, 0.12);
        color: var(--brand-primary);
        font-size: 0.63rem;
        font-weight: 700;
        padding: 0.18rem 0.5rem;
        border-radius: 0.35rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        border: 1px solid var(--brand-primary);
    }}

    .brand-tag-red {{
        display: inline-block;
        background: rgba(219, 13, 27, 0.12);
        color: var(--brand-secondary);
        font-size: 0.63rem;
        font-weight: 700;
        padding: 0.18rem 0.5rem;
        border-radius: 0.35rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
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
        color: var(--sidebar-text) !important;
        font-weight: 500;
        font-size: 0.88rem;
        transition: all 150ms ease;
        display: flex;
        align-items: center;
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label:hover {{
        background: var(--sidebar-surface);
        color: var(--ink-primary) !important;
        border-color: var(--border-subtle);
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {{
        background: var(--sidebar-surface);
        border-color: var(--brand-primary);
        border-left: 3px solid var(--brand-secondary);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) p {{
        color: var(--brand-primary) !important;
        font-weight: 700;
    }}

    /* Sidebar Status Card */
    .sidebar-status-card {{
        margin-top: 1.5rem;
        padding: 1rem;
        border: 1px solid var(--sidebar-border);
        border-left: 3px solid var(--brand-primary);
        border-radius: 0.85rem;
        background: var(--sidebar-surface);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }}

    .sidebar-status-kicker {{
        color: var(--brand-secondary);
        font-size: 0.66rem;
        font-weight: 800;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }}

    .sidebar-status-val {{
        margin-top: 0.35rem;
        color: var(--ink-primary);
        font: 700 0.95rem 'Manrope', sans-serif;
    }}

    .sidebar-status-sub {{
        margin-top: 0.2rem;
        color: var(--ink-muted);
        font-size: 0.75rem;
    }}

    /* Page Header */
    .page-kicker {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.35rem;
        color: var(--brand-primary);
        font-size: 0.74rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }}

    .kicker-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: var(--brand-secondary);
        box-shadow: 0 0 8px var(--brand-secondary);
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
        border-left: 5px solid var(--brand-secondary);
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
        width: 160px;
        height: 160px;
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
        0% {{ transform: scale(0.92); opacity: 0.8; box-shadow: 0 0 0 0 rgba(219, 13, 27, 0.7); }}
        70% {{ transform: scale(1.08); opacity: 1; box-shadow: 0 0 0 8px rgba(219, 13, 27, 0); }}
        100% {{ transform: scale(0.92); opacity: 0.8; box-shadow: 0 0 0 0 rgba(219, 13, 27, 0); }}
    }}

    .pulse-dot {{
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: var(--brand-secondary);
        animation: pulseGlow 2s infinite;
    }}

    .exec-synthesis-text {{
        font-size: 0.98rem;
        line-height: 1.72;
        color: var(--ink-primary);
        font-weight: 450;
    }}

    .exec-meta-grid {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.65rem;
        margin-top: 1.1rem;
        padding-top: 0.95rem;
        border-top: 1px solid var(--border-subtle);
    }}

    .exec-meta-chip {{
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.78rem;
        background: var(--chip-bg);
        border: 1px solid var(--chip-border);
        padding: 0.3rem 0.7rem;
        border-radius: 0.5rem;
        color: var(--ink-secondary);
        font-weight: 500;
    }}

    .exec-meta-chip strong {{
        color: var(--ink-primary);
        font-weight: 700;
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
        background: rgba(219, 13, 27, 0.12);
        color: var(--brand-secondary);
        border: 1px solid var(--brand-secondary);
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
        border-color: var(--brand-primary) !important;
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
        box-shadow: 0 6px 20px var(--brand-red-glow) !important;
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
        border-color: var(--brand-primary) !important;
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

    /* Custom Scrollbar for Sleek Appearance */
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
    </style>
    """


def configure_altair_theme(chart: alt.Chart, is_dark: bool) -> alt.Chart:
    """Apply unified, responsive Metropolitan Red & Blue theme to an Altair chart."""
    axis_color = "#94a3b8" if is_dark else "#475569"
    title_color = "#f8fafc" if is_dark else "#0f172a"
    grid_color = "rgba(255, 255, 255, 0.07)" if is_dark else "#e2e8f0"

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
