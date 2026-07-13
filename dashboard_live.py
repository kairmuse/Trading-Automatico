import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import time
from datetime import datetime

# ==========================================
# CONFIGURAZIONE PAGINA E TEMA "TERMINAL"
# ==========================================
st.set_page_config(page_title="Quant Terminal | Live", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    div[data-testid="metric-container"] {
        background-color: #1E212B; border: 1px solid #2D3139; padding: 15px; border-radius: 8px;
    }
    .main-header { font-family: 'Courier New', Courier, monospace; color: #00FF41; font-size: 24px; font-weight: bold;}
    .log-console { background-color: #000000; color: #00FF41; font-family: monospace; padding: 10px; border-radius: 5px; height: 180px; overflow-y: auto; border: 1px solid #2D3139;}
    hr { border-color: #2D3139; }
    </style>
""", unsafe_allow_html=True)

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

@st.cache_data(ttl=300) # Storico aggiornato ogni 5 min
def get_portfolio_history():
    """Recupera la curva di equity dell'ultimo mese"""
    url = f"{BASE_URL}/v2/account/portfolio/history?period=1M&timeframe=1D"
    resp = requests.get(url, headers=HEADERS)
    return resp.json() if resp.status_code == 200 else None

def close_all_positions():
    resp = requests.delete(f"{BASE_URL}/v2/positions", headers=HEADERS)
    return resp.status_code in [200, 207]

def crea_grafico_equity(history):
    """Genera il grafico lineare della crescita del portafoglio"""
    df = pd.DataFrame({
        'Data': pd.to_datetime(history['timestamp'], unit='s'),
        'Equity': history['equity']
    })
    fig = go.Figure(go.Scatter(x=df['Data'], y=df['Equity'], mode='lines', 
                               line=dict(color='#00FF41', width=3), 
                               fill='tozeroy', fillcolor='rgba(0, 255, 65, 0.1)'))
    fig.update_layout(title="Curva di Equity (Ultimo Mese)", template="plotly_dark", 
                      margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor="#1E212B", plot_bgcolor="#1E212B", height=300)
    return fig

def crea_grafico_allocazione(account, posizioni):
    """Genera la Donut Chart dell'esposizione al rischio"""
    labels = ['Liquidità (Cash)']
    equity = float(account['portfolio_value'])
    valore_investito = sum([float(p['market_value']) for p in posizioni])
    cash = equity - valore_investito
    values = [cash]

    for p in posizioni:
        labels.append(p['symbol'])
        values.append(float(p['market_value']))

    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.6, textinfo='label+percent', 
                                 marker=dict(colors=['#2D3139', '#00FF41', '#FF003C', '#00A1FF', '#FFD700', '#FF00FF']))])
    fig.update_layout(title="Asset Allocation", template="plotly_dark", 
                      margin=dict(l=0, r=0, t=40, b=0), paper_bgcolor="#1E212B", plot_bgcolor="#1E212B", showlegend=False, height=300)
    return fig

def crea_grafico_candele(ticker):
    df = yf.Ticker(ticker).history(period="1d", interval="5m")
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                         increasing_line_color='#00FF41', decreasing_line_color='#FF003C')])
    fig.update_layout(title=f"Analisi Intraday: {ticker} (5m)", template="plotly_dark", 
                      margin=dict(l=0, r=0, t=40, b=0), xaxis_rangeslider_visible=False, paper_bgcolor="#1E212B", plot_bgcolor="#1E212B", height=350)
    return fig

@st.cache_data(ttl=60)
def get_telegram_updates():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            dati = resp.json()
            if 'result' in dati and len(dati['result']) > 0:
                messaggi = []
                for update in reversed(dati['result'][-5:]):
                    if 'message' in update and 'text' in update['message']:
                        testo = update['message']['text']
                        data = datetime.fromtimestamp(update['message']['date']).strftime('%Y-%m-%d %H:%M:%S')
                        messaggi.append(f"[{data}] SYS_MSG: {testo[:100]}...")
                return messaggi if messaggi else ["Nessuna operazione registrata oggi."]
    except: pass
    return ["Nessun log disponibile."]

# ==========================================
# UI: RENDER DEL TERMINALE
# ==========================================
st.markdown('<p class="main-header">⚡ QUANTITATIVE TRADING TERMINAL v3.0</p>', unsafe_allow_html=True)

col_agg, col_status = st.columns([8, 1])
with col_agg:
    if st.button("🔄 Aggiorna Dati Live"): st.rerun()
with col_status:
    st.markdown("🟢 **SYS: ONLINE**")

account = get_account_info()
posizioni = get_open_positions()
history = get_portfolio_history()

if account:
    # --- RIGA 1: KPI AVANZATI ---
    eq = float(account['portfolio_value'])
    bp = float(account['buying_power'])
    pnl = float(account['equity']) - float(account['last_equity'])
    esposizione_totale = sum([float(p['market_value']) for p in posizioni])
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("NET EQUITY", f"${eq:,.2f}")
    kpi2.metric("TOTAL EXPOSURE (RISK)", f"${esposizione_totale:,.2f}")
    kpi3.metric("BUYING POWER", f"${bp:,.2f}")
    kpi4.metric("DAY P&L", f"${pnl:,.2f}", f"{(pnl/eq)*100:,.2f}%")
    
    st.divider()

    # --- RIGA 2: MACRO ANALISI (STORICO & RISCHIO) ---
    col_history, col_donut = st.columns([2, 1])
    with col_history:
        if history:
            st.plotly_chart(crea_grafico_equity(history), use_container_width=True)
    with col_donut:
        st.plotly_chart(crea_grafico_allocazione(account, posizioni), use_container_width=True)

    st.divider()

    # --- RIGA 3: MICRO ANALISI (GRAFICO & BOOK) ---
    col_chart, col_book = st.columns([2, 1]) 
    
    with col_book:
        st.subheader("📋 Order Book (Live)")
        if posizioni:
            dati = []
            for p in posizioni:
                pl_val = float(p['unrealized_pl'])
                pl_perc = float(p['unrealized_plpc']) * 100
                dati.append({"SYM": p['symbol'], "QTY": p['qty'], "P&L (%)": f"${pl_val:.2f} ({pl_perc:.2f}%)"})
            st.dataframe(pd.DataFrame(dati), use_container_width=True, hide_index=True)
            
            ticker_scelto = st.selectbox("🔍 Ispeziona Titolo", [p['symbol'] for p in posizioni])
        else:
            st.info("Portafoglio 100% Cash. In attesa di segnali.")
            ticker_scelto = None

    with col_chart:
        if ticker_scelto: st.plotly_chart(crea_grafico_candele(ticker_scelto), use_container_width=True)
        else: st.plotly_chart(crea_grafico_candele("SPY"), use_container_width=True)

    st.divider()

    # --- RIGA 4: LOGS & PANIC BUTTON ---
    col_logs, col_panic = st.columns([3, 1])
    
    with col_logs:
        st.subheader("📡 System Logs")
        log_html = '<div class="log-console">'
        for msg in get_telegram_updates(): log_html += f"<p>{msg}</p>"
        log_html += '</div>'
        st.markdown(log_html, unsafe_allow_html=True)

    with col_panic:
        st.subheader("🚨 Override")
        st.caption("Liquidazione immediata a prezzo di mercato.")
        if st.button("🛑 CHIUDI TUTTE LE POSIZIONI", type="primary", use_container_width=True):
            with st.spinner("Invio ordine al broker..."):
                if close_all_positions():
                    st.success("Conto Flat.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Errore di routing.")
else:
    st.error("Connessione API Alpaca fallita.")
