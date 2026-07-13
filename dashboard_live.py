import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests

# ==========================================
# SETUP PAGINA E CSS
# ==========================================
st.set_page_config(layout="wide", page_title="Institutional Terminal v7.2")

st.markdown("""
    <style>
    .stApp { background-color: #0b0e11; color: #fff; }
    /* Stile per i box delle metriche superiori */
    .metric-card { background-color: #161b22; border-radius: 12px; padding: 20px; border: 1px solid #30363d; margin-bottom: 20px; }
    .metric-title { font-size: 14px; color: #8b949e; margin-bottom: 5px; }
    .metric-val { font-family: 'Courier New', monospace; font-size: 24px; color: #ffffff; }
    .val-positive { color: #00ff41; }
    .val-negative { color: #ff003c; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# CREDENZIALI API
# ==========================================
try:
    ALPACA_API_KEY = st.secrets["ALPACA_API_KEY"]
    ALPACA_SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
    BASE_URL = "https://paper-api.alpaca.markets"
    HEADERS = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}
except Exception as e:
    st.error("Errore lettura Secrets. Verifica la configurazione su Streamlit Cloud.")
    st.stop()

# ==========================================
# FUNZIONI DATI
# ==========================================
@st.cache_data(ttl=60)
def get_account_info():
    resp = requests.get(f"{BASE_URL}/v2/account", headers=HEADERS)
    return resp.json() if resp.status_code == 200 else None

@st.cache_data(ttl=60)
def get_open_positions():
    resp = requests.get(f"{BASE_URL}/v2/positions", headers=HEADERS)
    return resp.json() if resp.status_code == 200 else []

def get_bot_reasoning():
    try:
        df = pd.read_csv("decision_log.csv")
        # Se il file esiste ma è vuoto, restituisce un DF con le colonne corrette
        if df.empty:
            return pd.DataFrame(columns=["Ticker", "Strategy", "Decision", "Reason"])
        return df
    except:
        return pd.DataFrame(columns=["Ticker", "Strategy", "Decision", "Reason"])

def close_all_positions():
    resp = requests.delete(f"{BASE_URL}/v2/positions", headers=HEADERS)
    return resp.status_code in [200, 207]

# ==========================================
# UI DASHBOARD
# ==========================================
col_title, col_btn = st.columns([8, 1])
with col_title:
    st.title("⚡ QUANTITATIVE TERMINAL")
with col_btn:
    if st.button("🔄 REFRESH"): st.rerun()

account = get_account_info()
posizioni = get_open_positions()

if account:
    # --- RIGA 1: METRICHE ---
    eq = float(account['portfolio_value'])
    pnl = float(account['equity']) - float(account['last_equity'])
    pnl_class = "val-positive" if pnl >= 0 else "val-negative"
    
    col1, col2, col3 = st.columns(3)
    with col1: 
        st.markdown(f'<div class="metric-card"><div class="metric-title">NET EQUITY</div><div class="metric-val">${eq:,.2f}</div></div>', unsafe_allow_html=True)
    with col2: 
        st.markdown(f'<div class="metric-card"><div class="metric-title">DAY P&L</div><div class="metric-val {pnl_class}">${pnl:,.2f}</div></div>', unsafe_allow_html=True)
    with col3: 
        st.markdown(f'<div class="metric-card"><div class="metric-title">ACTIVE POSITIONS</div><div class="metric-val">{len(posizioni)}</div></div>', unsafe_allow_html=True)

    # --- RIGA 2: TRADINGVIEW & LEDGER ---
    col_main, col_side = st.columns([2.5, 1.5])
    
    with col_main:
        ticker_tv = "NASDAQ:AAPL" 
        # Il box contenitore è ora integrato direttamente nel codice HTML del widget
        components.html(f"""
            <div style="background-color: #161b22; border-radius: 12px; padding: 20px; border: 1px solid #30363d;">
                <div class="tradingview-widget-container">
                  <div id="tradingview_chart" style="height: 400px;"></div>
                  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                  <script type="text/javascript">
                  new TradingView.widget({{"autosize": true, "symbol": "{ticker_tv}", "theme": "dark", "container_id": "tradingview_chart"}});
                  </script>
                </div>
            </div>
        """, height=450)
        
    with col_side:
        st.subheader("📋 Live Ledger")
        if posizioni:
            df_pos = pd.DataFrame([{"SYM": p['symbol'], "QTY": p['qty'], "P&L": f"{float(p['unrealized_plpc'])*100:.2f}%"} for p in posizioni])
            st.dataframe(df_pos, use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna posizione aperta.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🛑 EMERGENCY LIQUIDATION", type="primary", use_container_width=True):
            if close_all_positions(): st.rerun()

    st.divider()

    # --- RIGA 3: BOT REASONING ENGINE ---
    st.subheader("🧠 BOT REASONING ENGINE (Audit Log)")
    df_reasoning = get_bot_reasoning()
    
    if df_reasoning.empty:
        st.info("In attesa della prima esecuzione del Bot per generare i log decisionali...")
    else:
        st.dataframe(
            df_reasoning,
            column_config={
                "Decision": st.column_config.TextColumn("Decision", help="BUY o IGNORE"),
                "Reason": st.column_config.TextColumn("Reason", width="large")
            },
            use_container_width=True
        )

else:
    st.error("Connessione API Alpaca fallita. Controlla i Secrets su Streamlit Cloud.")
