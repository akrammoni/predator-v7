import time
import threading
import requests
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

# ========= CONFIG =========
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = "-1003878364200"

SLEEP_TIME = 10

# ========= STATE =========
price_history = []
last_heartbeat = 0

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
        print("❌ BOT_TOKEN is None", flush=True)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        r = requests.post(url, json={
            "chat_id": CHANNEL_ID,
            "text": msg
        })
        print("📨", msg, flush=True)
        print("Telegram:", r.text, flush=True)
    except Exception as e:
        print("❌ Telegram error:", e, flush=True)

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
        print("❌ Price error:", e, flush=True)
        return None

# ========= BOT =========
def bot():
    global last_heartbeat

    print("🤖 BOT STARTED", flush=True)
    send("🚀 Predator V7 Live")

    while True:
        try:
            price = get_price()

            if price:
                print(f"💰 Price: {price}", flush=True)

                # HEARTBEAT every 60s
                if time.time() - last_heartbeat > 60:
                    send(f"⏱ Alive | BTC: {price:,.2f}")
                    last_heartbeat = time.time()

        except Exception as e:
            print("❌ Bot error:", e, flush=True)

        time.sleep(SLEEP_TIME)

# ========= START =========
if __name__ == "__main__":
    print("🚀 STARTING APP...", flush=True)

    threading.Thread(target=bot, daemon=True).start()

    run_server()
