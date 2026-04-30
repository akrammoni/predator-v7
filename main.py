import requests
import time
import os
import threading
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "-1003878364200"

prices = []
position = None
entry_price = 0
last_good_price = None

# === TELEGRAM ===
def send(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

# === GET PRICE (BINANCE + FALLBACK) ===
def get_price():
    global last_good_price

    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
            timeout=10
        ).json()

        if "price" in r:
            price = float(r["price"])
            last_good_price = price
            return price

    except:
        pass

    # fallback
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=10
        ).json()

        price = r["bitcoin"]["usd"]
        last_good_price = price
        return price

    except:
        return last_good_price

# === BOT LOOP ===
def run_bot():
    global position, entry_price

    last_heartbeat = 0
    send("🚀 Bot A LIVE")

    while True:
        price = get_price()

        if price:
            prices.append(price)
            if len(prices) > 6:
                prices.pop(0)

        # HEARTBEAT
        if time.time() - last_heartbeat > 60:
            if price:
                send(f"⏱ BTC: {price:,.2f}")
            else:
                send("⏱ Alive (no data)")
            last_heartbeat = time.time()

        if len(prices) < 6:
            time.sleep(12)
            continue

        c1 = (prices[-1] - prices[-2]) / prices[-2]

        # BUY
        if position is None and c1 > 0.001:
            position = "LONG"
            entry_price = price
            send(f"🟢 BUY {price:,.2f}")

        # SELL
        elif position == "LONG":
            pnl = price - entry_price

            if pnl > 40 or pnl < -25:
                send(f"🔴 SELL {price:,.2f} | PnL {pnl:.2f}")
                position = None

        time.sleep(12)

# === SERVER ===
@app.route("/")
def home():
    return "Bot A running", 200

threading.Thread(target=run_bot, daemon=True).start()
