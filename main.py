import requests
import time
import os
import csv
from datetime import datetime
import threading
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = "-1003878364200"

prices = []
position = None
entry_price = 0

# === TELEGRAM SEND ===
def send(msg):
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN missing")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}

    try:
        r = requests.post(url, data=data, timeout=10)
        print("📨", msg)
        print("Telegram:", r.text)
    except Exception as e:
        print("Telegram Error:", e)

# === GET PRICE (SAFE) ===
def get_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    try:
        r = requests.get(url, timeout=10).json()

        if "price" not in r:
            print("⚠️ Bad API response:", r)
            return None

        return float(r["price"])

    except Exception as e:
        print("⚠️ Price fetch error:", e)
        return None

# === SAVE TRADE ===
def log_trade(side, entry, exit_price, pnl):
    with open("trades.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            side,
            entry,
            exit_price,
            pnl
        ])

# === MAIN BOT LOOP ===
def run_bot():
    global position, entry_price

    last_heartbeat = 0
    print("🤖 BOT LOOP STARTED")
    send("🚀 Predator V7 Live")

    while True:
        try:
            price = get_price()
            print("DEBUG price:", price)

            # 🔥 HEARTBEAT ALWAYS RUNS
            if time.time() - last_heartbeat > 60:
                if price is not None:
                    send(f"⏱ Alive | BTC: {price:,.2f}")
                else:
                    send("⏱ Alive (price unavailable)")
                last_heartbeat = time.time()

            # skip logic if no price
            if price is None:
                time.sleep(5)
                continue

            print(f"💰 Price: {price:,.2f}")

            prices.append(price)
            if len(prices) > 6:
                prices.pop(0)

            if len(prices) < 6:
                time.sleep(5)
                continue

            # === PRICE CHANGES (RELAXED FOR TESTING) ===
            change_1 = (prices[-1] - prices[-2]) / prices[-2]
            change_3 = (prices[-1] - prices[-4]) / prices[-4]
            change_5 = (prices[-1] - prices[0]) / prices[0]

            print(f"Δ1: {change_1:.4f}, Δ3: {change_3:.4f}, Δ5: {change_5:.4f}")

            strong_move = change_1 > 0.0015
            building_trend = change_3 > 0.0025
            overall_trend = change_5 > 0.004

            # === BUY ===
            if position is None:
                if strong_move and building_trend and overall_trend:
                    position = "LONG"
                    entry_price = price
                    send(f"🟢 BUY (TREND)\nEntry: {price:,.2f}")

                elif change_1 > 0.001:
                    position = "LONG"
                    entry_price = price
                    send(f"🟡 BUY (SCALP)\nEntry: {price:,.2f}")

            # === SELL ===
            elif position == "LONG":
                pnl = price - entry_price

                if pnl > 40 or pnl < -25:
                    send(f"🔴 SELL\nExit: {price:,.2f}\nPnL: {pnl:.2f}")
                    log_trade("LONG", entry_price, price, pnl)
                    position = None

            time.sleep(5)

        except Exception as e:
            print("ERROR:", e)
            time.sleep(5)

# === HEALTH CHECK ===
@app.route("/")
def home():
    return "✅ Bot A is running", 200

# === START THREAD ===
def start_bot():
    t = threading.Thread(target=run_bot)
    t.daemon = True
    t.start()

start_bot()
