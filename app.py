import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests

st.set_page_config(layout="wide", page_title="Terminal Pro")

# CSS Minimalista Premium
st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #fff; }
    .metric-box { background-color: #161b22; border-radius: 12px; padding: 20px; border: 1px solid #30363d; margin-bottom: 20px; }
    .metric-title { font-size: 14px; color: #8b949e; }
    .metric-value { font-family: 'Courier New', monospace; font-size: 26px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# API Alpaca
ALPACA_API_KEY = st.secrets["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
BASE_URL = "https://paper-api.alpaca.markets"
HEADERS = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}

@st.cache_data(ttl=30)
def get_data(endpoint):
    try:
        resp = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS)
        return resp.json() if resp.status_code == 200 else None
    except: return None

# UI Header
st.title("⚡ QUANTITATIVE TERMINAL")
if st.button("🔄 REFRESH"): st.rerun()

account = get_data("/v2/account")
posizioni = get_data("/v2/positions") or []

if account:
    # Metriche
    eq = float(account['portfolio_value'])
    pnl = float(account['equity']) - float(account['last_equity'])
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown(f'<div class="metric-box"><div class="metric-title">NET EQUITY</div><div class="metric-value">${eq:,.2f}</div></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="metric-box"><div class="metric-title">DAY P&L</div><div class="metric-value" style="color:{"#00ff41" if pnl>=0 else "#ff003c"}">${pnl:,.2f}</div></div>', unsafe_allow_html=True)
    with col3: st.markdown(f'<div class="metric-box"><div class="metric-title">ACTIVE POSITIONS</div><div class="metric-value">{len(posizioni)}</div></div>', unsafe_allow_html=True)

    # Grafico & Ledger
    col_g, col_l = st.columns([2.5, 1.5])
    with col_g:
        components.html("""
            <div style="background-color: #161b22; border-radius: 12px; padding: 15px; border: 1px solid #30363d;">
                <div id="tv-chart" style="height: 380px;"></div>
                <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                <script type="text/javascript">
                    new TradingView.widget({"autosize": true, "symbol": "NASDAQ:AAPL", "theme": "dark", "container_id": "tv-chart"});
                </script>
            </div>
        """, height=420)
        
    with col_l:
        st.subheader("📋 Ledger Posizioni")
        if posizioni:
            df_pos = pd.DataFrame([{"SYM": p['symbol'], "QTY": p['qty'], "P&L": f"{float(p['unrealized_plpc'])*100:.2f}%"} for p in posizioni])
            st.dataframe(df_pos, use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna posizione a mercato.")

    # Bot Reasoning Engine
    st.divider()
    st.subheader("🧠 Bot Reasoning Engine")
    try:
        df_log = pd.read_csv("decision_log.csv")
        st.dataframe(df_log, use_container_width=True)
    except:
        st.info("In attesa che il Bot esegua la prima scansione per generare il file dei log...")
