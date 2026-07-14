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
st.set_page_config(page_title="Quant Terminal | Live", page_icon="◆", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# DESIGN TOKENS
# ==========================================
COLORS = {
    "void": "#0B0E14",
    "sidebar": "#0F131B",
    "panel": "#141922",
    "panel_alt": "#191F2B",
    "border": "#232938",
    "primary": "#00E28A",      # verde spring - brand/accento principale
    "accent2": "#6C8CFF",      # blu-violetto - azioni secondarie
    "amber": "#F0A868",
    "positive": "#00E28A",
    "negative": "#FF5C7A",
    "text": "#EAEDF2",
    "text_dim": "#8B93A7",
    "text_faint": "#525A6B",
}

def hex_to_rgba(hex_color, alpha=0.1):
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"

def avatar_gradient(symbol):
    """Genera una coppia di colori coerente per simbolo, per l'avatar circolare in tabella."""
    palette_pairs = [
        ("#00E28A", "#00A8FF"), ("#6C8CFF", "#B26CFF"), ("#F0A868", "#FF6C6C"),
        ("#00D0C8", "#4FD1C5"), ("#FF6CAF", "#B26CFF"), ("#5CE0C0", "#00A8FF"),
    ]
    idx = sum(ord(c) for c in symbol) % len(palette_pairs)
    return palette_pairs[idx]

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

    html, body, .stApp {{ background-color: {COLORS['void']}; }}
    .stApp {{
        background:
            radial-gradient(circle at 12% 0%, {hex_to_rgba(COLORS['primary'], 0.09)} 0%, transparent 38%),
            radial-gradient(circle at 88% 8%, {hex_to_rgba(COLORS['accent2'], 0.07)} 0%, transparent 42%),
            {COLORS['void']};
    }}
    * {{ font-family: 'Inter', sans-serif; }}
    section.main > div {{ padding-top: 1.4rem; padding-bottom: 2rem; }}
    ::selection {{ background: {hex_to_rgba(COLORS['primary'],0.3)}; }}

    /* Scrollbar */
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: {COLORS['border']}; border-radius: 8px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {COLORS['text_faint']}; }}

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] > div:first-child {{
        background: linear-gradient(180deg, {COLORS['sidebar']} 0%, {COLORS['void']} 130%);
        border-right: 1px solid {COLORS['border']};
    }}
    .sb-brand {{
        font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 19px;
        color: {COLORS['text']}; padding: 10px 4px 20px 4px; letter-spacing: 0.3px;
        border-bottom: 1px solid {COLORS['border']}; margin-bottom: 16px;
        display: flex; align-items: center; gap: 8px;
    }}
    .sb-brand .diamond {{
        display: inline-block; width: 9px; height: 9px; border-radius: 2px;
        background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['accent2']});
        transform: rotate(45deg); box-shadow: 0 0 12px {hex_to_rgba(COLORS['primary'],0.7)};
    }}
    .sb-brand span {{
        background: linear-gradient(90deg, {COLORS['primary']}, #5CE0C0);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        padding: 10px 14px; border-radius: 8px; margin-bottom: 3px; width: 100%;
        transition: all 0.15s ease; border-left: 2px solid transparent;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: linear-gradient(90deg, {hex_to_rgba(COLORS['primary'],0.08)}, transparent);
        border-left: 2px solid {hex_to_rgba(COLORS['primary'],0.5)};
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label p {{
        font-size: 14px !important; color: {COLORS['text_dim']} !important; font-weight: 500;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"] input:checked + div {{
        color: {COLORS['primary']} !important;
    }}
    .sb-foot {{
        position: fixed; bottom: 20px; font-family: 'IBM Plex Mono', monospace;
        font-size: 10.5px; color: {COLORS['text_faint']}; padding: 10px 14px; line-height: 1.6;
        border-top: 1px solid {COLORS['border']}; width: 85%;
    }}

    /* ---------- Top bar ---------- */
    .page-title {{
        font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 24px; color: {COLORS['text']};
        letter-spacing: -0.3px;
    }}
    .page-sub {{ font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; color: {COLORS['text_faint']}; margin-top: 2px; letter-spacing: 0.5px; }}
    .status-pill {{
        font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; letter-spacing: 1px;
        padding: 7px 16px; border-radius: 20px; border: 1px solid; display: inline-flex;
        align-items: center; gap: 8px; backdrop-filter: blur(6px);
    }}
    .status-open {{
        color: {COLORS['positive']}; border-color: {hex_to_rgba(COLORS['positive'],0.35)};
        background: {hex_to_rgba(COLORS['positive'],0.08)}; box-shadow: 0 0 18px {hex_to_rgba(COLORS['positive'],0.15)};
    }}
    .status-closed {{ color: {COLORS['text_dim']}; border-color: {COLORS['border']}; background: {COLORS['panel']}; }}
    .pulse-dot {{
        width: 7px; height: 7px; border-radius: 50%; background: {COLORS['positive']};
        box-shadow: 0 0 0 0 {hex_to_rgba(COLORS['positive'],0.6)};
        animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
        0% {{ box-shadow: 0 0 0 0 {hex_to_rgba(COLORS['positive'],0.55)}; }}
        70% {{ box-shadow: 0 0 0 7px rgba(0,0,0,0); }}
        100% {{ box-shadow: 0 0 0 0 rgba(0,0,0,0); }}
    }}
    .dot-closed {{ width: 7px; height: 7px; border-radius: 50%; background: {COLORS['text_faint']}; }}

    /* ---------- Cards (contenitori nativi st.container(border=True)) ---------- */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: linear-gradient(160deg, {COLORS['panel_alt']} 0%, {COLORS['panel']} 100%) !important;
        border: 1px solid {COLORS['border']} !important; border-radius: 6px !important;
        box-shadow: 0 6px 18px -14px rgba(0,0,0,0.6); position: relative; overflow: hidden;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"]::before {{
        content: ""; position: absolute; top: 0; left: 0; right: 0; height: 1px; z-index: 1;
        background: linear-gradient(90deg, transparent, {hex_to_rgba(COLORS['primary'],0.4)}, transparent);
    }}
    .card-title {{
        font-family: 'IBM Plex Mono', monospace; font-size: 10.5px; letter-spacing: 1.8px;
        text-transform: uppercase; color: {COLORS['text_faint']}; margin-bottom: 12px;
        display: flex; align-items: center; gap: 8px;
    }}
    .card-title::before {{ content: ""; width: 3px; height: 11px; background: {COLORS['primary']}; border-radius: 1px; display: inline-block; }}

    /* ---------- Dense stat grid (stile pannello dati compatto) ---------- */
    .stat-grid {{ display: flex; flex-wrap: wrap; }}
    .stat-block {{
        flex: 1 1 0; min-width: 90px; padding: 0 14px; border-left: 1px solid {COLORS['border']};
    }}
    .stat-block:first-child {{ padding-left: 0; border-left: none; }}
    .stat-label {{
        font-family: 'IBM Plex Mono', monospace; font-size: 9.5px; letter-spacing: 1px;
        text-transform: uppercase; color: {COLORS['text_faint']}; margin-bottom: 4px;
    }}
    .stat-value {{ font-family: 'Space Grotesk', sans-serif; font-weight: 600; font-size: 17px; color: {COLORS['text']}; }}
    .stat-value-up {{ color: {COLORS['positive']}; }}
    .stat-value-down {{ color: {COLORS['negative']}; }}

    .verified-badge {{
        display: inline-flex; align-items: center; gap: 4px; font-family: 'IBM Plex Mono', monospace;
        font-size: 10px; letter-spacing: 0.5px; color: {COLORS['primary']};
        background: {hex_to_rgba(COLORS['primary'],0.1)}; border: 1px solid {hex_to_rgba(COLORS['primary'],0.3)};
        padding: 2px 8px; border-radius: 4px;
    }}
    .risk-gauge {{ width: 100%; height: 5px; border-radius: 3px; background: {COLORS['border']}; overflow: hidden; margin-top: 6px; }}
    .risk-gauge-fill {{ height: 100%; border-radius: 3px; }}

    /* ---------- Feed list (stile live feed compatto) ---------- */
    .feed-row {{
        display: flex; align-items: center; justify-content: space-between; padding: 8px 4px;
        border-bottom: 1px solid {COLORS['border']}; font-family: 'IBM Plex Mono', monospace; font-size: 12px;
    }}
    .feed-row:last-child {{ border-bottom: none; }}
    .feed-left {{ display: flex; align-items: center; gap: 8px; color: {COLORS['text_dim']}; overflow: hidden; }}
    .feed-dot {{ width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }}
    .feed-time {{ color: {COLORS['text_faint']}; font-size: 10.5px; flex-shrink: 0; }}

    /* ---------- Spotlight ---------- */
    .spotlight-price {{
        font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 40px; color: {COLORS['text']};
        letter-spacing: -0.5px; line-height: 1.1;
    }}
    .spotlight-change-up, .spotlight-change-down {{
        font-family:'IBM Plex Mono',monospace; font-size:14px; font-weight: 600;
        padding: 3px 10px; border-radius: 6px; display: inline-block; margin-top: 4px;
    }}
    .spotlight-change-up {{ color: {COLORS['positive']}; background: {hex_to_rgba(COLORS['positive'],0.1)}; }}
    .spotlight-change-down {{ color: {COLORS['negative']}; background: {hex_to_rgba(COLORS['negative'],0.1)}; }}
    .spotlight-meta {{ font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; color: {COLORS['text_faint']}; letter-spacing: 0.5px; line-height: 1.8; }}

    /* ---------- Metric cards ---------- */
    div[data-testid="stMetric"] {{
        background: linear-gradient(160deg, {COLORS['panel_alt']} 0%, {COLORS['panel']} 100%);
        border: 1px solid {COLORS['border']}; padding: 16px 18px; border-radius: 14px;
        box-shadow: 0 8px 22px -14px rgba(0,0,0,0.6); position: relative; overflow: hidden;
        transition: border-color 0.2s ease;
    }}
    div[data-testid="stMetric"]::before {{
        content: ""; position: absolute; top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent, {hex_to_rgba(COLORS['primary'],0.35)}, transparent);
    }}
    div[data-testid="stMetric"]:hover {{ border-color: {hex_to_rgba(COLORS['primary'],0.3)}; }}
    div[data-testid="stMetricLabel"] {{
        font-family: 'IBM Plex Mono', monospace !important; font-size: 10.5px !important;
        letter-spacing: 1.4px; text-transform: uppercase; color: {COLORS['text_faint']} !important;
    }}
    div[data-testid="stMetricValue"] {{
        font-family: 'Space Grotesk', sans-serif !important; font-size: 24px !important;
        font-weight: 600 !important; color: {COLORS['text']} !important;
    }}

    /* ---------- Tabs ---------- */
    button[data-baseweb="tab"] {{ font-family: 'Inter', sans-serif; font-size: 13.5px; color: {COLORS['text_dim']}; font-weight: 500; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {COLORS['primary']} !important; }}
    div[data-baseweb="tab-highlight"] {{ background: linear-gradient(90deg, {COLORS['primary']}, {COLORS['accent2']}) !important; height: 2.5px !important; }}
    div[data-baseweb="tab-border"] {{ background-color: {COLORS['border']} !important; }}

    /* ---------- Positions table ---------- */
    .pos-table {{ width: 100%; border-collapse: collapse; font-family: 'IBM Plex Mono', monospace; font-size: 13px; }}
    .pos-table th {{
        text-align: left; padding: 12px 14px; color: {COLORS['text_faint']}; font-size: 10.5px;
        letter-spacing: 1.4px; text-transform: uppercase; border-bottom: 1px solid {COLORS['border']};
    }}
    .pos-table td {{ padding: 13px 14px; border-bottom: 1px solid {COLORS['border']}; color: {COLORS['text']}; }}
    .pos-table tr {{ transition: background 0.15s ease; }}
    .pos-table tr:hover td {{ background: {hex_to_rgba(COLORS['primary'],0.04)}; }}
    .badge {{
        padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; display: inline-block;
        border: 1px solid transparent;
    }}
    .badge-up {{ background: {hex_to_rgba(COLORS['positive'],0.12)}; color: {COLORS['positive']}; border-color: {hex_to_rgba(COLORS['positive'],0.25)}; }}
    .badge-down {{ background: {hex_to_rgba(COLORS['negative'],0.12)}; color: {COLORS['negative']}; border-color: {hex_to_rgba(COLORS['negative'],0.25)}; }}
    .sym-cell {{ display: flex; align-items: center; gap: 10px; }}
    .sym-avatar {{
        width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
        font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 11px; color: #0B0E14;
        flex-shrink: 0;
    }}
    .sym-chip {{ font-weight: 600; color: {COLORS['text']}; font-family: 'Inter', sans-serif; }}

    hr {{ border-color: {COLORS['border']}; }}

    /* ---------- Log console ---------- */
    .log-console {{
        background: linear-gradient(160deg, #0D1017, {COLORS['void']}); color: {COLORS['primary']};
        font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; padding: 14px; border-radius: 10px;
        height: 190px; overflow-y: auto; border: 1px solid {COLORS['border']};
        box-shadow: inset 0 2px 12px rgba(0,0,0,0.4);
    }}
    .log-console p {{ margin: 3px 0; }}
    .log-console p::before {{ content: "▸ "; color: {COLORS['text_faint']}; }}

    /* ---------- Buttons ---------- */
    .stButton > button {{
        border-radius: 10px; border: 1px solid {COLORS['border']}; font-weight: 500;
        transition: all 0.15s ease; background: {COLORS['panel_alt']};
    }}
    .stButton > button:hover {{ border-color: {hex_to_rgba(COLORS['primary'],0.5)}; color: {COLORS['primary']}; }}
    button[kind="primary"] {{
        background: linear-gradient(135deg, {COLORS['negative']}, #E8465F) !important; border: none !important;
        box-shadow: 0 8px 20px -8px {hex_to_rgba(COLORS['negative'],0.6)} !important; font-weight: 600 !important;
    }}
    button[kind="primary"]:hover {{ box-shadow: 0 8px 24px -6px {hex_to_rgba(COLORS['negative'],0.8)} !important; color: white !important; }}

    /* ---------- Select boxes ---------- */
    div[data-baseweb="select"] > div {{
        background-color: {COLORS['panel_alt']} !important; border-color: {COLORS['border']} !important; border-radius: 10px !important;
    }}
    </style>
""", unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    template="plotly_dark", paper_bgcolor=COLORS["panel"], plot_bgcolor=COLORS["panel"],
    font=dict(family="IBM Plex Mono, monospace", color=COLORS["text_dim"], size=11),
    margin=dict(l=0, r=10, t=40, b=0),
)

# ==========================================
# CREDENZIALI (Da Streamlit Secrets)
# ==========================================
ALPACA_API_KEY = st.secrets["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
BASE_URL = "https://paper-api.alpaca.markets"
HEADERS = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}

# ==========================================
# FUNZIONI CORE & ANALISI
# ==========================================
@st.cache_data(ttl=60)
def get_account_info():
    resp = requests.get(f"{BASE_URL}/v2/account", headers=HEADERS)
    return resp.json() if resp.status_code == 200 else None

@st.cache_data(ttl=60)
def get_open_positions():
    resp = requests.get(f"{BASE_URL}/v2/positions", headers=HEADERS)
    return resp.json() if resp.status_code == 200 else []

@st.cache_data(ttl=300)
def get_portfolio_history(period="1M", timeframe="1D"):
    url = f"{BASE_URL}/v2/account/portfolio/history?period={period}&timeframe={timeframe}"
    resp = requests.get(url, headers=HEADERS)
    return resp.json() if resp.status_code == 200 else None

@st.cache_data(ttl=30)
def get_market_clock():
    resp = requests.get(f"{BASE_URL}/v2/clock", headers=HEADERS)
    return resp.json() if resp.status_code == 200 else None

def close_all_positions():
    resp = requests.delete(f"{BASE_URL}/v2/positions", headers=HEADERS)
    return resp.status_code in [200, 207]

def calcola_metriche_rischio(history):
    equity = pd.Series(history["equity"], dtype=float).dropna()
    if len(equity) < 3:
        return None
    rendimenti = equity.pct_change().dropna()
    sharpe = (rendimenti.mean() / rendimenti.std()) * np.sqrt(252) if rendimenti.std() != 0 else 0.0
    volatilita_ann = rendimenti.std() * np.sqrt(252) * 100
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax
    return {"sharpe": sharpe, "volatilita": volatilita_ann, "max_dd": drawdown.min() * 100,
            "rendimenti": rendimenti, "drawdown_series": drawdown}

@st.cache_data(ttl=60)
def get_spotlight_data(ticker):
    """Prezzo live, variazione e storico intraday per il pannello in evidenza.
    fast_info può restituire None fuori dagli orari di mercato: usiamo lo storico come fallback."""
    tk = yf.Ticker(ticker)
    info = tk.fast_info
    hist = tk.history(period="5d", interval="5m")

    prezzo = info.get("last_price")
    prev = info.get("previous_close")
    high = info.get("day_high")
    low = info.get("day_low")

    if not hist.empty:
        ultimo_giorno = hist.index[-1].date()
        hist_oggi = hist[hist.index.date == ultimo_giorno]
        if hist_oggi.empty:
            hist_oggi = hist
        if prezzo is None:
            prezzo = float(hist_oggi['Close'].iloc[-1])
        if high is None:
            high = float(hist_oggi['High'].max())
        if low is None:
            low = float(hist_oggi['Low'].min())
        if prev is None:
            giorni = sorted(set(hist.index.date))
            if len(giorni) > 1:
                hist_prec = hist[hist.index.date == giorni[-2]]
                prev = float(hist_prec['Close'].iloc[-1]) if not hist_prec.empty else float(hist_oggi['Close'].iloc[0])
            else:
                prev = float(hist_oggi['Close'].iloc[0])
        hist = hist_oggi
    else:
        prezzo, high, low, prev = prezzo or 0.0, high or 0.0, low or 0.0, prev or 0.0

    var_pct = ((prezzo - prev) / prev * 100) if prezzo and prev else 0
    return {"prezzo": prezzo, "prev": prev, "var_pct": var_pct, "high": high, "low": low, "hist": hist}

def crea_grafico_spotlight(hist, positivo=True):
    colore = COLORS['positive'] if positivo else COLORS['negative']
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], mode='lines',
                               line=dict(color=colore, width=2.5),
                               fill='tozeroy', fillcolor=hex_to_rgba(colore, 0.12)))
    fig.update_layout(height=260, **PLOTLY_LAYOUT)
    fig.update_xaxes(gridcolor=COLORS['border'], showgrid=False)
    fig.update_yaxes(gridcolor=COLORS['border'])
    return fig

def crea_grafico_equity(history):
    df = pd.DataFrame({'Data': pd.to_datetime(history['timestamp'], unit='s'), 'Equity': history['equity']})
    fig = go.Figure(go.Scatter(x=df['Data'], y=df['Equity'], mode='lines',
                               line=dict(color=COLORS['primary'], width=2.5),
                               fill='tozeroy', fillcolor=hex_to_rgba(COLORS['primary'], 0.1)))
    fig.update_layout(height=260, **PLOTLY_LAYOUT)
    fig.update_xaxes(gridcolor=COLORS['border'])
    fig.update_yaxes(gridcolor=COLORS['border'])
    return fig

def crea_grafico_drawdown(drawdown_series, timestamps):
    df = pd.DataFrame({'Data': pd.to_datetime(timestamps, unit='s')[-len(drawdown_series):], 'Drawdown': drawdown_series.values * 100})
    fig = go.Figure(go.Scatter(x=df['Data'], y=df['Drawdown'], mode='lines',
                               line=dict(color=COLORS['negative'], width=2),
                               fill='tozeroy', fillcolor=hex_to_rgba(COLORS['negative'], 0.1)))
    fig.update_layout(title="Drawdown (%)", height=200, **PLOTLY_LAYOUT)
    fig.update_xaxes(gridcolor=COLORS['border'])
    fig.update_yaxes(gridcolor=COLORS['border'])
    return fig

def crea_grafico_rendimenti(rendimenti):
    colori = [COLORS['positive'] if r >= 0 else COLORS['negative'] for r in rendimenti]
    fig = go.Figure(go.Bar(x=rendimenti.index, y=rendimenti.values * 100, marker_color=colori))
    fig.update_layout(title="Rendimenti Giornalieri (%)", height=200, showlegend=False, **PLOTLY_LAYOUT)
    fig.update_xaxes(gridcolor=COLORS['border'], showticklabels=False)
    fig.update_yaxes(gridcolor=COLORS['border'])
    return fig

def crea_grafico_allocazione(account, posizioni):
    labels = ['Liquidità (Cash)']
    equity = float(account['portfolio_value'])
    valore_investito = sum([float(p['market_value']) for p in posizioni])
    values = [equity - valore_investito]
    for p in posizioni:
        labels.append(p['symbol'])
        values.append(float(p['market_value']))
    palette = [COLORS['border'], COLORS['primary'], COLORS['accent2'], COLORS['amber'], COLORS['negative'], '#8C6FE8', '#4E9BF0']
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.65, textinfo='label+percent',
                                 marker=dict(colors=palette, line=dict(color=COLORS['panel'], width=2)))])
    fig.update_layout(height=290, showlegend=False, **PLOTLY_LAYOUT)
    return fig

def crea_grafico_candele(ticker):
    df = yf.Ticker(ticker).history(period="1d", interval="5m")
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                         increasing_line_color=COLORS['positive'], decreasing_line_color=COLORS['negative'])])
    fig.update_layout(title=f"Analisi Intraday: {ticker} (5m)", height=360, xaxis_rangeslider_visible=False, **PLOTLY_LAYOUT)
    fig.update_xaxes(gridcolor=COLORS['border'])
    fig.update_yaxes(gridcolor=COLORS['border'])
    return fig

def build_positions_dataframe(posizioni):
    rows = []
    for p in posizioni:
        rows.append({
            "Simbolo": p['symbol'],
            "Quantità": float(p['qty']),
            "Prezzo Medio": float(p['avg_entry_price']),
            "Prezzo Attuale": float(p['current_price']),
            "Valore": float(p['market_value']),
            "P&L $": float(p['unrealized_pl']),
            "P&L %": float(p['unrealized_plpc']) * 100,
        })
    return pd.DataFrame(rows)

def style_positions_df(df):
    def colora_pl(val):
        colore = COLORS['positive'] if val >= 0 else COLORS['negative']
        return f'color: {colore}; font-weight: 600;'
    styler = df.style
    metodo_colore = styler.map if hasattr(styler, "map") else styler.applymap
    return (metodo_colore(colora_pl, subset=['P&L $', 'P&L %'])
            .format({'Quantità': '{:.0f}', 'Prezzo Medio': '${:.2f}', 'Prezzo Attuale': '${:.2f}',
                     'Valore': '${:,.2f}', 'P&L $': '${:+,.2f}', 'P&L %': '{:+.2f}%'}))

def mostra_tabella_posizioni(posizioni, key_prefix="pos"):
    """Tabella posizioni interattiva: filtro per simbolo, filtro profitto/perdita, ordinamento nativo (click sull'intestazione colonna)."""
    if not posizioni:
        st.info("Portafoglio 100% Cash. Nessuna posizione aperta.")
        return
    df = build_positions_dataframe(posizioni)
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        simboli_sel = st.multiselect("Filtra per simbolo", options=df['Simbolo'].tolist(),
                                      default=df['Simbolo'].tolist(), label_visibility="collapsed",
                                      placeholder="Filtra per simbolo...", key=f"{key_prefix}_sym")
    with col_f2:
        filtro_pl = st.selectbox("Filtro P&L", ["Tutte", "Solo in profitto", "Solo in perdita"],
                                  label_visibility="collapsed", key=f"{key_prefix}_pl")
    df_f = df[df['Simbolo'].isin(simboli_sel)] if simboli_sel else df.iloc[0:0]
    if filtro_pl == "Solo in profitto":
        df_f = df_f[df_f['P&L $'] >= 0]
    elif filtro_pl == "Solo in perdita":
        df_f = df_f[df_f['P&L $'] < 0]
    st.caption(f"{len(df_f)} di {len(df)} posizioni · clicca un'intestazione di colonna per ordinare")
    st.dataframe(style_positions_df(df_f), use_container_width=True, hide_index=True)

def build_orders_dataframe(ordini):
    rows = []
    for o in ordini:
        prezzo = o.get('filled_avg_price')
        rows.append({
            "Simbolo": o.get('symbol', ''),
            "Lato": (o.get('side') or '').upper(),
            "Quantità": float(o.get('filled_qty') or o.get('qty') or 0),
            "Prezzo": float(prezzo) if prezzo else None,
            "Data": (o.get('filled_at') or o.get('submitted_at') or '')[:16].replace('T', ' '),
        })
    return pd.DataFrame(rows)

def mostra_tabella_ordini(key_prefix="ord"):
    """Storico ordini chiusi con filtro periodo, filtro lato (buy/sell) e ordinamento nativo."""
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        periodo = st.selectbox("Periodo", ["Ultimi 7 giorni", "Ultimi 30 giorni", "Ultimi 90 giorni"],
                                index=1, label_visibility="collapsed", key=f"{key_prefix}_periodo")
    with col_d2:
        lato_filtro = st.selectbox("Lato", ["Tutti", "Buy", "Sell"], label_visibility="collapsed", key=f"{key_prefix}_lato")
    giorni_map = {"Ultimi 7 giorni": 7, "Ultimi 30 giorni": 30, "Ultimi 90 giorni": 90}
    ordini = get_recent_orders(giorni_map[periodo])
    if not ordini:
        st.info("Nessun ordine chiuso nel periodo selezionato.")
        return
    df = build_orders_dataframe(ordini)
    if lato_filtro != "Tutti":
        df = df[df['Lato'] == lato_filtro.upper()]
    st.caption(f"{len(df)} ordini · clicca un'intestazione di colonna per ordinare")
    st.dataframe(
        df.style.format({'Quantità': '{:.0f}', 'Prezzo': '${:.2f}'}),
        use_container_width=True, hide_index=True,
        column_config={"Data": st.column_config.TextColumn(width="medium")},
    )

def render_positions_table(posizioni):
    righe = ""
    for p in posizioni:
        pl_val = float(p['unrealized_pl'])
        pl_perc = float(p['unrealized_plpc']) * 100
        badge_class = "badge-up" if pl_val >= 0 else "badge-down"
        segno = "+" if pl_val >= 0 else ""
        righe += f"""
        <tr>
            <td><span class="sym-chip">{p['symbol']}</span></td>
            <td>{p['qty']}</td>
            <td>${float(p['avg_entry_price']):.2f}</td>
            <td>${float(p['current_price']):.2f}</td>
            <td>${float(p['market_value']):,.2f}</td>
            <td><span class="badge {badge_class}">{segno}${pl_val:.2f} ({segno}{pl_perc:.2f}%)</span></td>
        </tr>"""
    html = f"""
    <table class="pos-table">
        <thead><tr>
            <th>Simbolo</th><th>Qtà</th><th>Prezzo Medio</th><th>Prezzo Attuale</th><th>Valore</th><th>P&amp;L</th>
        </tr></thead>
        <tbody>{righe}</tbody>
    </table>"""
    return html

def render_account_summary(account, posizioni, eq, bp, pnl, leva):
    """Card riassuntiva stile 'profilo' del riferimento: badge verificato + griglia di statistiche."""
    account_num = account.get('account_number', 'N/D')
    pnl_class = "stat-value-up" if pnl >= 0 else "stat-value-down"
    pnl_segno = "+" if pnl >= 0 else ""
    if leva < 1:
        risk_color, risk_label, risk_pct = COLORS['positive'], "BASSO", min(leva * 40, 100)
    elif leva < 2:
        risk_color, risk_label, risk_pct = COLORS['amber'], "MEDIO", min(leva * 40, 100)
    else:
        risk_color, risk_label, risk_pct = COLORS['negative'], "ALTO", 100
    return f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
        <div>
            <div class="stat-label">ACCOUNT ID</div>
            <div style="font-family:'IBM Plex Mono',monospace; font-size:13px; color:{COLORS['text']};">{account_num}</div>
        </div>
        <span class="verified-badge">✓ PAPER LIVE</span>
    </div>
    <div class="stat-label">NET EQUITY</div>
    <div class="stat-value" style="font-size:30px; margin-bottom:14px;">${eq:,.2f}</div>
    <div class="stat-grid">
        <div class="stat-block">
            <div class="stat-label">DAY P&amp;L</div>
            <div class="stat-value {pnl_class}">{pnl_segno}${pnl:,.2f}</div>
        </div>
        <div class="stat-block">
            <div class="stat-label">BUYING POWER</div>
            <div class="stat-value">${bp:,.0f}</div>
        </div>
        <div class="stat-block">
            <div class="stat-label">POSIZIONI</div>
            <div class="stat-value">{len(posizioni)}</div>
        </div>
    </div>
    <div style="margin-top:14px;">
        <div class="stat-label">LEVA / RISCHIO ESPOSIZIONE — {risk_label}</div>
        <div class="risk-gauge"><div class="risk-gauge-fill" style="width:{risk_pct}%; background:{risk_color};"></div></div>
    </div>
    """

def render_best_worst_position(posizioni):
    """Miglior e peggior posizione aperta per P&L percentuale — dati reali dal portafoglio corrente."""
    if not posizioni:
        return "<div class='stat-label'>Nessuna posizione aperta da confrontare.</div>"
    ordinate = sorted(posizioni, key=lambda p: float(p['unrealized_plpc']), reverse=True)
    migliore, peggiore = ordinate[0], ordinate[-1]

    def blocco(p, etichetta):
        pl_perc = float(p['unrealized_plpc']) * 100
        pl_val = float(p['unrealized_pl'])
        cls = "stat-value-up" if pl_val >= 0 else "stat-value-down"
        segno = "+" if pl_val >= 0 else ""
        return f"""
        <div style="margin-bottom:14px;">
            <div class="stat-label">{etichetta}</div>
            <div style="display:flex; justify-content:space-between; align-items:baseline;">
                <span class="sym-chip" style="font-size:15px;">{p['symbol']}</span>
                <span class="stat-value {cls}" style="font-size:16px;">{segno}{pl_perc:.2f}%</span>
            </div>
            <div class="stat-label" style="margin-top:2px;">{segno}${pl_val:.2f} · {p['qty']} QTY @ ${float(p['avg_entry_price']):.2f}</div>
        </div>"""

    html = blocco(migliore, "MIGLIOR POSIZIONE")
    if peggiore['symbol'] != migliore['symbol']:
        html += blocco(peggiore, "PEGGIOR POSIZIONE")
    return html

def render_feed_list(messaggi):
    righe = ""
    for msg in messaggi:
        if msg.startswith("Nessun") or msg.startswith("Nessuna"):
            dot_color = COLORS['text_faint']
        elif msg.startswith("⚠"):
            dot_color = COLORS['amber']
        else:
            dot_color = COLORS['primary']
        righe += f"""
        <div class="feed-row">
            <div class="feed-left"><span class="feed-dot" style="background:{dot_color};"></span><span>{msg}</span></div>
        </div>"""
    return f"<div>{righe}</div>"

@st.cache_data(ttl=60)
def get_watchlist_snapshot(tickers):
    righe = []
    for t in tickers:
        try:
            # Usiamo history invece di fast_info perché è stabile a mercati chiusi
            df = yf.Ticker(t).history(period="2d")
            if len(df) >= 2:
                prezzo = float(df['Close'].iloc[-1])
                prev = float(df['Close'].iloc[-2])
                righe.append({"symbol": t, "price": prezzo, "change": (prezzo - prev) / prev * 100})
            elif len(df) == 1:
                prezzo = float(df['Close'].iloc[-1])
                righe.append({"symbol": t, "price": prezzo, "change": 0.0})
        except Exception:
            continue
    return righe

def render_watchlist(tickers):
    dati = get_watchlist_snapshot(tickers)
    if not dati:
        return "<div class='stat-label'>Nessun dato disponibile per i simboli inseriti.</div>"
    righe = ""
    for r in dati:
        positivo = r['change'] >= 0
        colore = COLORS['positive'] if positivo else COLORS['negative']
        freccia = "▲" if positivo else "▼"
        righe += f"""
        <div class="feed-row">
            <div class="feed-left"><span class="sym-chip">{r['symbol']}</span></div>
            <div style="text-align:right;">
                <span style="color:{COLORS['text']}; font-family:'IBM Plex Mono',monospace; font-size:12.5px;">${r['price']:.2f}</span>
                <span style="color:{colore}; font-family:'IBM Plex Mono',monospace; font-size:11.5px; margin-left:8px;">{freccia} {abs(r['change']):.2f}%</span>
            </div>
        </div>"""
    return f"<div>{righe}</div>"

def render_cash_gauge(account, posizioni, eq):
    valore_investito = sum(float(p['market_value']) for p in posizioni)
    cash = eq - valore_investito
    pct_investito = (valore_investito / eq * 100) if eq else 0
    pct_cash = max(0, 100 - pct_investito)
    return f"""
    <div class="stat-grid" style="margin-bottom:12px;">
        <div class="stat-block">
            <div class="stat-label">LIQUIDITÀ</div>
            <div class="stat-value">${cash:,.2f}</div>
        </div>
        <div class="stat-block">
            <div class="stat-label">INVESTITO</div>
            <div class="stat-value">${valore_investito:,.2f}</div>
        </div>
    </div>
    <div style="display:flex; height:10px; border-radius:5px; overflow:hidden; background:{COLORS['border']};">
        <div style="width:{pct_investito}%; background:{COLORS['primary']};"></div>
        <div style="width:{pct_cash}%; background:{COLORS['border']};"></div>
    </div>
    <div style="display:flex; justify-content:space-between; margin-top:6px;">
        <span class="stat-label">INVESTITO {pct_investito:.0f}%</span>
        <span class="stat-label">CASH {pct_cash:.0f}%</span>
    </div>
    """

@st.cache_data(ttl=120)
def get_recent_orders(giorni=30):
    after = (datetime.utcnow() - timedelta(days=giorni)).strftime('%Y-%m-%dT%H:%M:%SZ')
    url = f"{BASE_URL}/v2/orders?status=closed&limit=200&direction=desc&after={after}"
    resp = requests.get(url, headers=HEADERS)
    return resp.json() if resp.status_code == 200 else []

def render_recent_orders(ordini):
    if not ordini:
        return "<div class='stat-label'>Nessun ordine chiuso disponibile.</div>"
    righe = ""
    for o in ordini:
        side = (o.get('side') or '').upper()
        side_color = COLORS['positive'] if side == 'BUY' else COLORS['negative']
        prezzo = o.get('filled_avg_price')
        prezzo_str = f"${float(prezzo):.2f}" if prezzo else "—"
        qty = o.get('filled_qty') or o.get('qty') or '—'
        data_raw = o.get('filled_at') or o.get('submitted_at') or ''
        data_str = data_raw[:16].replace('T', ' ') if data_raw else ''
        righe += f"""
        <div class="feed-row">
            <div class="feed-left">
                <span class="badge" style="background:{hex_to_rgba(side_color,0.12)}; color:{side_color}; padding:2px 9px; font-size:10.5px;">{side}</span>
                <span class="sym-chip">{o.get('symbol','')}</span>
                <span style="color:{COLORS['text_faint']};">{qty} @ {prezzo_str}</span>
            </div>
            <span class="feed-time">{data_str}</span>
        </div>"""
    return f"<div>{righe}</div>"

@st.cache_data(ttl=60)
def get_telegram_updates():
    if not TELEGRAM_TOKEN:
        return ["⚠ TELEGRAM_TOKEN mancante o vuoto in secrets.toml"]
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 409:
            return ["⚠ Conflitto (409): un webhook è già attivo su questo bot — getUpdates non può essere usato insieme a un webhook."]
        if resp.status_code == 401:
            return ["⚠ Token non valido (401): controlla TELEGRAM_TOKEN in secrets.toml."]
        if resp.status_code != 200:
            return [f"⚠ Errore Telegram: HTTP {resp.status_code} — {resp.text[:150]}"]
        dati = resp.json()
        if not dati.get('ok', False):
            return [f"⚠ Telegram ha risposto ok=false: {dati.get('description', 'errore sconosciuto')}"]
        risultati = dati.get('result', [])
        if not risultati:
            return ["Nessun messaggio in coda per questo bot (nessuna nuova operazione o updates già confermati altrove)."]
        messaggi = []
        for update in reversed(risultati[-5:]):
            if 'message' in update and 'text' in update['message']:
                testo = update['message']['text']
                data = datetime.fromtimestamp(update['message']['date']).strftime('%Y-%m-%d %H:%M:%S')
                messaggi.append(f"[{data}] SYS_MSG: {testo[:100]}...")
        return messaggi if messaggi else ["Nessun messaggio testuale trovato negli updates recenti."]
    except requests.exceptions.RequestException as e:
        return [f"⚠ Errore di connessione a Telegram: {e}"]

# ==========================================
# SIDEBAR: NAVIGAZIONE
# ==========================================
with st.sidebar:
    st.markdown('<div class="sb-brand">◆ QUANT<span>TERMINAL</span></div>', unsafe_allow_html=True)
    
    # Rimosse le emoji dalla lista delle pagine
    pagina = st.radio("Naviga", ["Home", "Posizioni", "Analisi Rischio", "Log & Override"],
                       label_visibility="collapsed")

    with st.expander("⚙️ Personalizza Widget"):
        st.caption("Attiva o disattiva i pannelli della Home")
        WIDGET_DEFAULTS = {
            "w_account": ("Account Summary", True),
            "w_bestworst": ("Top / Bottom Posizione", True),
            "w_spotlight": ("Titolo in Evidenza", True),
            "w_equity": ("Curva di Equity", True),
            "w_alloc": ("Asset Allocation", True),
            "w_cash": ("Cash vs Investito", True),
            "w_watchlist": ("Watchlist", True),
            "w_positions": ("Posizioni Aperte", True),
            "w_orders": ("Ordini Recenti", True),
            "w_feed": ("Live Feed", True),
        }
        for key, (label, default) in WIDGET_DEFAULTS.items():
            if key not in st.session_state:
                st.session_state[key] = default
            st.session_state[key] = st.checkbox(label, value=st.session_state[key], key=f"chk_{key}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("Simboli Watchlist (separati da virgola)")
        watchlist_input = st.text_input("watchlist_input", value=st.session_state.get("watchlist_tickers", "AAPL, MSFT, GOOGL, AMZN, AMD, NVDA, TSLA, COIN, AVGO, META, NFLX, SPOT, UBER, IWM, PLTR, SOFI, ROKU, HOOD, AFRM"), label_visibility="collapsed")
        st.session_state["watchlist_tickers"] = watchlist_input

    st.markdown("<div class='card-title' style='margin-top:6px;'>Periodo Analisi</div>", unsafe_allow_html=True)
    PERIODI = {
        "1 Settimana": ("1W", "15Min"), "1 Mese": ("1M", "1D"), "3 Mesi": ("3M", "1D"),
        "6 Mesi": ("6M", "1D"), "1 Anno": ("1A", "1D"), "Da Inizio": ("all", "1D"),
    }
    periodo_scelto = st.selectbox("Periodo Analisi", list(PERIODI.keys()), index=1, label_visibility="collapsed")
    period_param, timeframe_param = PERIODI[periodo_scelto]

    st.markdown(f"<div class='sb-foot'>PAPER TRADING · ALPACA<br>{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>", unsafe_allow_html=True)

# ==========================================
# DATI COMUNI
# ==========================================
clock = get_market_clock()
mercato_aperto = clock.get("is_open") if clock else None
account = get_account_info()
posizioni = get_open_positions()
history = get_portfolio_history(period_param, timeframe_param)
metriche = calcola_metriche_rischio(history) if history else None

# Avendo rimosso le emoji, il titolo della pagina è semplicemente la stringa 'pagina'
titolo_pagina = pagina

col_t, col_s = st.columns([6, 1])
with col_t:
    st.markdown(f"<div class='page-title'>{titolo_pagina}</div>", unsafe_allow_html=True)
with col_s:
    if mercato_aperto is True:
        st.markdown('<div class="status-pill status-open">● MARKET OPEN</div>', unsafe_allow_html=True)
    elif mercato_aperto is False:
        st.markdown('<div class="status-pill status-closed">○ MARKET CLOSED</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-pill status-closed">○ N/A</div>', unsafe_allow_html=True)
st.markdown("<div style='border-bottom:1px solid #232938; margin: 10px 0 18px 0;'></div>", unsafe_allow_html=True)

if not account:
    st.error("Connessione API Alpaca fallita.")
    st.stop()

eq = float(account['portfolio_value'])
bp = float(account['buying_power'])
pnl = float(account['equity']) - float(account['last_equity'])
esposizione_totale = sum([float(p['market_value']) for p in posizioni])
leva = esposizione_totale / eq if eq else 0

# ==========================================
# PAGINA: HOME
# ==========================================
if pagina == "Home":
    if st.button("↻ Aggiorna Dati Live"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    simboli_disponibili = [p['symbol'] for p in posizioni] if posizioni else []
    simboli_disponibili = list(dict.fromkeys(simboli_disponibili + ["AAPL", "MSFT", "GOOGL", "AMZN", "AMD", "NVDA", "TSLA"]))
    watchlist_tickers = [t.strip().upper() for t in st.session_state.get("watchlist_tickers", "AAPL, MSFT, GOOGL, AMZN, AMD, NVDA, TSLA, COIN, AVGO, META, NFLX, SPOT, UBER, IWM, PLTR, SOFI, ROKU, HOOD, AFRM").split(",") if t.strip()]

    def w_account_summary():
        with st.container(border=True):
            st.markdown('<div class="card-title">Account Summary</div>', unsafe_allow_html=True)
            st.markdown(render_account_summary(account, posizioni, eq, bp, pnl, leva), unsafe_allow_html=True)

    def w_best_worst():
        with st.container(border=True):
            st.markdown('<div class="card-title">Top / Bottom Posizione</div>', unsafe_allow_html=True)
            st.markdown(render_best_worst_position(posizioni), unsafe_allow_html=True)

    def w_spotlight():
        with st.container(border=True):
            ticker_spot = st.selectbox("Titolo in evidenza", simboli_disponibili, label_visibility="collapsed")
            dati_spot = get_spotlight_data(ticker_spot)
            if dati_spot['prezzo']:
                positivo = dati_spot['var_pct'] >= 0
                change_class = "spotlight-change-up" if positivo else "spotlight-change-down"
                freccia = "▲" if positivo else "▼"
                st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:flex-end;">
                        <div>
                            <div class="spotlight-meta">{ticker_spot}</div>
                            <div class="spotlight-price" style="font-size:28px;">${dati_spot['prezzo']:.2f}</div>
                            <div class="{change_class}">{freccia} {dati_spot['var_pct']:.2f}%</div>
                        </div>
                        <div class="spotlight-meta" style="text-align:right;">
                            HIGH ${dati_spot['high']:.2f}<br>LOW ${dati_spot['low']:.2f}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if not dati_spot['hist'].empty:
                    st.plotly_chart(crea_grafico_spotlight(dati_spot['hist'], positivo), use_container_width=True)
            else:
                st.info(f"Dati non disponibili per {ticker_spot} in questo momento.")

    def w_equity():
        with st.container(border=True):
            st.markdown(f'<div class="card-title">Curva di Equity — {periodo_scelto}</div>', unsafe_allow_html=True)
            if history:
                st.plotly_chart(crea_grafico_equity(history), use_container_width=True)
            else:
                st.info("Storico non disponibile.")

    def w_alloc():
        with st.container(border=True):
            st.markdown('<div class="card-title">Asset Allocation</div>', unsafe_allow_html=True)
            st.plotly_chart(crea_grafico_allocazione(account, posizioni), use_container_width=True)

    def w_cash():
        with st.container(border=True):
            st.markdown('<div class="card-title">Cash vs Investito</div>', unsafe_allow_html=True)
            st.markdown(render_cash_gauge(account, posizioni, eq), unsafe_allow_html=True)

    def w_watchlist():
        with st.container(border=True):
            st.markdown('<div class="card-title">Watchlist</div>', unsafe_allow_html=True)
            st.markdown(render_watchlist(watchlist_tickers), unsafe_allow_html=True)

    def w_positions():
        with st.container(border=True):
            st.markdown('<div class="card-title">Posizioni Aperte</div>', unsafe_allow_html=True)
            mostra_tabella_posizioni(posizioni, key_prefix="home_pos")

    def w_orders():
        with st.container(border=True):
            st.markdown('<div class="card-title">Ordini Recenti</div>', unsafe_allow_html=True)
            mostra_tabella_ordini(key_prefix="home_ord")

    def w_feed():
        with st.container(border=True):
            st.markdown('<div class="card-title">Live Feed</div>', unsafe_allow_html=True)
            st.markdown(render_feed_list(get_telegram_updates()), unsafe_allow_html=True)

    def render_row(widgets):
        """widgets: lista di (chiave_toggle, funzione, peso_colonna). Disegna solo quelli attivi, ridistribuendo lo spazio."""
        attivi = [(fn, peso) for chiave, fn, peso in widgets if st.session_state.get(chiave, True)]
        if not attivi:
            return
        cols = st.columns([peso for _, peso in attivi])
        for col, (fn, _) in zip(cols, attivi):
            with col:
                fn()

    render_row([("w_account", w_account_summary, 1.1), ("w_bestworst", w_best_worst, 1), ("w_spotlight", w_spotlight, 1.4)])
    st.markdown("<br>", unsafe_allow_html=True)
    render_row([("w_equity", w_equity, 2), ("w_alloc", w_alloc, 1)])
    st.markdown("<br>", unsafe_allow_html=True)
    render_row([("w_cash", w_cash, 1), ("w_watchlist", w_watchlist, 1)])
    st.markdown("<br>", unsafe_allow_html=True)
    render_row([("w_positions", w_positions, 2), ("w_orders", w_orders, 1)])
    st.markdown("<br>", unsafe_allow_html=True)
    render_row([("w_feed", w_feed, 1)])

    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('<div class="card-title">Override</div>', unsafe_allow_html=True)
        st.caption("Liquidazione immediata a prezzo di mercato.")
        if st.button("🛑 CHIUDI TUTTE LE POSIZIONI", type="primary", use_container_width=True):
            with st.spinner("Invio ordine al broker..."):
                if close_all_positions():
                    st.success("Conto Flat.")
                    time.sleep(1)
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("Errore di routing.")

# ==========================================
# PAGINA: POSIZIONI
# ==========================================
elif pagina == "Posizioni":
    tab_attive, tab_grafico, tab_ordini = st.tabs(["Posizioni Aperte", "Grafico Titolo", "Ordini Recenti"])

    with tab_attive:
        with st.container(border=True):
            mostra_tabella_posizioni(posizioni, key_prefix="pagina_pos")

    with tab_grafico:
        if posizioni:
            ticker_scelto = st.selectbox("🔍 Ispeziona Titolo", [p['symbol'] for p in posizioni])
        else:
            st.info("Nessuna posizione in portafoglio: viene mostrato SPY come riferimento.")
            ticker_scelto = "SPY"
        with st.container(border=True):
            st.plotly_chart(crea_grafico_candele(ticker_scelto), use_container_width=True)

    with tab_ordini:
        with st.container(border=True):
            mostra_tabella_ordini(key_prefix="pagina_ord")

# ==========================================
# PAGINA: ANALISI RISCHIO
# ==========================================
elif pagina == "Analisi Rischio":
    st.caption(f"Periodo di analisi: {periodo_scelto} · modificabile dalla sidebar")
    r1, r2, r3, r4 = st.columns(4)
    if metriche:
        r1.metric("SHARPE RATIO", f"{metriche['sharpe']:.2f}")
        r2.metric("VOLATILITÀ ANN.", f"{metriche['volatilita']:.2f}%")
        r3.metric("MAX DRAWDOWN", f"{metriche['max_dd']:.2f}%")
    else:
        r1.metric("SHARPE RATIO", "N/D")
        r2.metric("VOLATILITÀ ANN.", "N/D")
        r3.metric("MAX DRAWDOWN", "N/D")
    if posizioni:
        in_profitto = sum(1 for p in posizioni if float(p['unrealized_pl']) > 0)
        r4.metric("POSIZIONI IN PROFITTO", f"{in_profitto/len(posizioni)*100:.0f}%", f"{in_profitto}/{len(posizioni)}")
    else:
        r4.metric("POSIZIONI IN PROFITTO", "N/D")

    st.markdown("<br>", unsafe_allow_html=True)
    if metriche:
        col_dd, col_ret = st.columns(2)
        with col_dd:
            with st.container(border=True):
                st.plotly_chart(crea_grafico_drawdown(metriche['drawdown_series'], history['timestamp']), use_container_width=True)
        with col_ret:
            with st.container(border=True):
                st.plotly_chart(crea_grafico_rendimenti(metriche['rendimenti']), use_container_width=True)
    else:
        st.info("Dati storici insufficienti per calcolare le metriche di rischio.")

# ==========================================
# PAGINA: LOG & OVERRIDE
# ==========================================
elif pagina == "Log & Override":
    col_logs, col_panic = st.columns([3, 1])
    with col_logs:
        with st.container(border=True):
            st.markdown('<div class="card-title">System Logs</div>', unsafe_allow_html=True)
            st.markdown(render_feed_list(get_telegram_updates()), unsafe_allow_html=True)
    with col_panic:
        with st.container(border=True):
            st.markdown('<div class="card-title">Override</div>', unsafe_allow_html=True)
            st.caption("Liquidazione immediata a prezzo di mercato.")
            if st.button("🛑 CHIUDI TUTTE LE POSIZIONI", type="primary", use_container_width=True):
                with st.spinner("Invio ordine al broker..."):
                    if close_all_positions():
                        st.success("Conto Flat.")
                        time.sleep(1)
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Errore di routing.")
