import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

# Layout Wide obbligatorio
st.set_page_config(layout="wide", page_title="Bet-Style Terminal")

# CSS AGGRESSIVO PER STILE DARK/NEON
st.markdown("""
    <style>
    /* Reset generale */
    .stApp { background-color: #0b0e11; color: #e1e1e1; }
    
    /* Pannelli stile "Bet-Safu" */
    .trading-card {
        background-color: #171b21;
        border: 1px solid #2d3139;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }
    
    /* Bottone Neon */
    div.stButton > button:first-child {
        background-color: #00ff41; color: #000; font-weight: bold; border: none; width: 100%;
    }
    
    /* Tabella Ledger Custom */
    .stDataFrame { border: 1px solid #2d3139; }
    
    /* Font monospazio per dati finanziari */
    h1, h2, h3 { font-family: 'Courier New', monospace; color: #ffffff; }
    </style>
""", unsafe_allow_html=True)

# SIDEBAR (Navigazione)
with st.sidebar:
    st.image("https://img.icons8.com/nolan/64/bitcoin.png", width=50)
    st.title("BET-STYLING")
    st.write("---")
    st.write("📈 Trading")
    st.write("🎮 Casino")
    st.write("🏆 Sports")
    st.write("⚙️ Settings")

# LOGICA (Simulata per il layout)
posizioni = [{"SYM": "ETH", "QTY": "1.2", "ENTRY": "3500", "P&L": "+12.4%"}, {"SYM": "BTC", "QTY": "0.5", "ENTRY": "64000", "P&L": "-2.1%"}]
df = pd.DataFrame(posizioni)

# LAYOUT: Grafico (Sinistra) + Azioni (Destra)
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown('<div class="trading-card">', unsafe_allow_html=True)
    st.subheader("ETH / USDT - 5m")
    # Grafico Dummy
    fig = go.Figure(go.Candlestick(x=['10:00','10:05','10:10'], open=[3600,3610,3605], high=[3620,3615,3610], low=[3590,3600,3595], close=[3610,3605,3608]))
    fig.update_layout(template="plotly_dark", margin=dict(l=0,r=0,t=0,b=0), height=300)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="trading-card">', unsafe_allow_html=True)
    st.subheader("Place Bet")
    st.number_input("Amount (USDT)", value=1.0)
    st.slider("Multiplier", 1, 100, 10)
    st.button("PLACE BET")
    st.markdown('</div>', unsafe_allow_html=True)

# BOTTOM: LEDGER (Tabella stile Trading)
st.markdown('<div class="trading-card">', unsafe_allow_html=True)
st.subheader("Active Bets")
st.table(df)
st.markdown('</div>', unsafe_allow_html=True)
