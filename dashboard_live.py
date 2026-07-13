import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import time

# ==========================================
# CONFIGURAZIONE PAGINA E TEMA "TERMINAL"
# ==========================================
st.set_page_config(page_title="Quant Terminal | Live", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")

# Iniezione CSS per stile istituzionale (Dark & Compact)
st.markdown("""
    <style>
    .stApp { background-color: #0E1117; }
    div[data-testid="metric-container"] {
        background-color: #1E212B; border: 1px solid #2D3139; padding: 15px; border-radius: 8px;
    }
    .main-header { font-family: 'Courier New', Courier, monospace; color: #00FF41; font-size: 24px; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# CREDENZIALI ALPACA (Da Streamlit Secrets)
# ==========================================
ALPACA_API_KEY = st.secrets["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
BASE_URL = "https://paper-api.alpaca.markets"

HEADERS = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}

# ==========================================
# FUNZIONI CORE
# ==========================================
@st.cache_data(ttl=60) # Mantiene i dati in cache per 60 sec per non sovraccaricare le API
def get_account_info():
    resp = requests.get(f"{BASE_URL}/v2/account", headers=HEADERS)
    return resp.json() if resp.status_code == 200 else None

def get_open_positions():
    resp = requests.get(f"{BASE_URL}/v2/positions", headers=HEADERS)
    return resp.json() if resp.status_code == 200 else []

def close_all_positions():
    resp = requests.delete(f"{BASE_URL}/v2/positions", headers=HEADERS)
    return resp.status_code in [200, 207]

def crea_grafico_candele(ticker):
    """Scarica i dati intraday di oggi e crea un grafico Plotly."""
    df = yf.Ticker(ticker).history(period="1d", interval="5m")
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#00FF41', decreasing_line_color='#FF003C'
    )])
    fig.update_layout(
        title=f"Analisi Intraday: {ticker} (Candele 5m)",
        template="plotly_dark", margin=dict(l=0, r=0, t=40, b=0),
        xaxis_rangeslider_visible=False, paper_bgcolor="#1E212B", plot_bgcolor="#1E212B"
    )
    return fig

# ==========================================
# UI: RENDER DEL TERMINALE
# ==========================================
st.markdown('<p class="main-header">⚡ QUANTITATIVE TRADING TERMINAL v2.0</p>', unsafe_allow_html=True)

col_agg, col_status = st.columns([8, 1])
with col_agg:
    if st.button("🔄 Aggiorna Flusso Dati"): st.rerun()
with col_status:
    st.markdown("🟢 **SYS: ONLINE**")

account = get_account_info()
posizioni = get_open_positions()

if account:
    # --- RIGA 1: KPI GLOBALI ---
    eq = float(account['portfolio_value'])
    bp = float(account['buying_power'])
    pnl = float(account['equity']) - float(account['last_equity'])
    pnl_perc = (pnl / float(account['last_equity'])) * 100
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("NET LIQUIDITY", f"${eq:,.2f}")
    kpi2.metric("BUYING POWER", f"${bp:,.2f}")
    kpi3.metric("DAY P&L", f"${pnl:,.2f}", f"{pnl_perc:,.2f}%")
    kpi4.metric("OPEN POSITIONS", f"{len(posizioni)}")
    
    st.divider()

    # --- RIGA 2: GRAFICO & ORDER BOOK ---
    col_chart, col_book = st.columns([2, 1]) # Il grafico occupa 2/3 dello schermo
    
    with col_book:
        st.subheader("📋 Order Book (Live)")
        if posizioni:
            dati = []
            for p in posizioni:
                pl_val = float(p['unrealized_pl'])
                pl_perc = float(p['unrealized_plpc']) * 100
                icona = "🟢" if pl_val > 0 else "🔴"
                dati.append({
                    "SYM": p['symbol'],
                    "QTY": p['qty'],
                    "P&L": f"{icona} ${pl_val:.2f} ({pl_perc:.2f}%)"
                })
            st.dataframe(pd.DataFrame(dati), use_container_width=True, hide_index=True)
            
            # Selezionatore per il grafico
            st.write("🔍 **Ispeziona Titolo:**")
            ticker_scelto = st.selectbox("Seleziona", [p['symbol'] for p in posizioni], label_visibility="collapsed")
        else:
            st.info("Nessuna posizione aperta. Attendere segnali dal motore quantitativo.")
            ticker_scelto = None

    with col_chart:
        if ticker_scelto:
            st.plotly_chart(crea_grafico_candele(ticker_scelto), use_container_width=True)
        else:
            # Grafico placeholder del mercato (SP500) se non ci sono posizioni
            st.plotly_chart(crea_grafico_candele("SPY"), use_container_width=True)

    st.divider()

    # --- RIGA 3: ZONA EMERGENZA ---
    st.subheader("🚨 Override Manuale")
    col_panic, _ = st.columns([1, 4])
    with col_panic:
        if st.button("🛑 LIQUIDA PORTAFOGLIO", type="primary", use_container_width=True):
            with st.spinner("Invio ordine di liquidazione a mercato..."):
                if close_all_positions():
                    st.success("Operazione completata. Conto flat.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Errore di routing verso il broker.")
else:
    st.error("Connessione API Alpaca rifiutata. Controllare i Secrets.")
