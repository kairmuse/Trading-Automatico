import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
import time
from datetime import datetime, timedelta

# ==========================================
# CONFIGURAZIONE PAGINA
# ==========================================
st.set_page_config(page_title="Quant Terminal", page_icon="◆", layout="wide")

# ==========================================
# FUNZIONI DI SUPPORTO GRAFICO
# ==========================================
def hex_to_rgba(hex_color, alpha=0.1):
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"

# ==========================================
# GESTIONE TEMA (CHIARO/SCURO)
# ==========================================
if 'theme' not in st.session_state:
    st.session_state.theme = 'dark'

COLORS_DARK = {
    "void": "#0B0E14", "sidebar": "#0F131B", "panel": "#141922", "panel_alt": "#191F2B",
    "border": "#232938", "primary": "#00E28A", "accent2": "#6C8CFF", "amber": "#F0A868",
    "positive": "#00E28A", "negative": "#FF5C7A", "text": "#EAEDF2", "text_dim": "#8B93A7", "text_faint": "#525A6B"
}

COLORS_LIGHT = {
    "void": "#F4F6F8", "sidebar": "#FFFFFF", "panel": "#FFFFFF", "panel_alt": "#F9FAFB",
    "border": "#E2E8F0", "primary": "#00A859", "accent2": "#4C6EF5", "amber": "#F59F00",
    "positive": "#00A859", "negative": "#E03131", "text": "#1E293B", "text_dim": "#475569", "text_faint": "#94A3B8"
}

COLORS = COLORS_LIGHT if st.session_state.theme == 'light' else COLORS_DARK
PLOTLY_TEMPLATE = "plotly_white" if st.session_state.theme == 'light' else "plotly_dark"

# ==========================================
# CSS PERSONALIZZATO
# ==========================================
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

    html, body, .stApp {{ background-color: {COLORS['void']}; }}
    * {{ font-family: 'Inter', sans-serif; }}
    
    /* Nascondi Sidebar e menu Hamburger */
    #MainMenu {{visibility: hidden;}}
    [data-testid="collapsedControl"] {{display: none;}}
    header {{visibility: hidden;}}

    /* Navbar personalizzata orizzontale */
    div[role="radiogroup"] {{
        display: flex; justify-content: center; gap: 20px;
        background-color: {COLORS['panel']}; padding: 12px;
        border-radius: 12px; border: 1px solid {COLORS['border']}; margin-bottom: 20px;
    }}
    div[role="radiogroup"] label {{
        background: transparent !important; border: none !important;
        padding: 8px 16px !important; border-radius: 8px !important; transition: 0.2s;
    }}
    div[role="radiogroup"] label:hover {{ background: {hex_to_rgba(COLORS['primary'],0.1)} !important; }}
    div[role="radiogroup"] p {{ font-weight: 600 !important; color: {COLORS['text_dim']} !important; font-size: 15px !important;}}
    div[role="radiogroup"] label[data-baseweb="radio"] input:checked + div p {{ color: {COLORS['primary']} !important; }}
    div[role="radiogroup"] label[data-baseweb="radio"] input:checked + div {{
        background: {hex_to_rgba(COLORS['primary'],0.1)} !important;
    }}

    .page-title {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 32px; color: {COLORS['text']}; letter-spacing: -0.5px; margin-bottom: 10px;}}
    .brand-accent {{ color: {COLORS['primary']}; }}
    
    .status-pill {{
        font-family: 'IBM Plex Mono', monospace; font-size: 12px; letter-spacing: 1px;
        padding: 6px 14px; border-radius: 20px; border: 1px solid; display: inline-flex; align-items: center; gap: 8px;
    }}
    .status-open {{ color: {COLORS['positive']}; border-color: {hex_to_rgba(COLORS['positive'],0.35)}; background: {hex_to_rgba(COLORS['positive'],0.08)}; }}
    .status-closed {{ color: {COLORS['text_dim']}; border-color: {COLORS['border']}; background: {COLORS['panel']}; }}

    /* Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {COLORS['panel']} !important;
        border: 1px solid {COLORS['border']} !important; border-radius: 10px !important;
        box-shadow: 0 4px 12px {hex_to_rgba('#000000', 0.05 if st.session_state.theme == 'light' else 0.4)};
    }}
    .card-title {{
        font-family: 'IBM Plex Mono', monospace; font-size: 11px; letter-spacing: 1.5px;
        text-transform: uppercase; color: {COLORS['text_faint']}; margin-bottom: 12px;
        display: flex; align-items: center; gap: 8px;
    }}
    .card-title::before {{ content: ""; width: 4px; height: 12px; background: {COLORS['primary']}; border-radius: 2px; display: inline-block; }}

    .stat-label {{ font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 1px; text-transform: uppercase; color: {COLORS['text_faint']}; margin-bottom: 4px; }}
    .stat-value {{ font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 18px; color: {COLORS['text']}; }}
    .stat-value-up {{ color: {COLORS['positive']}; }}
    .stat-value-down {{ color: {COLORS['negative']}; }}
    .sym-chip {{ font-weight: 600; color: {COLORS['text']}; font-family: 'Inter', sans-serif; }}

    /* Tabella */
    .pos-table {{ width: 100%; border-collapse: collapse; font-family: 'IBM Plex Mono', monospace; font-size: 13px; }}
    .pos-table th {{ text-align: left; padding: 12px 14px; color: {COLORS['text_faint']}; font-size: 10.5px; border-bottom: 1px solid {COLORS['border']}; }}
    .pos-table td {{ padding: 13px 14px; border-bottom: 1px solid {COLORS['border']}; color: {COLORS['text']}; }}
    .badge {{ padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block; }}
    .badge-up {{ background: {hex_to_rgba(COLORS['positive'],0.15)}; color: {COLORS['positive']}; }}
    .badge-down {{ background: {hex_to_rgba(COLORS['negative'],0.15)}; color: {COLORS['negative']}; }}

    /* Feed & Spotlight */
    .feed-row {{ display: flex; justify-content: space-between; padding: 8px 4px; border-bottom: 1px solid {COLORS['border']}; font-family: 'IBM Plex Mono', monospace; font-size: 12px; }}
    .spotlight-price {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 36px; color: {COLORS['text']}; line-height: 1.1; }}
    </style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    template=PLOTLY_TEMPLATE, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family="IBM Plex Mono, monospace", color=COLORS["text_dim"], size=11),
    margin=dict(l=0, r=10, t=40, b=0),
)

# ==========================================
# CREDENZIALI & FUNZIONI CORE
# ==========================================
ALPACA_API_KEY = st.secrets["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
BASE_URL = "https://paper-api.alpaca.markets"
HEADERS = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}

@st.cache_data(ttl=60)
