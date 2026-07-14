import yfinance as yf
import pandas as pd
import requests
import numpy as np
from datetime import datetime, timedelta
import os

# ==========================================
# CREDENZIALI API (GitHub Secrets)
# ==========================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8815402200:AAEOwcUUvrfk82DPWQRhZOaF9zNrTxgw8qQ")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7864993931")
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "PKXI7EN3SIKMTWTCT7U2M7R4DZ")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "E3xykXwW3251vfi6bkKUiCuBLfpB5WCAbgXDY7aDko8T")
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

HEADERS = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY, "Content-Type": "application/json"}

# Parametri operativi
CAPITALE_PER_TRADE = 5000
BUFFER_SICUREZZA_PRO = 3.0  # -3% per vendere le Put
TAKE_PROFIT_PERC = 10.0     # +10% per incassare i guadagni azionari
STOP_LOSS_PERC = 5.0        # -5% per tagliare le perdite azionarie

WL_OPZIONI = ["AAPL", "MSFT"]
WL_MEAN_REV = ["AMD", "NVDA", "TSLA"]
WL_TREND = ["AMZN", "META", "NFLX"]
WL_SMALL_CAP = ["IWM", "PLTR", "SOFI", "ROKU"]

# ------------------------------------------
# FUNZIONI UTILI
# ------------------------------------------
def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"})
    except: pass

def invia_ordine_alpaca(ticker, azione, capitale, prezzo_attuale):
    quantita = int(capitale / prezzo_attuale)
    if quantita <= 0: return False
    url = f"{ALPACA_BASE_URL}/v2/orders"
    data = {"symbol": ticker, "qty": str(quantita), "side": azione.lower(), "type": "market", "time_in_force": "day"}
    try:
        resp = requests.post(url, json=data, headers=HEADERS)
        return quantita if resp.status_code in [200, 201] else False
    except: return False

def chiudi_posizione_alpaca(ticker):
    # Chiude interamente la posizione a mercato
    url = f"{ALPACA_BASE_URL}/v2/positions/{ticker}"
    try:
        resp = requests.delete(url, headers=HEADERS)
        return resp.status_code == 200
    except: return False

def vendi_put_alpaca(ticker, prezzo_attuale, buffer_perc):
    target_strike = prezzo_attuale * (1 - (buffer_perc / 100))
    oggi = datetime.now()
    data_min = (oggi + timedelta(days=30)).strftime('%Y-%m-%d')
    data_max = (oggi + timedelta(days=45)).strftime('%Y-%m-%d')
    
    url_contracts = f"{ALPACA_BASE_URL}/v2/options/contracts?underlying_symbols={ticker}&status=active&type=put&expiration_date_gte={data_min}&expiration_date_lte={data_max}"
    try:
        resp = requests.get(url_contracts, headers=HEADERS)
        if resp.status_code != 200: return False, f"Blocco API Dati: {resp.text}"
            
        contratti = resp.json().get('option_contracts', [])
        if not contratti: return False, "Database opzioni vuoto per queste date."
            
        contratti_validi = [c for c in contratti if float(c['strike_price']) <= target_strike]
        if not contratti_validi: return False, f"Nessuno strike sotto al buffer (${target_strike:.2f})"
            
        contratti_validi.sort(key=lambda x: float(x['strike_price']), reverse=True)
        contratto_scelto = contratti_validi[0]['symbol']
        strike_scelto = contratti_validi[0]['strike_price']
        
        url_order = f"{ALPACA_BASE_URL}/v2/orders"
        data_order = {"symbol": contratto_scelto, "qty": "1", "side": "sell", "type": "market", "time_in_force": "day"}
        resp_order = requests.post(url_order, json=data_order, headers=HEADERS)
        
        if resp_order.status_code in [200, 201]:
            return f"{contratto_scelto} (Strike: ${strike_scelto})", "OK"
        else:
            return False, f"Ordine rifiutato dal Broker: {resp_order.text}"
    except Exception as e: return False, f"Errore Python: {str(e)}"

def get_portafoglio_attivo():
    # Ritorna un dizionario: { 'AAPL': -2.5, 'ROKU': 1.2 } (con P&L in percentuale)
    try:
        resp = requests.get(f"{ALPACA_BASE_URL}/v2/positions", headers=HEADERS)
        if resp.status_code == 200:
            return {p['symbol']: float(p['unrealized_plpc']) * 100 for p in resp.json()}
        return {}
    except: return {}

# ------------------------------------------
# MOTORE DI SCANSIONE E LOGICA
# ------------------------------------------
def esegui_trading():
    print("Avvio scansione mercati...")
    report_esecuzioni = []
    log_decisioni = []
    portafoglio = get_portafoglio_attivo()

    # 1. STRATEGIA OPZIONI PRO (Non applica Stop Loss / Take profit standard)
    for ticker in WL_OPZIONI:
        if ticker in portafoglio:
            log_decisioni.append({"Ticker": ticker, "Strategy": "Opzioni", "Decision": "IGNORE", "Reason": "Contratto già attivo"})
            continue
        try:
            df = yf.Ticker(ticker).history(period="1mo")
            var_mensile = ((df['Close'].iloc[-1] - df['Open'].iloc[0]) / df['Open'].iloc[0]) * 100
            
            if var_mensile >= -BUFFER_SICUREZZA_PRO:
                esito, messaggio = vendi_put_alpaca(ticker, df['Close'].iloc[-1], BUFFER_SICUREZZA_PRO)
                if esito:
                    report_esecuzioni.append(f"🛡️ **AUTO-SELL (Opzioni)**: Venduta Put su `{ticker}` ({esito})")
                    log_decisioni.append({"Ticker": ticker, "Strategy": "Opzioni", "Decision": "SELL PUT", "Reason": f"Var {var_mensile:.1f}% stabile"})
                else:
                    log_decisioni.append({"Ticker": ticker, "Strategy": "Opzioni", "Decision": "ERROR", "Reason": messaggio})
            else:
                log_decisioni.append({"Ticker": ticker, "Strategy": "Opzioni", "Decision": "IGNORE", "Reason": f"Var {var_mensile:.1f}% sotto il buffer"})
        except Exception as e:
            log_decisioni.append({"Ticker": ticker, "Strategy": "Opzioni", "Decision": "ERROR", "Reason": str(e)})

    # GESTORE PORTAFOGLIO: TAKE PROFIT E STOP LOSS
    def gestisci_posizione(ticker, strategia):
        pl_perc = portafoglio[ticker]
        if pl_perc >= TAKE_PROFIT_PERC:
            if chiudi_posizione_alpaca(ticker):
                report_esecuzioni.append(f"💰 **TAKE PROFIT**: Chiusa posizione su `{ticker}` a +{pl_perc:.2f}%")
                log_decisioni.append({"Ticker": ticker, "Strategy": strategia, "Decision": "SELL (TP)", "Reason": f"Raggiunto Target +{pl_perc:.2f}%"})
            else:
                log_decisioni.append({"Ticker": ticker, "Strategy": strategia, "Decision": "ERROR", "Reason": "Impossibile chiudere posizione per TP"})
        elif pl_perc <= -STOP_LOSS_PERC:
            if chiudi_posizione_alpaca(ticker):
                report_esecuzioni.append(f"🛑 **STOP LOSS**: Chiusa posizione su `{ticker}` a {pl_perc:.2f}%")
                log_decisioni.append({"Ticker": ticker, "Strategy": strategia, "Decision": "SELL (SL)", "Reason": f"Scattato Stop a {pl_perc:.2f}%"})
            else:
                log_decisioni.append({"Ticker": ticker, "Strategy": strategia, "Decision": "ERROR", "Reason": "Impossibile chiudere posizione per SL"})
        else:
            log_decisioni.append({"Ticker": ticker, "Strategy": strategia, "Decision": "HOLD", "Reason": f"P&L attuale: {pl_perc:.2f}% (In attesa)"})

    # 2. STRATEGIA MEAN REVERSION
    for ticker in WL_MEAN_REV:
        if ticker in portafoglio:
            gestisci_posizione(ticker, "MeanRev")
            continue
        try:
            df = yf.Ticker(ticker).history(period="1y")
            df['SMA200'] = df['Close'].rolling(200).mean()
            delta = df['Close'].diff()
            gain = delta.clip(lower=0).ewm(com=3, adjust=False).mean()
            loss = (-1 * delta.clip(upper=0)).ewm(com=3, adjust=False).mean()
            df['RSI4'] = 100 - (100 / (1 + (gain / loss)))
            oggi = df.iloc[-1]
            
            if oggi['Close'] > oggi['SMA200'] and oggi['RSI4'] < 20:
                qty = invia_ordine_alpaca(ticker, "buy", CAPITALE_PER_TRADE, oggi['Close'])
                if qty:
                    report_esecuzioni.append(f"🛒 **AUTO-BUY (Mean Rev)**: Comprate `{qty}` azioni di `{ticker}`")
                    log_decisioni.append({"Ticker": ticker, "Strategy": "MeanRev", "Decision": "BUY", "Reason": f"RSI {oggi['RSI4']:.1f} < 20 e sopra SMA200"})
                else:
                    log_decisioni.append({"Ticker": ticker, "Strategy": "MeanRev", "Decision": "ERROR", "Reason": "Errore invio ordine Alpaca"})
            else:
                log_decisioni.append({"Ticker": ticker, "Strategy": "MeanRev", "Decision": "IGNORE", "Reason": f"RSI {oggi['RSI4']:.1f} non in ipervenduto o sotto SMA200"})
        except Exception as e:
            log_decisioni.append({"Ticker": ticker, "Strategy": "MeanRev", "Decision": "ERROR", "Reason": str(e)})

    # 3. STRATEGIA TREND FOLLOWING
    for ticker in WL_TREND:
        if ticker in portafoglio:
            gestisci_posizione(ticker, "Trend")
            continue
        try:
            df = yf.Ticker(ticker).history(period="1y")
            df['SMA200'] = df['Close'].rolling(window=200).mean()
            df['Max20'] = df['High'].rolling(window=20).max().shift(1)
            oggi = df.iloc[-1]
            
            if oggi['Close'] > oggi['Max20'] and oggi['Close'] > oggi['SMA200']:
                qty = invia_ordine_alpaca(ticker, "buy", CAPITALE_PER_TRADE, oggi['Close'])
                if qty:
                    report_esecuzioni.append(f"🔥 **AUTO-BUY (Trend)**: Breakout su `{ticker}`. Comprate `{qty}` azioni.")
                    log_decisioni.append({"Ticker": ticker, "Strategy": "Trend", "Decision": "BUY", "Reason": "Breakout Max 20 Giorni e sopra SMA200"})
                else:
                    log_decisioni.append({"Ticker": ticker, "Strategy": "Trend", "Decision": "ERROR", "Reason": "Errore invio ordine Alpaca"})
            else:
                log_decisioni.append({"Ticker": ticker, "Strategy": "Trend", "Decision": "IGNORE", "Reason": "Nessun Breakout confermato"})
        except Exception as e:
            log_decisioni.append({"Ticker": ticker, "Strategy": "Trend", "Decision": "ERROR", "Reason": str(e)})

    # 4. STRATEGIA SMALL CAP
    for ticker in WL_SMALL_CAP:
        if ticker in portafoglio:
            gestisci_posizione(ticker, "SmallCap")
            continue
        try:
            df = yf.Ticker(ticker).history(period="6mo")
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            df['Upper'] = df['SMA50'] + (df['Close'].rolling(window=20).std() * 2)
            oggi = df.iloc[-1]
            
            if oggi['Close'] > oggi['Upper']:
                qty = invia_ordine_alpaca(ticker, "buy", CAPITALE_PER_TRADE, oggi['Close'])
                if qty:
                    report_esecuzioni.append(f"🚀 **AUTO-BUY (Small Cap)**: Esplosione volumi su `{ticker}`. Comprate `{qty}` azioni.")
                    log_decisioni.append({"Ticker": ticker, "Strategy": "SmallCap", "Decision": "BUY", "Reason": "Breakout Banda Bollinger Superiore"})
                else:
                    log_decisioni.append({"Ticker": ticker, "Strategy": "SmallCap", "Decision": "ERROR", "Reason": "Errore invio ordine Alpaca"})
            else:
                log_decisioni.append({"Ticker": ticker, "Strategy": "SmallCap", "Decision": "IGNORE", "Reason": "Nessun Breakout di volatilità"})
        except Exception as e:
            log_decisioni.append({"Ticker": ticker, "Strategy": "SmallCap", "Decision": "ERROR", "Reason": str(e)})

    # Salvataggio log su CSV
    pd.DataFrame(log_decisioni).to_csv("decision_log.csv", index=False)
    
    # Notifica Telegram
    if report_esecuzioni:
        msg = "🤖 **NOTIFICA BOT DI TRADING**\n\n" + "\n\n".join(report_esecuzioni)
        send_telegram_msg(msg)
    else:
        send_telegram_msg("🤖 Scansione completata. Nessuna operazione di acquisto o chiusura eseguita. Log salvati.")

if __name__ == "__main__":
    esegui_trading()
