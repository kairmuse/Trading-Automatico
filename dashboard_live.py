import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime

# ==========================================
# UI PROFESSIONALE: STILE "INSTITUTIONAL"
# ==========================================
st.set_page_config(page_title="Terminal Pro | Live", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    /* Rimozione del padding standard per più spazio */
    .main { padding: 1rem !important; }
    
    /* Effetto Glassmorphism sui pannelli */
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

# [Mantenere le funzioni get_account_info, get_open_positions, ecc. come nella versione precedente]

# ==========================================
# RENDERING DASHBOARD "PRO"
# ==========================================

st.markdown('<p class="ticker-header">QUANTITATIVE DESK v4.0</p>', unsafe_allow_html=True)

# Barra di controllo alta
col_ctrl, col_sys = st.columns([6, 1])
with col_ctrl:
    if st.button("🔄 REFRESH DATA"): st.rerun()
with col_sys:
    st.markdown("🟢 SYSTEM READY")

# --- PANNELLO METRICHE ---
# Usiamo i contenitori personalizzati (glass-card)
account = get_account_info()
posizioni = get_open_positions()

if account:
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

    # --- MAIN GRID ---
    col_left, col_right = st.columns([2.5, 1])
    
    with col_left:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("📊 Chart Analysis")
        # Logica ticker selezionato
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
        
        # Override Pulsante in stile "Emergency Switch"
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🛑 EMERGENCY LIQUIDATION", type="primary", use_container_width=True):
            if close_all_positions(): st.rerun()
