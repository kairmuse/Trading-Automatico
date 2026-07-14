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
    if len(equity) < 3: return None
    rendimenti = equity.pct_change().dropna()
    sharpe = (rendimenti.mean() / rendimenti.std()) * np.sqrt(252) if rendimenti.std() != 0 else 0.0
    volatilita_ann = rendimenti.std() * np.sqrt(252) * 100
    cummax = equity.cummax()
    drawdown = (equity - cummax) / cummax
    return {"sharpe": sharpe, "volatilita": volatilita_ann, "max_dd": drawdown.min() * 100, "rendimenti": rendimenti, "drawdown_series": drawdown}

@st.cache_data(ttl=60)
def get_spotlight_data(ticker):
    tk = yf.Ticker(ticker)
    info = tk.fast_info
    hist = tk.history(period="5d", interval="5m")
    prezzo, prev, high, low = info.get("last_price"), info.get("previous_close"), info.get("day_high"), info.get("day_low")
    
    if not hist.empty:
        ultimo_giorno = hist.index[-1].date()
        hist_oggi = hist[hist.index.date == ultimo_giorno]
        if hist_oggi.empty: hist_oggi = hist
        if prezzo is None: prezzo = float(hist_oggi['Close'].iloc[-1])
        if high is None: high = float(hist_oggi['High'].max())
        if low is None: low = float(hist_oggi['Low'].min())
        if prev is None:
            giorni = sorted(set(hist.index.date))
            prev = float(hist[hist.index.date == giorni[-2]]['Close'].iloc[-1]) if len(giorni) > 1 else float(hist_oggi['Close'].iloc[0])
        hist = hist_oggi
    else:
        prezzo, high, low, prev = prezzo or 0.0, high or 0.0, low or 0.0, prev or 0.0

    return {"prezzo": prezzo, "prev": prev, "var_pct": ((prezzo - prev) / prev * 100) if prezzo and prev else 0, "high": high, "low": low, "hist": hist}

@st.cache_data(ttl=60)
def get_watchlist_snapshot(tickers):
    righe = []
    for t in tickers:
        try:
            df = yf.Ticker(t).history(period="2d")
            if len(df) >= 2:
                prezzo, prev = float(df['Close'].iloc[-1]), float(df['Close'].iloc[-2])
                righe.append({"symbol": t, "price": prezzo, "change": (prezzo - prev) / prev * 100})
            elif len(df) == 1:
                righe.append({"symbol": t, "price": float(df['Close'].iloc[-1]), "change": 0.0})
        except Exception: continue
    return righe

@st.cache_data(ttl=120)
def get_recent_orders(giorni=30):
    after = (datetime.utcnow() - timedelta(days=giorni)).strftime('%Y-%m-%dT%H:%M:%SZ')
    url = f"{BASE_URL}/v2/orders?status=closed&limit=200&direction=desc&after={after}"
    resp = requests.get(url, headers=HEADERS)
    return resp.json() if resp.status_code == 200 else []

@st.cache_data(ttl=60)
def get_telegram_updates():
    if not TELEGRAM_TOKEN: return ["⚠ Token Telegram mancante."]
    try:
        resp = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", timeout=10)
        if resp.status_code == 409: return ["⚠ Conflitto Webhook Telegram."]
        if resp.status_code != 200: return [f"⚠ Errore Telegram."]
        risultati = resp.json().get('result', [])
        messaggi = [f"[{datetime.fromtimestamp(u['message']['date']).strftime('%H:%M:%S')}] SYS: {u['message']['text'][:80]}" for u in reversed(risultati[-5:]) if 'message' in u and 'text' in u['message']]
        return messaggi if messaggi else ["Nessun log recente."]
    except: return ["⚠ Errore connessione Telegram."]

# ==========================================
# RENDER FUNZIONI GRAFICI
# ==========================================
def crea_grafico_spotlight(hist, positivo=True):
    colore = COLORS['positive'] if positivo else COLORS['negative']
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', line=dict(color=colore, width=2.5), fill='tozeroy', fillcolor=hex_to_rgba(colore, 0.12)))
    fig.update_layout(height=260, **PLOTLY_LAYOUT); fig.update_xaxes(showgrid=False, visible=False); fig.update_yaxes(gridcolor=COLORS['border'])
    return fig

def crea_grafico_equity(history):
    df = pd.DataFrame({'Data': pd.to_datetime(history['timestamp'], unit='s'), 'Equity': history['equity']})
    fig = go.Figure(go.Scatter(x=df['Data'], y=df['Equity'], mode='lines', line=dict(color=COLORS['primary'], width=2.5), fill='tozeroy', fillcolor=hex_to_rgba(COLORS['primary'], 0.1)))
    fig.update_layout(height=260, **PLOTLY_LAYOUT); fig.update_xaxes(gridcolor=COLORS['border']); fig.update_yaxes(gridcolor=COLORS['border'])
    return fig

def crea_grafico_allocazione(account, posizioni):
    eq, val_inv = float(account['portfolio_value']), sum([float(p['market_value']) for p in posizioni])
    labels, values = ['Liquidità'], [eq - val_inv]
    for p in posizioni: labels.append(p['symbol']); values.append(float(p['market_value']))
    palette = [COLORS['border'], COLORS['primary'], COLORS['accent2'], COLORS['amber'], COLORS['negative']]
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.65, marker=dict(colors=palette, line=dict(color=COLORS['panel'], width=2)))])
    fig.update_layout(height=290, showlegend=False, **PLOTLY_LAYOUT)
    return fig

def render_account_summary(account, posizioni, eq, bp, pnl, leva):
    pnl_c = "stat-value-up" if pnl >= 0 else "stat-value-down"
    segno = "+" if pnl >= 0 else ""
    return f"""
    <div style="display:flex; justify-content:space-between; margin-bottom:14px;">
        <div><div class="stat-label">ACCOUNT ID</div><div style="font-family:'IBM Plex Mono'; font-size:13px; color:{COLORS['text']};">{account.get('account_number', 'N/D')}</div></div>
        <span style="color:{COLORS['primary']}; font-size:11px; border:1px solid {COLORS['primary']}; padding:2px 6px; border-radius:4px;">✓ PAPER</span>
    </div>
    <div class="stat-label">NET EQUITY</div><div class="stat-value" style="font-size:30px; margin-bottom:14px;">${eq:,.2f}</div>
    <div style="display:flex; gap:15px;">
        <div><div class="stat-label">DAY P&L</div><div class="stat-value {pnl_c}">{segno}${pnl:,.2f}</div></div>
        <div style="border-left:1px solid {COLORS['border']}; padding-left:15px;"><div class="stat-label">BUYING POWER</div><div class="stat-value">${bp:,.0f}</div></div>
        <div style="border-left:1px solid {COLORS['border']}; padding-left:15px;"><div class="stat-label">POSIZIONI</div><div class="stat-value">{len(posizioni)}</div></div>
    </div>
    """

def render_feed_list(messaggi):
    righe = "".join([f"<div class='feed-row'><div style='color:{COLORS['text_dim']}'>{msg}</div></div>" for msg in messaggi])
    return f"<div>{righe}</div>"

def render_watchlist(tickers):
    dati = get_watchlist_snapshot(tickers)
    if not dati: return "<div class='stat-label'>Nessun dato.</div>"
    righe = ""
    for r in dati:
        pos = r['change'] >= 0
        col = COLORS['positive'] if pos else COLORS['negative']
        righe += f"<div class='feed-row'><div><span class='sym-chip'>{r['symbol']}</span></div><div style='text-align:right;'><span style='color:{COLORS['text']};'>${r['price']:.2f}</span> <span style='color:{col};'>{'▲' if pos else '▼'} {abs(r['change']):.2f}%</span></div></div>"
    return righe

# ==========================================
# INTESTAZIONE & NAVBAR
# ==========================================
col_title, col_theme = st.columns([5, 1])
with col_title:
    st.markdown('<div class="page-title">◆ QUANT <span class="brand-accent">TERMINAL</span></div>', unsafe_allow_html=True)
with col_theme:
    # Toggle Tema nativo
    is_light = st.toggle("☀️ Tema Chiaro", value=(st.session_state.theme == 'light'))
    if is_light and st.session_state.theme != 'light':
        st.session_state.theme = 'light'
        st.rerun()
    elif not is_light and st.session_state.theme != 'dark':
        st.session_state.theme = 'dark'
        st.rerun()

# Barra di navigazione orizzontale
nav_options = ["Home", "Posizioni", "Analisi Rischio", "Log & Override"]
pagina = st.radio("Menu", nav_options, horizontal=True, label_visibility="collapsed")

# ==========================================
# CARICAMENTO DATI
# ==========================================
clock = get_market_clock()
account = get_account_info()
posizioni = get_open_positions()

if not account:
    st.error("Connessione API Alpaca fallita.")
    st.stop()

eq = float(account['portfolio_value'])
bp = float(account['buying_power'])
pnl = float(account['equity']) - float(account['last_equity'])

# ==========================================
# PAGINA: HOME (WIDGET DINAMICI)
# ==========================================
if pagina == "Home":
    with st.expander("⚙️ Impostazioni Globali e Layout"):
        st.caption("Configura la Dashboard. Trascina i nomi nel campo 'Disposizione Widget' per cambiare l'ordine visivo.")
        
        c_per, c_watch = st.columns(2)
        with c_per:
            PERIODI = {"1 Mese": ("1M", "1D"), "3 Mesi": ("3M", "1D"), "6 Mesi": ("6M", "1D"), "1 Anno": ("1A", "1D")}
            periodo_scelto = st.selectbox("Periodo Analisi Storica", list(PERIODI.keys()), index=0)
            st.session_state.period_param, st.session_state.timeframe_param = PERIODI[periodo_scelto]
        with c_watch:
            # I 20 TICKER DEL BOT SONO ORA SALVATI DI DEFAULT!
            watchlist_input = st.text_input("Watchlist (Simboli separati da virgola)", value=st.session_state.get("watchlist_tickers", "AAPL, MSFT, GOOGL, AMZN, AMD, NVDA, TSLA, COIN, AVGO, META, NFLX, SPOT, UBER, IWM, PLTR, SOFI, ROKU, HOOD, AFRM"))
            st.session_state.watchlist_tickers = watchlist_input
            wl_list = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

        # ELENCO WIDGET DISPONIBILI
        ALL_WIDGETS = ["Account Summary", "Titolo in Evidenza", "Curva di Equity", "Asset Allocation", "Watchlist", "Live Feed"]
        
        if 'layout_order' not in st.session_state:
            st.session_state.layout_order = ALL_WIDGETS
            
        new_order = st.multiselect("Disposizione Widget (Trascina per riordinare)", ALL_WIDGETS, default=st.session_state.layout_order)
        st.session_state.layout_order = new_order

    st.markdown("<br>", unsafe_allow_html=True)
    history = get_portfolio_history(st.session_state.get('period_param', '1M'), st.session_state.get('timeframe_param', '1D'))

    # DEFINIZIONE WIDGET (Funzioni di rendering)
    def w_account():
        with st.container(border=True):
            st.markdown('<div class="card-title">Account Summary</div>', unsafe_allow_html=True)
            st.markdown(render_account_summary(account, posizioni, eq, bp, pnl, 0), unsafe_allow_html=True)

    def w_spotlight():
        with st.container(border=True):
            st.markdown('<div class="card-title">Titolo in Evidenza</div>', unsafe_allow_html=True)
            ticker_spot = st.selectbox("Titolo", wl_list if wl_list else ["SPY"], label_visibility="collapsed")
            dati_spot = get_spotlight_data(ticker_spot)
            if dati_spot['prezzo']:
                pos = dati_spot['var_pct'] >= 0
                st.markdown(f"""
                    <div class="spotlight-price">${dati_spot['prezzo']:.2f}</div>
                    <div style="color:{COLORS['positive'] if pos else COLORS['negative']}; font-family:'IBM Plex Mono'; font-weight:600; margin-bottom:10px;">
                        {'▲' if pos else '▼'} {dati_spot['var_pct']:.2f}%
                    </div>
                """, unsafe_allow_html=True)
                st.plotly_chart(crea_grafico_spotlight(dati_spot['hist'], pos), use_container_width=True)

    def w_equity():
        with st.container(border=True):
            st.markdown('<div class="card-title">Curva di Equity</div>', unsafe_allow_html=True)
            if history: st.plotly_chart(crea_grafico_equity(history), use_container_width=True)

    def w_alloc():
        with st.container(border=True):
            st.markdown('<div class="card-title">Asset Allocation</div>', unsafe_allow_html=True)
            st.plotly_chart(crea_grafico_allocazione(account, posizioni), use_container_width=True)

    def w_watchlist():
        with st.container(border=True):
            st.markdown('<div class="card-title">Watchlist</div>', unsafe_allow_html=True)
            st.markdown(render_watchlist(wl_list), unsafe_allow_html=True)

    def w_feed():
        with st.container(border=True):
            st.markdown('<div class="card-title">System Logs</div>', unsafe_allow_html=True)
            st.markdown(render_feed_list(get_telegram_updates()), unsafe_allow_html=True)

    # MAPPA DEI WIDGET
    WIDGET_MAP = {
        "Account Summary": w_account, "Titolo in Evidenza": w_spotlight, "Curva di Equity": w_equity,
        "Asset Allocation": w_alloc, "Watchlist": w_watchlist, "Live Feed": w_feed
    }

    # RENDERIZZAZIONE DINAMICA A 2 COLONNE IN BASE ALL'ORDINE
    active_widgets = st.session_state.layout_order
    for i in range(0, len(active_widgets), 2):
        col1, col2 = st.columns(2)
        with col1: WIDGET_MAP[active_widgets[i]]()
        if i + 1 < len(active_widgets):
            with col2: WIDGET_MAP[active_widgets[i+1]]()
