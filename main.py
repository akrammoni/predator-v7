import time
import threading
import requests
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# ========= CONFIG =========
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "-1003878364200"

SLEEP_TIME = 10
COOLDOWN = 60

STOP_LOSS = -0.05
MAX_HOLD = 180
TRAIL_START = 0.03
TRAIL_DROP = 0.02

# ========= STATE =========
position = None
entry_price = 0
entry_time = 0
peak_pnl = 0
last_trade_time = 0

total_pnl = 0
trades = 0
wins = 0

price_history = []
last_heartbeat = 0

# ========= SERVER =========
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"running")

def run_server():
    HTTPServer(("0.0.0.0", 7860), Handler).serve_forever()

# ========= TELEGRAM =========
def send(msg):
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN is None")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        r = requests.post(url, json={
            "chat_id": CHANNEL_ID,
            "text": msg
        })
        print("📨", msg)
        print("Telegram:", r.text)
    except Exception as e:
        print("❌ Telegram error:", e)

def fmt(p):
    return f"{p:,.2f}"

# ========= PRICE =========
def get_price():
    try:
        c = requests.get(
            "https://api.coinbase.com/v2/prices/spot?currency=USD",
            timeout=10
        )
        k = requests.get(
            "https://api.kraken.com/0/public/Ticker?pair=XBTUSD",
            timeout=10
        )

        c_price = float(c.json()["data"]["amount"])
        pair = list(k.json()["result"].keys())[0]
        k_price = float(k.json()["result"][pair]["c"][0])

        return (c_price + k_price) / 2
    except Exception as e:
        print("❌ Price error:", e)
        return None

# ========= BOT =========
def bot():
    global position, entry_price, entry_time, peak_pnl
    global total_pnl, trades, wins, price_history, last_trade_time, last_heartbeat

    print("🤖 BOT STARTED")
    send("🚀 Predator V7 Live\n⚠️ Experimental system")

    while True:
        try:
            price = get_price()

            if not price:
                time.sleep(SLEEP_TIME)
                continue

            price_history.append(price)
            if len(price_history) > 10:
                price_history.pop(0)

            # ===== HEARTBEAT (every 60s) =====
            if time.time() - last_heartbeat > 60:
                send(f"⏱ Alive | BTC: {fmt(price)}")
                last_heartbeat = time.time()

            if len(price_history) >= 5:
                p1 = price_history[0]
                p5 = price_history[-1]
                p4 = price_history[-2]

                # ===== TREND =====
                trend_up = p5 > p1
                move = (p5 - p1) / p1 * 100
                recent_jump = (p5 - p4) / p4 * 100

                # ===== VOLATILITY =====
                volatility = max(price_history) - min(price_history)
                vol_pct = (volatility / p1) * 100

                # ===== ENTRY =====
                if (
                    position is None and
                    time.time() - last_trade_time > COOLDOWN and
                    trend_up and
                    move > 0.02 and
                    recent_jump < 0.05
                ):
                    position = "LONG"
                    entry_price = price
                    entry_time = time.time()
                    peak_pnl = 0
                    trades += 1

                    send(
                        f"🟢 BUY\n"
                        f"Price: {fmt(price)}\n"
                        f"Trend: UP\n"
                        f"Volatility: {vol_pct:.2f}%"
                    )

                # ===== EXIT =====
                elif position == "LONG":
                    pnl = (price - entry_price) / entry_price * 100
                    hold_time = time.time() - entry_time

                    if pnl > peak_pnl:
                        peak_pnl = pnl

                    trailing_hit = (
                        peak_pnl >= TRAIL_START and
                        pnl <= peak_pnl - TRAIL_DROP
                    )

                    if pnl <= STOP_LOSS or hold_time > MAX_HOLD or trailing_hit:
                        total_pnl += pnl
                        last_trade_time = time.time()

                        if pnl > 0:
                            wins += 1

                        winrate = (wins / trades) * 100 if trades > 0 else 0

                        send(
                            f"🔴 SELL\n"
                            f"Exit: {fmt(price)}\n"
                            f"PnL: {pnl:.2f}%\n\n"
                            f"📊 Stats\n"
                            f"Trades: {trades}\n"
                            f"Win Rate: {winrate:.1f}%\n"
                            f"Total: {total_pnl:.2f}%"
                        )

                        position = None

        except Exception as e:
            print("❌ Error:", e)

        time.sleep(SLEEP_TIME)

# ========= START =========
threading.Thread(target=bot, daemon=True).start()
run_server()
