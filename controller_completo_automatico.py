import yfinance as yf
import pandas as pd
import requests
import numpy as np
from datetime import datetime

# ==========================================
# CONFIGURAZIONE CREDENZIALI
# ==========================================
TELEGRAM_TOKEN = "8815402200:AAEOwcUUvrfk82DPWQRhZOaF9zNrTxgw8qQ"
TELEGRAM_CHAT_ID = "7864993931"

ALPACA_API_KEY = "PKXI7EN3SIKMTWTCT7U2M7R4DZ"
ALPACA_SECRET_KEY = "E3xykXwW3251vfi6bkKUiCuBLfpB5WCAbgXDY7aDko8T"
ALPACA_BASE_URL = "https://paper-api.alpaca.markets" 

# ==========================================
# IMPOSTAZIONI ASSET ALLOCATION E GESTIONE RISCHIO
# ==========================================
CAPITALE_BASE_OPZIONI = 25000  
PREMIO_MENSILE_PRO = 2.5       
BUFFER_SICUREZZA_PRO = 3.0     

CAPITALE_PER_TRADE_SISTEMI = 5000 

# Parametri Uscita Automatica (in decimali: 0.10 = 10%)
TAKE_PROFIT_PERC = 0.10  
STOP_LOSS_PERC = -0.05   

WL_OPZIONI = ["AAPL", "MSFT"]
WL_MEAN_REV = ["AMD", "NVDA", "TSLA"]
WL_TREND = ["AMZN", "META", "NFLX"]
WL_SMALL_CAP = ["IWM", "PLTR", "SOFI", "ROKU"]

# ------------------------------------------
# FUNZIONI DI TRASMISSIONE E BROKER
# ------------------------------------------
def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, data=payload)
    except Exception as e: print(f"Errore invio Telegram: {e}")

def invia_ordine_alpaca(ticker, azione, capitale, prezzo_attuale):
    quantita = int(capitale / prezzo_attuale)
    if quantita <= 0: return False

    url = f"{ALPACA_BASE_URL}/v2/orders"
    headers = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY, "Content-Type": "application/json"}
    data = {"symbol": ticker, "qty": str(quantita), "side": azione.lower(), "type": "market", "time_in_force": "day"}
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code in [200, 201]: return quantita
        else: return False
    except: return False

def chiudi_posizione_alpaca(ticker):
    """Vende l'intera posizione posseduta per un determinato ticker."""
    url = f"{ALPACA_BASE_URL}/v2/positions/{ticker}"
    headers = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}
    try:
        resp = requests.delete(url, headers=headers)
        return resp.status_code == 200
    except: return False

def gestisci_portafoglio_e_uscite():
    """Legge le posizioni, chiude quelle in TP/SL e restituisce i ticker ancora aperti."""
    url = f"{ALPACA_BASE_URL}/v2/positions"
    headers = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY}
    
    report_uscite = []
    titoli_mantenuti = []
    
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            posizioni = resp.json()
            for p in posizioni:
                ticker = p['symbol']
                pl_perc = float(p['unrealized_plpc']) # Es: 0.05 corrisponde al 5%
                
                # Controllo Take Profit
                if pl_perc >= TAKE_PROFIT_PERC:
                    if chiudi_posizione_alpaca(ticker):
                        report_uscite.append(f"🎯 **TAKE PROFIT**: Venduto `{ticker}` (+{pl_perc*100:.1f}%)")
                # Controllo Stop Loss
                elif pl_perc <= STOP_LOSS_PERC:
                    if chiudi_posizione_alpaca(ticker):
                        report_uscite.append(f"🛑 **STOP LOSS**: Venduto `{ticker}` ({pl_perc*100:.1f}%)")
                else:
                    # Se non scatta né TP né SL, lo teniamo in portafoglio
                    titoli_mantenuti.append(ticker)
    except Exception as e:
        print(f"Errore lettura/gestione posizioni: {e}")
        
    return report_uscite, titoli_mantenuti

# ------------------------------------------
# INDICATORI MATEMATICI
# ------------------------------------------
def calcola_rsi(df, periodi=4):
    delta = df['Close'].diff()
    gain = delta.clip(lower=0).ewm(com=periodi-1, adjust=False).mean()
    loss = (-1 * delta.clip(upper=0)).ewm(com=periodi-1, adjust=False).mean()
    return 100 - (100 / (1 + (gain / loss)))

# ------------------------------------------
# CORE ENGINE: SCANSIONE AUTOMATICA LIVE
# ------------------------------------------
def esegui_scansione_e_trading():
    print(f"⏳ [{datetime.now().strftime('%H:%M:%S')}] Avvio esecuzione algoritmica automatica...")
    report_esecuzioni = []

    # 0. GESTIONE POSIZIONI ESISTENTI (TAKE PROFIT / STOP LOSS)
    report_chiusure, titoli_in_portafoglio = gestisci_portafoglio_e_uscite()
    if report_chiusure:
        report_esecuzioni.extend(report_chiusure)
        
    print(f"💼 Titoli attualmente in portafoglio: {titoli_in_portafoglio}")

    # 1. STRATEGIA VENDITA OPZIONI PRO
    for ticker in WL_OPZIONI:
        if ticker in titoli_in_portafoglio: continue
        try:
            df = yf.Ticker(ticker).history(period="1mo", interval="1d")
            apertura_mese = df['Open'].iloc[0]
            prezzo_attuale = df['Close'].iloc[-1]
            variazione_mensile = ((prezzo_attuale - apertura_mese) / apertura_mese) * 100
            
            if variazione_mensile >= -BUFFER_SICUREZZA_PRO:
                report_esecuzioni.append(f"🛡️ **OPZIONI PRO ({ticker})**: Condizioni stabili. Premio stimato: +{PREMIO_MENSILE_PRO}%.")
        except: pass

    # 2. STRATEGIA MEAN REVERSION HIGH-BETA
    for ticker in WL_MEAN_REV:
        if ticker in titoli_in_portafoglio: continue
        try:
            df = yf.Ticker(ticker).history(period="1y", interval="1d")
            df['SMA200'] = df['Close'].rolling(window=200).mean()
            df['RSI4'] = calcola_rsi(df, periodi=4)
            oggi = df.iloc[-1]
            
            if oggi['Close'] > oggi['SMA200'] and oggi['RSI4'] < 20:
                qty = invia_ordine_alpaca(ticker, "buy", CAPITALE_PER_TRADE_SISTEMI, oggi['Close'])
                if qty:
                    report_esecuzioni.append(f"🛒 **AUTO-BUY (Mean Rev)**: Comprate `{qty}` azioni di `{ticker}` a ${oggi['Close']:.2f} (RSI: {oggi['RSI4']:.1f})")
        except: pass

    # 3. STRATEGIA TREND FOLLOWING (BREAKOUT)
    for ticker in WL_TREND:
        if ticker in titoli_in_portafoglio: continue
        try:
            df = yf.Ticker(ticker).history(period="1y", interval="1d")
            df['SMA200'] = df['Close'].rolling(window=200).mean()
            df['Max20'] = df['High'].rolling(window=20).max().shift(1)
            oggi = df.iloc[-1]
            
            if oggi['Close'] > oggi['Max20'] and oggi['Close'] > oggi['SMA200']:
                qty = invia_ordine_alpaca(ticker, "buy", CAPITALE_PER_TRADE_SISTEMI, oggi['Close'])
                if qty:
                    report_esecuzioni.append(f"🔥 **AUTO-BUY (Trend)**: Breakout su `{ticker}`. Eseguite `{qty}` azioni.")
        except: pass

    # 4. STRATEGIA SMALL CAP (BOLLINGER BREAKOUT)
    for ticker in WL_SMALL_CAP:
        if ticker in titoli_in_portafoglio: continue
        try:
            df = yf.Ticker(ticker).history(period="6mo", interval="1d")
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            df['Upper'] = df['SMA50'] + (df['Close'].rolling(window=20).std() * 2)
            oggi = df.iloc[-1]
            
            if oggi['Close'] > oggi['Upper']:
                qty = invia_ordine_alpaca(ticker, "buy", CAPITALE_PER_TRADE_SISTEMI, oggi['Close'])
                if qty:
                    report_esecuzioni.append(f"🚀 **AUTO-BUY (Small Cap)**: Esplosione volumi su `{ticker}`. Entrate `{qty}` azioni.")
        except: pass

    # Invio riepilogo operativo centralizzato
    if report_esecuzioni:
        msg = f"🤖 **SISTEMA AUTOMATICO CENTRALIZZATO**\nReport del {datetime.now().strftime('%d/%m/%Y')}\n\n"
        for rep in report_esecuzioni: msg += rep + "\n\n"
        send_telegram_msg(msg)
    else:
        send_telegram_msg(f"🤖 **SISTEMA AUTOMATICO CENTRALIZZATO**\nNessuna esecuzione. Il capitale è parcheggiato al sicuro.")

if __name__ == "__main__":
    esegui_scansione_e_trading()
