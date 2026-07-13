import yfinance as yf
import pandas as pd
import requests
import numpy as np
from datetime import datetime

# ==========================================
# CONFIGURAZIONE CREDENZIALI (INSERISCI LE TUE)
# ==========================================
TELEGRAM_TOKEN = "8815402200:AAEOwcUUvrfk82DPWQRhZOaF9zNrTxgw8qQ"
TELEGRAM_CHAT_ID = "7864993931"

ALPACA_API_KEY = "PKXI7EN3SIKMTWTCT7U2M7R4DZ"
ALPACA_SECRET_KEY = "E3xykXwW3251vfi6bkKUiCuBLfpB5WCAbgXDY7aDko8T"
ALPACA_BASE_URL = "https://paper-api.alpaca.markets" 

# ==========================================
# IMPOSTAZIONI ASSET ALLOCATION & PARAMETRI PRO
# ==========================================
CAPITALE_BASE_OPZIONI = 10000  # Allocazione per singolo contratto Opzioni
PREMIO_MENSILE_PRO = 2.5       # Target premio 2.5%
BUFFER_SICUREZZA_PRO = 3.0     # Protezione al ribasso 3%

CAPITALE_PER_TRADE_SISTEMI = 1000 # Per Mean Rev, Trend e Small Cap

WL_OPZIONI = ["AAPL", "MSFT"]
WL_MEAN_REV = ["AMD", "NVDA", "TSLA"]
WL_TREND = ["AMZN", "META", "NFLX"]
WL_SMALL_CAP = ["IWM", "PLTR", "SOFI", "ROKU"]

# ------------------------------------------
# FUNZIONI DI TRASMISSIONE (TELEGRAM & ALPACA)
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
    headers = {
        "APCA-API-KEY-ID": ALPACA_API_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "symbol": ticker,
        "qty": str(quantita),
        "side": azione.lower(), # 'buy' o 'sell'
        "type": "market",
        "time_in_force": "day"
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code in [200, 201]:
            return quantita
        else:
            print(f"Errore esecuzione Broker su {ticker}: {response.text}")
            return False
    except Exception as e:
        print(f"Errore connessione Alpaca su {ticker}: {e}")
        return False

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

    # 1. STRATEGIA VENDITA OPZIONI PRO (Modello Proxy di Screening Segnale)
    for ticker in WL_OPZIONI:
        try:
            df = yf.Ticker(ticker).history(period="1mo", interval="1d")
            apertura_mese = df['Open'].iloc[0]
            prezzo_attuale = df['Close'].iloc[-1]
            variazione_mensile = ((prezzo_attuale - apertura_mese) / apertura_mese) * 100
            
            if variazione_mensile >= -BUFFER_SICUREZZA_PRO:
                # Condizioni ottimali: Il mercato tiene, inviamo notifica di monitoraggio posizioni
                report_esecuzioni.append(f"🛡️ **OPZIONI PRO ({ticker})**: Condizioni stabili. Premio stimato corrente: +{PREMIO_MENSILE_PRO}% sul collaterale.")
        except Exception as e: print(f"Errore Opzioni {ticker}: {e}")

    # 2. STRATEGIA MEAN REVERSION HIGH-BETA
    for ticker in WL_MEAN_REV:
        try:
            df = yf.Ticker(ticker).history(period="1y", interval="1d")
            df['SMA200'] = df['Close'].rolling(window=200).mean()
            df['RSI4'] = calcola_rsi(df, periodi=4)
            oggi = df.iloc[-1]
            
            if oggi['Close'] > oggi['SMA200'] and oggi['RSI4'] < 20:
                qty = invia_ordine_alpaca(ticker, "buy", CAPITALE_PER_TRADE_SISTEMI, oggi['Close'])
                if qty:
                    report_esecuzioni.append(f"🛒 **AUTO-BUY (Mean Rev)**: Eseguito ordine su `{ticker}`. Acquistate `{qty}` azioni a ${oggi['Close']:.2f} (RSI: {oggi['RSI4']:.1f})")
        except Exception as e: print(f"Errore Mean Rev {ticker}: {e}")

    # 3. STRATEGIA TREND FOLLOWING (BREAKOUT)
    for ticker in WL_TREND:
        try:
            df = yf.Ticker(ticker).history(period="1y", interval="1d")
            df['SMA200'] = df['Close'].rolling(window=200).mean()
            df['Max20'] = df['High'].rolling(window=20).max().shift(1)
            oggi = df.iloc[-1]
            
            if oggi['Close'] > oggi['Max20'] and oggi['Close'] > oggi['SMA200']:
                qty = invia_ordine_alpaca(ticker, "buy", CAPITALE_PER_TRADE_SISTEMI, oggi['Close'])
                if qty:
                    report_esecuzioni.append(f"🔥 **AUTO-BUY (Trend)**: Rottura massimi a 20 giorni su `{ticker}`. Eseguite `{qty}` azioni.")
        except Exception as e: print(f"Errore Trend {ticker}: {e}")

    # 4. STRATEGIA SMALL CAP (BOLLINGER BREAKOUT)
    for ticker in WL_SMALL_CAP:
        try:
            df = yf.Ticker(ticker).history(period="6mo", interval="1d")
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            df['Upper'] = df['SMA50'] + (df['Close'].rolling(window=20).std() * 2)
            oggi = df.iloc[-1]
            
            if oggi['Close'] > oggi['Upper']:
                qty = invia_ordine_alpaca(ticker, "buy", CAPITALE_PER_TRADE_SISTEMI, oggi['Close'])
                if qty:
                    report_esecuzioni.append(f"🚀 **AUTO-BUY (Small Cap)**: Esplosione di volatilità su `{ticker}`. Entrate `{qty}` azioni a mercato.")
        except Exception as e: print(f"Errore Small Cap {ticker}: {e}")

    # Invio riepilogo operativo centralizzato
    if report_esecuzioni:
        msg = f"🤖 **SISTEMA AUTOMATICO CENTRALIZZATO**\nReport del {datetime.now().strftime('%d/%m/%Y')}\n\n"
        for rep in report_esecuzioni: msg += rep + "\n\n"
        send_telegram_msg(msg)
    else:
        send_telegram_msg(f"🤖 **SISTEMA AUTOMATICO CENTRALIZZATO**\nNessun ordine inoltrato a mercato oggi. Tutti i parametri sono sotto i livelli di trigger.")

if __name__ == "__main__":
    esegui_scansione_e_trading()