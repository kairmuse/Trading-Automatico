import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime

# ==========================================
# CONFIGURAZIONE PAGINA E TEMA "TERMINAL"
# ==========================================
st.set_page_config(page_title="Terminal Pro | Live", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .main { padding: 1rem !important; }
    .stApp { background: linear-gradient(135deg, #090a0f 0%, #161b22 100%); }
    div[data-testid="stMetricValue"] { font-family: 'Courier New', monospace; font-size: 28px !important; }
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .ticker-header { font-family: 'Inter', sans-serif; font-size: 32px; font-weight: 700; color: #ffffff; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# CONFIGURAZIONE API E CREDENZIALI
# ==========================================
ALPACA_API_KEY = st.secrets["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
BASE_URL = "https://paper-api.alpaca.markets"
HEADERS = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}

# ==========================================
# FUNZIONI HELPER (TUTTE LE LOGICHE)
# ==========================================
@st.cache_data(ttl=60)
def get_account_info():
    resp = requests.get(f"{BASE_URL}/v2/account", headers=HEADERS)
    return resp.json() if resp.status_code == 200 else None

@st.cache_data(ttl=60)
def get_open_positions():
    resp = requests.get(f"{BASE_URL}/v2/positions", headers=HEADERS)
    return resp.json() if resp.status_code == 200 else []

def close_all_positions():
    resp = requests.delete(f"{BASE_URL}/v2/positions", headers=HEADERS)
    return resp.status_code in [200, 207]

def crea_grafico_candele(ticker):
    import yfinance as yf
    df = yf.Ticker(ticker).history(period="1d", interval="5m")
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                                         increasing_line_color='#00FF41', decreasing_line_color='#FF003C')])
    fig.update_layout(title=f"Analisi: {ticker}", template="plotly_dark", margin=dict(l=0, r=0, t=40, b=0),
                      xaxis_rangeslider_visible=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
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
                        data = datetime.fromtimestamp(update['message']['date']).strftime('%H:%M:%S')
                        messaggi.append(f"[{data}] {testo[:50]}...")
                return messaggi
    except: pass
    return ["Nessun log recente."]

# ==========================================
# UI: RENDER DELLA DASHBOARD
# ==========================================
st.markdown('<p class="ticker-header">QUANTITATIVE DESK v4.0</p>', unsafe_allow_html=True)

if st.button("🔄 REFRESH DATA"): st.rerun()

account = get_account_info()
posizioni = get_open_positions()

if account:
    # Metriche in alto
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.metric("NET EQUITY", f"${float(account['portfolio_value']):,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.metric("BUYING POWER", f"${float(account['buying_power']):,.2f}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        pnl = float(account['equity']) - float(account['last_equity'])
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.metric("DAY P&L", f"${pnl:,.2f}", f"{(pnl/float(account['portfolio_value']))*100:,.2f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.metric("ACTIVE POSITIONS", f"{len(posizioni)}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Main Grid
    col_left, col_right = st.columns([2.5, 1])
    
    with col_left:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📊 Chart Analysis")
        ticker = st.selectbox("Seleziona asset", [p['symbol'] for p in posizioni] if posizioni else ["SPY"])
        st.plotly_chart(crea_grafico_candele(ticker), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_right:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📋 Live Ledger")
        if posizioni:
            df = pd.DataFrame([{"SYM": p['symbol'], "QTY": p['qty'], "P&L": f"{float(p['unrealized_plpc'])*100:.2f}%"} for p in posizioni])
            st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🛑 EMERGENCY LIQUIDATION", type="primary", use_container_width=True):
            if close_all_positions(): st.rerun()
else:
    st.error("Connessione API fallita. Controlla i Secrets su Streamlit Cloud.")
