# Nifty AI Analysis Script with Telegram Output

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from ta.trend import MACD, EMAIndicator
from ta.momentum import RSIIndicator
import pytz
# ========== CONFIG ==========
BOT_TOKEN = "7974119756:AAESnz98xnm3XhPqoUkVQ6FQVQjOlsWAfw4"
CHAT_ID = "622334857"
INDEX = "^NSEI"
BANK_NIFTY = "^NSEBANK"
EXPIRY = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")  # Approx expiry


def fetch_data(symbol):
    df = yf.download(symbol, period="5d", interval="15m", auto_adjust=True)
    df.dropna(inplace=True)
    return df

#def supertrend(df, period=10, multiplier=3):
    # Calculate basic price
    hl2 = (df['High'] + df['Low']) / 2

    # Calculate ATR using True Range method
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR'] = df['TR'].rolling(window=period).mean()

    # Upper and Lower Bands
    df['UpperBand'] = hl2 + multiplier * df['ATR']
    df['LowerBand'] = hl2 - multiplier * df['ATR']

    # Initialize Supertrend
    df['Supertrend'] = True

  #  for i in range(period, len(df)):
     #   if pd.isna(df['ATR'].iloc[i]):
         #   continue  # skip until ATR is fully formed

    #    close = df['Close'].iloc[i]
    #    prev_upper = df['UpperBand'].iloc[i - 1]
    #    prev_lower = df['LowerBand'].iloc[i - 1]
    #   prev_supertrend = df['Supertrend'].iloc[i - 1]

    #    if close > prev_upper:
    #        df.at[i, 'Supertrend'] = True
    #   elif close < prev_lower:
    #       df.at[i, 'Supertrend'] = False
    #     else:
    #       df.at[i, 'Supertrend'] = prev_supertrend

    # Drop helper columns to clean up
   # df.drop(columns=['H-L', 'H-PC', 'L-PC', 'TR'], inplace=True)

  #  return df
def ema_strategy(df):
    ema_5 = EMAIndicator(df['Close'], window=5).ema_indicator()
    ema_20 = EMAIndicator(df['Close'], window=20).ema_indicator()
    df['EMA_5'] = ema_5
    df['EMA_20'] = ema_20
    return df

def detect_volume_spike(df):
    avg_vol = df['Volume'].rolling(window=20).mean()
    df['Volume_Spike'] = df['Volume'] > 1.5 * avg_vol
    return df
def detect_candlestick_pattern(df):
    last = df.iloc[-1]
    body = abs(last['Close'] - last['Open'])
    candle_range = last['High'] - last['Low']
    upper_wick = last['High'] - max(last['Close'], last['Open'])
    lower_wick = min(last['Close'], last['Open']) - last['Low']

    if body < candle_range * 0.3 and upper_wick > lower_wick * 2:
        return "Inverted Hammer"
    elif body < candle_range * 0.3 and lower_wick > upper_wick * 2:
        return "Hammer"
    elif last['Close'] > last['Open'] and body > candle_range * 0.6:
        return "Bullish Marubozu"
    elif last['Close'] < last['Open'] and body > candle_range * 0.6:
        return "Bearish Marubozu"
    else:
        return "No pattern"
def get_option_chain():
    nifty = yf.Ticker("^NSEI")
    try:
        oc = nifty.option_chain(EXPIRY)
        calls = oc.calls.sort_values("openInterest", ascending=False).head(3)
        puts = oc.puts.sort_values("openInterest", ascending=False).head(3)
        return calls[['strike', 'openInterest']], puts[['strike', 'openInterest']]
    except Exception:
        return None, None

def get_vix():
    vix = yf.Ticker("^INDIAVIX")
    vix_hist = vix.history(period="1d")
    return vix_hist['Close'].iloc[-1] if not vix_hist.empty else None

def get_fii_dii():
    # Dummy values (replace with scraping or API source if available)
    return {"FII": "+₹850 Cr", "DII": "-₹200 Cr"}
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

# ========== MAIN SCRIPT ==========
nifty = fetch_data(INDEX)
nifty = supertrend(nifty)
nifty = ema_strategy(nifty)
nifty = detect_volume_spike(nifty)

bn = fetch_data(BANK_NIFTY)
bn = ema_strategy(bn)
bn = supertrend(bn)

rsi = RSIIndicator(nifty['Close'], window=14).rsi().iloc[-1]
macd = MACD(nifty['Close']).macd().iloc[-1]
macd_signal = MACD(nifty['Close']).macd_signal().iloc[-1]

pattern = detect_candlestick_pattern(nifty)
vix = get_vix()
fii_dii = get_fii_dii()
calls, puts = get_option_chain()

trend = "⬆️ Bullish" if nifty['Supertrend'].iloc[-1] and nifty['EMA_5'].iloc[-1] > nifty['EMA_20'].iloc[-1] else "⬇️ Bearish"
bn_confirm = "Yes" if bn['Supertrend'].iloc[-1] and bn['EMA_5'].iloc[-1] > bn['EMA_20'].iloc[-1] else "No"

msg = f"""
📈 *Nifty AI Trade Plan – {datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%A, %d %B %Y')}*

*Current Price:* ₹{nifty['Close'].iloc[-1]:.2f}
*Trend:* {trend}
*Bank Nifty Confirmation:* {bn_confirm}

🧠 *Pattern:* {pattern}
📊 *RSI:* {rsi:.2f}
📊 *MACD:* {macd:.2f} | Signal: {macd_signal:.2f}
💥 *Volume Spike:* {'Yes' if nifty['Volume_Spike'].iloc[-1] else 'No'}
🧮 *VWAP:* ₹{(nifty['Close'] * nifty['Volume']).cumsum().iloc[-1] / nifty['Volume'].cumsum().iloc[-1]:.2f}

🌪️ *India VIX:* {vix:.2f} 🔻
📊 *FII:* {fii_dii['FII']} | *DII:* {fii_dii['DII']}

🔗 *Option Chain Highlights:*
"""

if calls is not None:
    msg += "📈 *Calls:*\n"
    for _, row in calls.iterrows():
        msg += f"- Strike ₹{row['strike']} | OI: {row['openInterest']}\n"
if puts is not None:
    msg += "📉 *Puts:*\n"
    for _, row in puts.iterrows():
        msg += f"- Strike ₹{row['strike']} | OI: {row['openInterest']}\n"

send_telegram(msg)
print("Message sent to Telegram ✅")
