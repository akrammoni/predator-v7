import time
import threading
import requests
import os
import csv
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

balance = 100
max_balance = 100
max_drawdown = 0

price_history = []
last_heartbeat = 0
last_report = 0

# ========= FILE =========
if not os.path.exists("trades.csv"):
    with open("trades.csv", "w", newline="") as f:
        csv.writer(f).writerow([
            "time","type","entry","exit","pnl%","balance","drawdown"
        ])

# ========= SERVER =========
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"running")

def run_server():
    print("🌐 SERVER STARTED", flush=True)
    HTTPServer(("0.0.0.0", 7860), Handler).serve_forever()

# ========= TELEGRAM =========
def send(msg):
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN missing", flush=True)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHANNEL_ID, "text": msg})

def send_file():
    if not BOT_TOKEN:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"

    try:
        with open("trades.csv", "rb") as f:
            requests.post(url, data={"chat_id": CHANNEL_ID}, files={"document": f})
        print("📤 Sent CSV to Telegram", flush=True)
    except Exception as e:
        print("❌ File send error:", e, flush=True)

# ========= PRICE =========
def get_price():
    try:
        c = requests.get("https://api.coinbase.com/v2/prices/spot?currency=USD", timeout=10)
        k = requests.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD", timeout=10)

        c_price = float(c.json()["data"]["amount"])
        pair = list(k.json()["result"].keys())[0]
        k_price = float(k.json()["result"][pair]["c"][0])

        return (c_price + k_price) / 2
    except:
        return None

# ========= LOG =========
def log_trade(entry, exit_p, pnl):
    global balance, max_balance, max_drawdown

    balance *= (1 + pnl / 100)

    if balance > max_balance:
        max_balance = balance

    dd = (balance - max_balance) / max_balance * 100

    if dd < max_drawdown:
        max_drawdown = dd

    with open("trades.csv", "a", newline="") as f:
        csv.writer(f).writerow([
            time.strftime("%Y-%m-%d %H:%M:%S"),
            "LONG",
            round(entry, 2),
            round(exit_p, 2),
            round(pnl, 4),
            round(balance, 2),
            round(max_drawdown, 2)
        ])

    return dd

# ========= BOT =========
def bot():
    global position, entry_price, entry_time, peak_pnl
    global total_pnl, trades, wins, last_trade_time
    global last_heartbeat, last_report

    print("🤖 BOT STARTED", flush=True)
    send("🚀 Predator V7 Live (logging enabled)")

    while True:
        try:
            price = get_price()

            if not price:
                time.sleep(SLEEP_TIME)
                continue

            print(f"💰 {price}", flush=True)

            price_history.append(price)
            if len(price_history) > 5:
                price_history.pop(0)

            # ===== HEARTBEAT =====
            if time.time() - last_heartbeat > 60:
                send(f"⏱ Alive | BTC: {price:,.2f}")
                last_heartbeat = time.time()

            # ===== DAILY REPORT =====
            if time.time() - last_report > 86400:  # 24 hours
                winrate = (wins / trades * 100) if trades > 0 else 0

                send(
                    f"📊 DAILY REPORT\n"
                    f"Trades: {trades}\n"
                    f"Winrate: {winrate:.1f}%\n"
                    f"Balance: {balance:.2f}\n"
                    f"Drawdown: {max_drawdown:.2f}%"
                )

                send_file()
                last_report = time.time()

            if len(price_history) == 5:
                p1, p2, p3, p4, p5 = price_history

                trend_up = p5 > p1
                move = (p5 - p1) / p1 * 100
                jump = (p5 - p4) / p4 * 100

                # ===== ENTRY =====
                if (
                    position is None and
                    time.time() - last_trade_time > COOLDOWN and
                    trend_up and
                    move > 0.02 and
                    jump < 0.05
                ):
                    position = "LONG"
                    entry_price = price
                    entry_time = time.time()
                    peak_pnl = 0
                    trades += 1

                    send(f"🟢 BUY @ {price:,.2f}")

                # ===== EXIT =====
                elif position == "LONG":
                    pnl = (price - entry_price) / entry_price * 100
                    hold = time.time() - entry_time

                    if pnl > peak_pnl:
                        peak_pnl = pnl

                    trailing = (
                        peak_pnl >= TRAIL_START and
                        pnl <= peak_pnl - TRAIL_DROP
                    )

                    if pnl <= STOP_LOSS or hold > MAX_HOLD or trailing:
                        total_pnl += pnl
                        last_trade_time = time.time()

                        if pnl > 0:
                            wins += 1

                        dd = log_trade(entry_price, price, pnl)

                        winrate = (wins / trades) * 100

                        send(
                            f"🔴 SELL\n"
                            f"PnL: {pnl:.2f}%\n"
                            f"Balance: {balance:.2f}\n"
                            f"Winrate: {winrate:.1f}%\n"
                            f"DD: {dd:.2f}%"
                        )

                        position = None

        except Exception as e:
            print("❌ Error:", e, flush=True)

        time.sleep(SLEEP_TIME)

# ========= START =========
if __name__ == "__main__":
    print("🚀 STARTING APP...", flush=True)
    threading.Thread(target=bot, daemon=True).start()
    run_server()
