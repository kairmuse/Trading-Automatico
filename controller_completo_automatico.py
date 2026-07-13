import yfinance as yf
import pandas as pd
import requests
import numpy as np
from datetime import datetime, timedelta

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

TAKE_PROFIT_PERC = 0.10  
STOP_LOSS_PERC = -0.05   

WL_OPZIONI = ["AAPL", "MSFT"]
WL_MEAN_REV = ["AMD", "NVDA", "TSLA"]
WL_TREND = ["AMZN", "META", "NFLX"]
WL_SMALL_CAP = ["IWM", "PLTR", "SOFI", "ROKU"]

HEADERS = {"APCA-API-KEY-ID": ALPACA_API_KEY, "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY, "Content-Type": "application/json"}

# ------------------------------------------
# FUNZIONI DI TRASMISSIONE E BROKER
# ------------------------------------------
def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: requests.post(url, data=payload)
    except: pass

def invia_ordine_alpaca(ticker, azione, capitale, prezzo_attuale):
    quantita = int(capitale / prezzo_attuale)
    if quantita <= 0: return False

    url = f"{ALPACA_BASE_URL}/v2/orders"
    data = {"symbol": ticker, "qty": str(quantita), "side": azione.lower(), "type": "market", "time_in_force": "day"}
    
    try:
        response = requests.post(url, json=data, headers=HEADERS)
        if response.status_code in [200, 201]: return quantita
        else: return False
    except: return False

# ------------------------------------------
# IL NUOVO MOTORE DERIVATI (OPTIONS ENGINE)
# ------------------------------------------
def vendi_put_alpaca(ticker, prezzo_attuale, buffer_perc):
    """
    Trova la Put ottimale (30-45 giorni) con strike al di sotto del buffer e la vende.
    Ritorna il simbolo del contratto se l'ordine ha successo, altrimenti False.
    """
    target_strike = prezzo_attuale * (1 - (buffer_perc / 100))
    
    # Finestra temporale: 30-45 giorni da oggi
    oggi = datetime.now()
    data_min = (oggi + timedelta(days=30)).strftime('%Y-%m-%d')
    data_max = (oggi + timedelta(days=45)).strftime('%Y-%m-%d')
    
    # 1. Cerca i contratti disponibili
    url_contracts = f"{ALPACA_BASE_URL}/v2/options/contracts?underlying_symbols={ticker}&status=active&type=put&expiration_date_gte={data_min}&expiration_date_lte={data_max}"
    
    try:
        resp = requests.get(url_contracts, headers=HEADERS)
        if resp.status_code != 200: return False
        
        contratti = resp.json().get('option_contracts', [])
        if not contratti: return False
        
        # 2. Trova il contratto con lo Strike più vicino al nostro Target Strike (ma inferiore o uguale ad esso)
        contratti_validi = [c for c in contratti if float(c['strike_price']) <= target_strike]
        if not contratti_validi: return False
        
        # Ordina per strike decrescente per prendere quello più alto sotto il nostro limite
        contratti_validi.sort(key=lambda x: float(x['strike_price']), reverse=True)
        contratto_scelto = contratti_validi[0]['symbol']
        strike_scelto = contratti_validi[0]['strike_price']
        
        # 3. Invia l'ordine "Sell to Open" (Vendita allo scoperto della Put)
        url_order = f"{ALPACA_BASE_URL}/v2/orders"
        data_order = {
            "symbol": contratto_scelto,
            "qty": "1", # 1 contratto = 100 azioni
            "side": "sell",
            "type": "market",
            "time_in_force": "day"
        }
        
        resp_order = requests.post(url_order, json=data_order, headers=HEADERS)
        if resp_order.status_code in [200, 201]:
            return f"{contratto_scelto} (Strike: ${strike_scelto})"
        else:
            return False
            
    except Exception as e:
        print(f"Errore Motore Opzioni: {e}")
        return False

# ------------------------------------------
# GESTIONE POSIZIONI ESISTENTI (AZIONARIO)
# ------------------------------------------
def chiudi_posizione_alpaca(ticker):
    url = f"{ALPACA_BASE_URL}/v2/positions/{ticker}"
    try:
        resp = requests.delete(url, headers=HEADERS)
        return resp.status_code == 200
    except: return False

def gestisci_portafoglio_e_uscite():
    url = f"{ALPACA_BASE_URL}/v2/positions"
    report_uscite = []
    titoli_mantenuti = []
    
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            posizioni = resp.json()
            for p in posizioni:
                ticker = p['symbol']
                pl_perc = float(p['unrealized_plpc'])
                
                # Ignoriamo le opzioni in questa gestione uscite semplificata
                if p['asset_class'] == 'us_option':
                    titoli_mantenuti.append(ticker)
                    continue

                if pl_perc >= TAKE_PROFIT_PERC:
                    if chiudi_posizione_alpaca(ticker): report_uscite.append(f"🎯 **TAKE PROFIT**: Venduto `{ticker}` (+{pl_perc*100:.1f}%)")
                elif pl_perc <= STOP_LOSS_PERC:
                    if chiudi_posizione_alpaca(ticker): report_uscite.append(f"🛑 **STOP LOSS**: Venduto `{ticker}` ({pl_perc*100:.1f}%)")
                else:
                    titoli_mantenuti.append(ticker)
    except: pass
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
# CORE ENGINE: SCANSIONE AUTOMATICA LIVE E AUDIT
# ------------------------------------------
def esegui_scansione_e_trading():
    print(f"⏳ [{datetime.now().strftime('%H:%M:%S')}] Avvio esecuzione algoritmica automatica...")
    report_esecuzioni = []
    log_decisioni = []

    # 0. GESTIONE POSIZIONI ESISTENTI
    report_chiusure, titoli_in_portafoglio = gestisci_portafoglio_e_uscite()
    if report_chiusure: report_esecuzioni.extend(report_chiusure)

    # 1. STRATEGIA VENDITA OPZIONI PRO (Ora Completamente Automatica)
    for ticker in WL_OPZIONI:
        # Controllo se abbiamo già opzioni attive su questo sottostante
        ha_opzioni_attive = any(ticker in p for p in titoli_in_portafoglio)
        if ha_opzioni_attive:
            log_decisioni.append({"Ticker": ticker, "Strategy": "Opzioni", "Decision": "IGNORE", "Reason": "Contratto Opzione già in portafoglio"})
            continue
            
        try:
            df = yf.Ticker(ticker).history(period="1mo", interval="1d")
            apertura_mese = df['Open'].iloc[0]
            prezzo_attuale = df['Close'].iloc[-1]
            variazione_mensile = ((prezzo_attuale - apertura_mese) / apertura_mese) * 100
            
            if variazione_mensile >= -BUFFER_SICUREZZA_PRO:
                contratto_venduto = vendi_put_alpaca(ticker, prezzo_attuale, BUFFER_SICUREZZA_PRO)
                if contratto_venduto:
                    report_esecuzioni.append(f"🛡️ **AUTO-SELL (Opzioni)**: Venduta 1 PUT su `{ticker}`. Contratto: {contratto_venduto}.")
                    log_decisioni.append({"Ticker": ticker, "Strategy": "Opzioni", "Decision": "SELL PUT", "Reason": f"Venduto {contratto_venduto}"})
                else:
                    log_decisioni.append({"Ticker": ticker, "Strategy": "Opzioni", "Decision": "ERROR/IGNORE", "Reason": "Impossibile trovare/eseguire contratto idoneo"})
            else:
                log_decisioni.append({"Ticker": ticker, "Strategy": "Opzioni", "Decision": "IGNORE", "Reason": f"Var {variazione_mensile:.1f}% ha sfondato il buffer (-{BUFFER_SICUREZZA_PRO}%)"})
        except Exception as e:
            log_decisioni.append({"Ticker": ticker, "Strategy": "Opzioni", "Decision": "ERROR", "Reason": str(e)})

    # 2. STRATEGIA MEAN REVERSION
    for ticker in WL_MEAN_REV:
        if ticker in titoli_in_portafoglio:
            log_decisioni.append({"Ticker": ticker, "Strategy": "MeanRev", "Decision": "IGNORE", "Reason": "Già in portafoglio"})
            continue
        try:
            df = yf.Ticker(ticker).history(period="1y", interval="1d")
            df['SMA200'] = df['Close'].rolling(window=200).mean()
            df['RSI4'] = calcola_rsi(df, periodi=4)
            oggi = df.iloc[-1]
            
            if oggi['Close'] > oggi['SMA200'] and oggi['RSI4'] < 20:
                qty = invia_ordine_alpaca(ticker, "buy", CAPITALE_PER_TRADE_SISTEMI, oggi['Close'])
                if qty:
                    report_esecuzioni.append(f"🛒 **AUTO-BUY (Mean Rev)**: `{qty}` azioni `{ticker}` a ${oggi['Close']:.2f}")
                    log_decisioni.append({"Ticker": ticker, "Strategy": "MeanRev", "Decision": "BUY", "Reason": f"RSI {oggi['RSI4']:.1f} < 20"})
            else:
                log_decisioni.append({"Ticker": ticker, "Strategy": "MeanRev", "Decision": "IGNORE", "Reason": f"RSI {oggi['RSI4']:.1f} non in ipervenduto"})
        except Exception as e:
            log_decisioni.append({"Ticker": ticker, "Strategy": "MeanRev", "Decision": "ERROR", "Reason": str(e)})

    # 3. STRATEGIA TREND FOLLOWING
    for ticker in WL_TREND:
        if ticker in titoli_in_portafoglio:
            log_decisioni.append({"Ticker": ticker, "Strategy": "Trend", "Decision": "IGNORE", "Reason": "Già in portafoglio"})
            continue
        try:
            df = yf.Ticker(ticker).history(period="1y", interval="1d")
            df['SMA200'] = df['Close'].rolling(window=200).mean()
            df['Max20'] = df['High'].rolling(window=20).max().shift(1)
            oggi = df.iloc[-1]
            
            if oggi['Close'] > oggi['Max20'] and oggi['Close'] > oggi['SMA200']:
                qty = invia_ordine_alpaca(ticker, "buy", CAPITALE_PER_TRADE_SISTEMI, oggi['Close'])
                if qty:
                    report_esecuzioni.append(f"🔥 **AUTO-BUY (Trend)**: Breakout su `{ticker}`. Eseguite `{qty}` azioni.")
                    log_decisioni.append({"Ticker": ticker, "Strategy": "Trend", "Decision": "BUY", "Reason": "Breakout Max20 giorni"})
            else:
                log_decisioni.append({"Ticker": ticker, "Strategy": "Trend", "Decision": "IGNORE", "Reason": "Nessun Breakout"})
        except Exception as e:
            log_decisioni.append({"Ticker": ticker, "Strategy": "Trend", "Decision": "ERROR", "Reason": str(e)})

    # 4. STRATEGIA SMALL CAP
    for ticker in WL_SMALL_CAP:
        if ticker in titoli_in_portafoglio:
            log_decisioni.append({"Ticker": ticker, "Strategy": "SmallCap", "Decision": "IGNORE", "Reason": "Già in portafoglio"})
            continue
        try:
            df = yf.Ticker(ticker).history(period="6mo", interval="1d")
            df['SMA50'] = df['Close'].rolling(window=50).mean()
            df['Upper'] = df['SMA50'] + (df['Close'].rolling(window=20).std() * 2)
            oggi = df.iloc[-1]
            
            if oggi['Close'] > oggi['Upper']:
                qty = invia_ordine_alpaca(ticker, "buy", CAPITALE_PER_TRADE_SISTEMI, oggi['Close'])
                if qty:
                    report_esecuzioni.append(f"🚀 **AUTO-BUY (Small Cap)**: Esplosione volumi su `{ticker}`. Entrate `{qty}` azioni.")
                    log_decisioni.append({"Ticker": ticker, "Strategy": "SmallCap", "Decision": "BUY", "Reason": "Breakout Banda Bollinger Sup"})
            else:
                log_decisioni.append({"Ticker": ticker, "Strategy": "SmallCap", "Decision": "IGNORE", "Reason": "Nessun Breakout di volatilità"})
        except Exception as e:
            log_decisioni.append({"Ticker": ticker, "Strategy": "SmallCap", "Decision": "ERROR", "Reason": str(e)})

    # Salvataggio del Diario Decisioni
    try:
        df_log = pd.DataFrame(log_decisioni)
        df_log.to_csv("decision_log.csv", index=False)
    except: pass

    # Invio riepilogo Telegram
    if report_esecuzioni:
        msg = f"🤖 **SISTEMA AUTOMATICO CENTRALIZZATO**\nReport del {datetime.now().strftime('%d/%m/%Y')}\n\n"
        for rep in report_esecuzioni: msg += rep + "\n\n"
        send_telegram_msg(msg)
    else:
        send_telegram_msg(f"🤖 **SISTEMA AUTOMATICO CENTRALIZZATO**\nNessuna esecuzione a mercato. Log decisionale aggiornato sulla Dashboard.")

if __name__ == "__main__":
    esegui_scansione_e_trading()
