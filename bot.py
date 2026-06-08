import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import time
import threading
from datetime import datetime

# =========================
# Telegram Config
# =========================
BOT_TOKEN = "8746602597:AAECtu4m4jx9WVnYjeewdJbvcJiMTYk8xM0"
CHAT_ID = "434014948"

def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# =========================
# Stocks Universe
# =========================
stocks = [
    "AAPL","MSFT","NVDA","AMZN","META","TSLA","AMD","GOOGL",
    "NFLX","COIN","PLTR","AVGO","INTC","CRM","UBER"
]

# =========================
# Market Time Filter (US Market)
# =========================
def market_open():
    now = datetime.now()

    # السوق الأمريكي تقريبًا 16:30 - 23:00 بتوقيت السعودية
    start_hour = 16
    end_hour = 23

    return start_hour <= now.hour < end_hour


# =========================
# Analysis Function
# =========================
def analyze(symbol, tf):

    df = yf.download(symbol, period="5d", interval=tf)
    if len(df) < 50:
        return None

    df["EMA200"] = ta.ema(df["Close"], 200)
    df["RSI"] = ta.rsi(df["Close"], 14)

    macd = ta.macd(df["Close"])
    df["MACD"] = macd["MACD_12_26_9"]
    df["SIGNAL"] = macd["MACDs_12_26_9"]

    last = df.iloc[-1]

    price = last["Close"]
    ema = last["EMA200"]
    rsi = last["RSI"]
    macd_v = last["MACD"]
    signal_v = last["SIGNAL"]

    bins = pd.cut(df["Close"], 20)
    vp = df.groupby(bins)["Volume"].sum()
    poc = vp.idxmax().mid

    sorted_vp = vp.sort_values(ascending=False)
    hvn = sorted_vp.index[0].mid
    lvn = sorted_vp.index[-1].mid

    sl = ema * 0.99

    if not (
        price > ema and
        macd_v > signal_v and
        macd_v > 0 and signal_v > 0 and
        rsi > 50 and
        poc > price * 1.02
    ):
        return None

    tp1_pct = ((poc - price) / price) * 100
    tp2_pct = ((hvn - price) / price) * 100
    tp3_pct = ((lvn - price) / price) * 100
    sl_pct = ((sl - price) / price) * 100

    msg = f"""
🔥 {symbol} ({tf})

💰 Price: {round(price,2)}
📊 RSI: {round(rsi,1)}
🎯 POC: {round(poc,2)} ({tp1_pct:.1f}%)
🎯 HVN: {round(hvn,2)} ({tp2_pct:.1f}%)
🎯 LVN: {round(lvn,2)} ({tp3_pct:.1f}%)

🛑 SL: {round(sl,2)} ({sl_pct:.1f}%)
-------------------------
"""
    return msg


# =========================
# RUN BOT
# =========================
def run_bot():
    results = []

    for s in stocks:
        for tf in ["15m", "60m"]:
            try:
                r = analyze(s, tf)
                if r:
                    results.append(r)
            except:
                pass

    if results:
        send("🔥 Trading Signals\n\n" + "\n".join(results))
    else:
        send("No signals")


# =========================
# STATUS SYSTEM (/status)
# =========================
def check_messages():
    last_update_id = None

    while True:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        res = requests.get(url).json()

        if "result" in res:
            for update in res["result"]:

                update_id = update["update_id"]

                if last_update_id is None or update_id > last_update_id:
                    last_update_id = update_id

                    if "message" in update:
                        text = update["message"].get("text","")

                        if text == "/status":
                            send("🟢 البوت شغال + السوق الأمريكي تحت المراقبة")

        time.sleep(3)


# =========================
# START THREAD
# =========================
threading.Thread(target=check_messages, daemon=True).start()


# =========================
# MAIN LOOP (WITH MARKET FILTER)
# =========================
while True:

    if market_open():
        run_bot()
        time.sleep(3600)
    else:
        print("Market closed - waiting...")
        time.sleep(600)
