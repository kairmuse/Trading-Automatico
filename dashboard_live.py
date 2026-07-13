import streamlit as st
import requests
import pandas as pd
import time

# ==========================================
# CONFIGURAZIONE API ALPACA (PAPER TRADING)
# ==========================================
ALPACA_API_KEY = "PKXI7EN3SIKMTWTCT7U2M7R4DZ"
ALPACA_SECRET_KEY = "E3xykXwW3251vfi6bkKUiCuBLfpB5WCAbgXDY7aDko8T"
BASE_URL = "https://paper-api.alpaca.markets"

HEADERS = {
    "APCA-API-KEY-ID": ALPACA_API_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY
}

# Impostazioni pagina Streamlit
st.set_page_config(page_title="Ecosistema Trading Live", page_icon="📈", layout="wide")

# ==========================================
# FUNZIONI DI COLLEGAMENTO AL BROKER
# ==========================================
def get_account_info():
    """Recupera i dati del portafoglio dal broker."""
    resp = requests.get(f"{BASE_URL}/v2/account", headers=HEADERS)
    if resp.status_code == 200:
        return resp.json()
    return None

def get_open_positions():
    """Recupera le azioni attualmente possedute."""
    resp = requests.get(f"{BASE_URL}/v2/positions", headers=HEADERS)
    if resp.status_code == 200:
        return resp.json()
    return []

def close_all_positions():
    """Tasto d'emergenza: chiude tutto a mercato."""
    resp = requests.delete(f"{BASE_URL}/v2/positions", headers=HEADERS)
    return resp.status_code in [200, 207]

# ==========================================
# INTERFACCIA GRAFICA (UI)
# ==========================================
st.title("🎛️ Centro di Controllo Quantitativo")
st.markdown("Monitoraggio in tempo reale del bot esecutivo collegato ad Alpaca.")

# Tasto per aggiornare i dati manualmente
if st.button("🔄 Aggiorna Dati Ora"):
    st.rerun()

st.divider()

# Chiamata alle API
account = get_account_info()
posizioni = get_open_positions()

if account:
    # 1. PANNELLO METRICHE PRINCIPALI
    st.subheader("📊 Stato del Capitale")
    col1, col2, col3, col4 = st.columns(4)
    
    equity = float(account['portfolio_value'])
    buying_power = float(account['buying_power'])
    pnl_giornaliero = float(account['equity']) - float(account['last_equity'])
    perc_giornaliera = (pnl_giornaliero / float(account['last_equity'])) * 100
    
    col1.metric("Equity Totale ($)", f"${equity:,.2f}")
    col2.metric("Buying Power Disponibile", f"${buying_power:,.2f}")
    col3.metric("Profitto di Oggi ($)", f"${pnl_giornaliero:,.2f}", f"{perc_giornaliera:,.2f}%")
    col4.metric("Posizioni Attive", f"{len(posizioni)} Titoli")
    
    st.divider()
    
    # 2. TABELLA POSIZIONI APERTE
    st.subheader("🛒 Portafoglio in Tempo Reale")
    
    if len(posizioni) > 0:
        # Costruiamo un DataFrame pulito per visualizzare le posizioni
        dati_posizioni = []
        for p in posizioni:
            dati_posizioni.append({
                "Ticker": p['symbol'],
                "Lati": p['side'].upper(),
                "Quantità": p['qty'],
                "Prezzo Ingresso": f"${float(p['avg_entry_price']):.2f}",
                "Prezzo Attuale": f"${float(p['current_price']):.2f}",
                "Valore Mercato": f"${float(p['market_value']):.2f}",
                "Profitto/Perdita ($)": float(p['unrealized_pl'])
            })
            
        df = pd.DataFrame(dati_posizioni)
        
        # Coloriamo in verde i profitti e in rosso le perdite
        def colora_pnl(val):
            color = 'green' if val > 0 else 'red'
            return f'color: {color}; font-weight: bold;'
            
        st.dataframe(df.style.map(colora_pnl, subset=['Profitto/Perdita ($)']), use_container_width=True)
    else:
        st.info("Nessuna posizione aperta. Il bot è in attesa di nuovi segnali di mercato.")
        
    st.divider()
    
    # 3. ZONA DI EMERGENZA (PANIC BUTTON)
    st.subheader("🚨 Gestione Rischio (Intervento Manuale)")
    st.warning("ATTENZIONE: Cliccando questo tasto chiuderai ISTANTANEAMENTE tutte le posizioni aperte sul conto a prezzo di mercato.")
    
    col_panic, _ = st.columns([1, 3])
    with col_panic:
        if st.button("🛑 CHIUDI TUTTE LE POSIZIONI", type="primary"):
            with st.spinner("Invio ordine di liquidazione totale al broker..."):
                successo = close_all_positions()
                time.sleep(2) # Pausa per permettere al broker di processare
                if successo:
                    st.success("Tutte le posizioni sono state chiuse con successo!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Errore durante la chiusura delle posizioni.")
else:
    st.error("Impossibile connettersi ad Alpaca. Verifica le tue API Key.")
