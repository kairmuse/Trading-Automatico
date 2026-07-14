import streamlit as st
import requests
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
import time
from datetime import datetime, timedelta

# ==========================================
# CONFIGURAZIONE PAGINA (Mobile Optimized)
# ==========================================
st.set_page_config(page_title="Quant Terminal", page_icon="📱", layout="centered")

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
# CSS PERSONALIZZATO (Mobile Tweaks)
# ==========================================
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

    html, body, .stApp {{ background-color: {COLORS['void']}; }}
    * {{ font-family: 'Inter', sans-serif; }}
    
    /* Spaziature ridotte per mobile */
    .block-container {{ padding-top: 1.5rem !important; padding-bottom: 2rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }}
    
    #MainMenu {{visibility: hidden;}}
    [data-testid="collapsedControl"] {{display: none;}}
    header {{visibility: hidden;}}

    .page-title {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 26px; color: {COLORS['text']}; letter-spacing: -0.5px; margin-bottom: 6px;}}
    .brand-accent {{ color: {COLORS['primary']}; }}
    
    .status-pill {{
        font-family: 'IBM Plex Mono', monospace; font-size: 10px; letter-spacing: 1px;
        padding: 4px 10px; border-radius: 20px; border: 1px solid; display: inline-flex; align-items: center; gap: 6px;
    }}
    .status-open {{ color: {COLORS['positive']}; border-color: {hex_to_rgba(COLORS['positive'],0.35)}; background: {hex_to_rgba(COLORS['positive'],0.08)}; }}
    .status-closed {{ color: {COLORS['text_dim']}; border-color: {COLORS['border']}; background: {COLORS['panel']}; }}

    /* Cards - Adattate per la larghezza mobile */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: {COLORS['panel']} !important;
        border: 1px solid {COLORS['border']} !important; border-radius: 10px !important;
        box-shadow: 0 4px 12px {hex_to_rgba('#000000', 0.05 if st.session_state.theme == 'light' else 0.3)};
        margin-bottom: 8px !important;
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
    .sym-chip {{ font-weight: 600; color: {COLORS['text']}; font-family: 'Inter', sans-serif; font-size: 13px; }}

    /* Feed & Spotlight */
    .feed-row {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 4px; border-bottom: 1px solid {COLORS['border']}; font-family: 'IBM Plex Mono', monospace; font-size: 12px; }}
    .spotlight-price {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 32px; color: {COLORS['text']}; line-height: 1.1; margin-top: 4px; }}
    
    /* Pulsanti a tutta larghezza */
    .stButton > button {{ width: 100% !important; border-radius: 8px; font-weight: 600; }}
    </style>
""", unsafe_allow_html=True)

# Margini Plotly più stretti per il telefono
PLOTLY_LAYOUT = dict(
    template=PLOTLY_TEMPLATE, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    font=dict(family="IBM Plex Mono, monospace", color=COLORS["text_dim"], size=10),
    margin=dict(l=0, r=0, t=30, b=0),
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
        if resp.status_code != 200: return [f"⚠ Errore Telegram."]
        risultati = resp.json().get('result', [])
        messaggi = [f"[{datetime.fromtimestamp(u['message']['date']).strftime('%H:%M:%S')}] {u['message']['text'][:60]}..." for u in reversed(risultati[-5:]) if 'message' in u and 'text' in u['message']]
        return messaggi if messaggi else ["Nessun log recente."]
    except: return ["⚠ Errore connessione Telegram."]

# ==========================================
# RENDER FUNZIONI GRAFICI (Adattati in altezza)
# ==========================================
def crea_grafico_spotlight(hist, positivo=True):
    colore = COLORS['positive'] if positivo else COLORS['negative']
    fig = go.Figure(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', line=dict(color=colore, width=2.5), fill='tozeroy', fillcolor=hex_to_rgba(colore, 0.12)))
    fig.update_layout(height=200, **PLOTLY_LAYOUT); fig.update_xaxes(showgrid=False, visible=False); fig.update_yaxes(gridcolor=COLORS['border'])
    return fig

def crea_grafico_equity(history):
    df = pd.DataFrame({'Data': pd.to_datetime(history['timestamp'], unit='s'), 'Equity': history['equity']})
    fig = go.Figure(go.Scatter(x=df['Data'], y=df['Equity'], mode='lines', line=dict(color=COLORS['primary'], width=2.5), fill='tozeroy', fillcolor=hex_to_rgba(COLORS['primary'], 0.1)))
    fig.update_layout(height=220, **PLOTLY_LAYOUT); fig.update_xaxes(gridcolor=COLORS['border']); fig.update_yaxes(gridcolor=COLORS['border'])
    return fig

def crea_grafico_allocazione(account, posizioni):
    eq, val_inv = float(account['portfolio_value']), sum([float(p['market_value']) for p in posizioni])
    labels, values = ['Liquidità'], [eq - val_inv]
    for p in posizioni: labels.append(p['symbol']); values.append(float(p['market_value']))
    palette = [COLORS['border'], COLORS['primary'], COLORS['accent2'], COLORS['amber'], COLORS['negative']]
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.65, marker=dict(colors=palette, line=dict(color=COLORS['panel'], width=2)))])
    fig.update_layout(height=240, showlegend=False, **PLOTLY_LAYOUT)
    return fig

def render_account_summary(account, posizioni, eq, bp, pnl, leva):
    pnl_c = "stat-value-up" if pnl >= 0 else "stat-value-down"
    segno = "+" if pnl >= 0 else ""
    # Incolonnato per evitare compressioni orizzontali strette
    return f"""
    <div style="margin-bottom:14px;">
        <div class="stat-label">ACCOUNT ID: {account.get('account_number', 'N/D')} <span style="color:{COLORS['primary']}; margin-left:10px;">✓ PAPER</span></div>
    </div>
    <div style="margin-bottom:18px;">
        <div class="stat-label">NET EQUITY</div>
        <div class="stat-value" style="font-size:32px;">${eq:,.2f}</div>
    </div>
    <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:10px;">
        <div><div class="stat-label">DAY P&L</div><div class="stat-value {pnl_c}">{segno}${pnl:,.2f}</div></div>
        <div><div class="stat-label">BUYING POWER</div><div class="stat-value">${bp:,.0f}</div></div>
        <div><div class="stat-label">POSIZIONI</div><div class="stat-value">{len(posizioni)}</div></div>
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
        righe += f"<div class='feed-row'><div><span class='sym-chip'>{r['symbol']}</span></div><div style='text-align:right;'><span style='color:{COLORS['text']}; font-weight:600;'>${r['price']:.2f}</span> <br><span style='color:{col}; font-size:10px;'>{'▲' if pos else '▼'} {abs(r['change']):.2f}%</span></div></div>"
    return righe

# ==========================================
# HEADER & NAVBAR (Dropdown per Mobile)
# ==========================================
c_logo, c_theme = st.columns([4, 1])
with c_logo:
    st.markdown('<div class="page-title">◆ QUANT <span class="brand-accent">TERM</span></div>', unsafe_allow_html=True)
with c_theme:
    is_light = st.toggle("☀", value=(st.session_state.theme == 'light'))
    if is_light and st.session_state.theme != 'light':
        st.session_state.theme = 'light'; st.rerun()
    elif not is_light and st.session_state.theme != 'dark':
        st.session_state.theme = 'dark'; st.rerun()

# Menu a tendina nativo al posto dei pulsanti affiancati
nav_options = ["Home", "Posizioni Attive", "Log e Override"]
pagina = st.selectbox("Navigazione", nav_options, label_visibility="collapsed")

# ==========================================
# CARICAMENTO DATI
# ==========================================
clock = get_market_clock()
mercato_aperto = clock.get("is_open") if clock else None
account = get_account_info()
posizioni = get_open_positions()

if not account:
    st.error("Connessione API Alpaca fallita.")
    st.stop()

eq = float(account['portfolio_value'])
bp = float(account['buying_power'])
pnl = float(account['equity']) - float(account['last_equity'])

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# Status pill mobile
if mercato_aperto is True: st.markdown('<div class="status-pill status-open">● MARKET OPEN</div>', unsafe_allow_html=True)
elif mercato_aperto is False: st.markdown('<div class="status-pill status-closed">○ MARKET CLOSED</div>', unsafe_allow_html=True)
st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

# ==========================================
# PAGINA: HOME (Colonna Singola Verticale)
# ==========================================
if pagina == "Home":
    
    with st.expander("⚙️ Impostazioni"):
        PERIODI = {"1 Mese": ("1M", "1D"), "3 Mesi": ("3M", "1D"), "1 Anno": ("1A", "1D")}
        periodo_scelto = st.selectbox("Storico", list(PERIODI.keys()), index=0)
        st.session_state.period_param, st.session_state.timeframe_param = PERIODI[periodo_scelto]
        watchlist_input = st.text_input("Watchlist", value=st.session_state.get("watchlist_tickers", "AAPL, MSFT, GOOGL, AMZN, AMD, NVDA, TSLA, COIN, AVGO, META, NFLX, SPOT, UBER, IWM, PLTR, SOFI, ROKU, HOOD, AFRM"))
        st.session_state.watchlist_tickers = watchlist_input
        wl_list = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

    history = get_portfolio_history(st.session_state.get('period_param', '1M'), st.session_state.get('timeframe_param', '1D'))
    simboli_disponibili = list(dict.fromkeys([p['symbol'] for p in posizioni] + ["AAPL", "NVDA", "TSLA"]))

    # 1. ACCOUNT SUMMARY
    with st.container(border=True):
        st.markdown('<div class="card-title">Account Summary</div>', unsafe_allow_html=True)
        st.markdown(render_account_summary(account, posizioni, eq, bp, pnl, 0), unsafe_allow_html=True)
        if st.button("↻ Aggiorna Dati"):
            st.cache_data.clear()
            st.rerun()

    # 2. SPOTLIGHT
    with st.container(border=True):
        st.markdown('<div class="card-title">Titolo in Evidenza</div>', unsafe_allow_html=True)
        ticker_spot = st.selectbox("Seleziona", wl_list if wl_list else ["SPY"], label_visibility="collapsed")
        dati_spot = get_spotlight_data(ticker_spot)
        if dati_spot['prezzo']:
            pos = dati_spot['var_pct'] >= 0
            st.markdown(f"""
                <div class="spotlight-price">${dati_spot['prezzo']:.2f}</div>
                <div style="color:{COLORS['positive'] if pos else COLORS['negative']}; font-family:'IBM Plex Mono'; font-weight:600; margin-bottom:10px;">
                    {'▲' if pos else '▼'} {dati_spot['var_pct']:.2f}%
                </div>
                <div class="stat-label">HIGH ${dati_spot['high']:.2f} &nbsp;|&nbsp; LOW ${dati_spot['low']:.2f}</div>
            """, unsafe_allow_html=True)
            st.plotly_chart(crea_grafico_spotlight(dati_spot['hist'], pos), use_container_width=True)

    # 3. EQUITY CURVE
    with st.container(border=True):
        st.markdown('<div class="card-title">Curva di Equity</div>', unsafe_allow_html=True)
        if history: st.plotly_chart(crea_grafico_equity(history), use_container_width=True)

    # 4. ALLOCAZIONE
    with st.container(border=True):
        st.markdown('<div class="card-title">Asset Allocation</div>', unsafe_allow_html=True)
        st.plotly_chart(crea_grafico_allocazione(account, posizioni), use_container_width=True)

    # 5. WATCHLIST
    with st.container(border=True):
        st.markdown('<div class="card-title">Radar Watchlist</div>', unsafe_allow_html=True)
        st.markdown(render_watchlist(wl_list), unsafe_allow_html=True)

# ==========================================
# PAGINA: POSIZIONI
# ==========================================
elif pagina == "Posizioni Attive":
    st.markdown("### Portafoglio")
    if posizioni:
        # Costruzione tabella semplificata per il telefono
        for p in posizioni:
            pl_val = float(p['unrealized_pl'])
            pl_perc = float(p['unrealized_plpc']) * 100
            segno = "+" if pl_val >= 0 else ""
            color = COLORS['positive'] if pl_val >= 0 else COLORS['negative']
            with st.container(border=True):
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div class="sym-chip" style="font-size:18px;">{p['symbol']}</div>
                        <div class="stat-label" style="margin-top:2px;">{p['qty']} QTY @ ${float(p['avg_entry_price']):.2f}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-weight:700; color:{COLORS['text']};">${float(p['current_price']):.2f}</div>
                        <div style="color:{color}; font-family:'IBM Plex Mono'; font-size:12px; font-weight:600;">{segno}{pl_perc:.2f}%</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Nessuna posizione aperta.")

# ==========================================
# PAGINA: LOG & OVERRIDE
# ==========================================
elif pagina == "Log e Override":
    with st.container(border=True):
        st.markdown('<div class="card-title">System Logs (Telegram)</div>', unsafe_allow_html=True)
        st.markdown(render_feed_list(get_telegram_updates()), unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown('<div class="card-title">Panic Button</div>', unsafe_allow_html=True)
        st.caption("Chiude immediatamente tutte le posizioni a mercato.")
        if st.button("🛑 LIQUIDA TUTTO", type="primary"):
            with st.spinner("Invio ordine al broker..."):
                if close_all_positions():
                    st.success("Portafoglio svuotato con successo.")
                    time.sleep(1); st.rerun()
                else: st.error("Errore di comunicazione col broker.")
