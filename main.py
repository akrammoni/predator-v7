import os
import time
import threading
import logging
import requests

from flask import Flask


# =========================
# CONFIGURATION
# =========================

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

BINANCE_URL = (
    "https://api.binance.com/api/v3/ticker/price"
    "?symbol=BTCUSDT"
)

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin&vs_currencies=usd"
)


# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# =========================
# BOT STATE
# =========================

prices = []

position = None
entry_price = 0

last_good_price = None


# =========================
# TELEGRAM SERVICE
# =========================

def send_message(message):

    if not BOT_TOKEN or not CHAT_ID:
        logging.warning(
            "Telegram credentials missing"
        )
        return

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    try:
        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=10
        )

        response.raise_for_status()

    except Exception as e:
        logging.error(
            f"Telegram error: {e}"
        )


# =========================
# PRICE SERVICE
# =========================

def get_price():

    global last_good_price


    # Binance

    try:

        response = requests.get(
            BINANCE_URL,
            timeout=10
        )

        data = response.json()

        if "price" in data:

            price = float(
                data["price"]
            )

            last_good_price = price

            return price


    except Exception as e:

        logging.warning(
            f"Binance failed: {e}"
        )


    # CoinGecko fallback

    try:

        response = requests.get(
            COINGECKO_URL,
            timeout=10
        )

        data = response.json()

        price = data["bitcoin"]["usd"]

        last_good_price = price

        return price


    except Exception as e:

        logging.warning(
            f"CoinGecko failed: {e}"
        )


    return last_good_price



# =========================
# TRADING LOGIC
# =========================

def run_bot():

    global position
    global entry_price


    last_heartbeat = 0


    send_message(
        "🚀 BTC Bot Online"
    )


    while True:


        price = get_price()


        if price:

            prices.append(price)


            if len(prices) > 6:

                prices.pop(0)



        # heartbeat every minute

        if time.time() - last_heartbeat > 60:


            if price:

                send_message(
                    f"⏱ BTC: {price:,.2f}"
                )

            else:

                send_message(
                    "⏱ Bot alive but no price"
                )


            last_heartbeat = time.time()



        if len(prices) < 6:

            time.sleep(12)

            continue



        change = (
            prices[-1] - prices[-2]
        ) / prices[-2]



        # BUY SIGNAL

        if position is None and change > 0.001:


            position = "LONG"

            entry_price = price


            send_message(
                f"🟢 BUY BTC {price:,.2f}"
            )



        # SELL SIGNAL

        elif position == "LONG":


            profit_loss = (
                price - entry_price
            )


            if (
                profit_loss > 40
                or profit_loss < -25
            ):


                send_message(
                    f"🔴 SELL BTC "
                    f"{price:,.2f} "
                    f"| PnL {profit_loss:.2f}"
                )


                position = None



        time.sleep(12)



# =========================
# FLASK HEALTH CHECK
# =========================

@app.route("/")
def home():

    return {
        "status": "running",
        "bot": "BTC Monitor"
    }, 200



# =========================
# START BOT
# =========================

if __name__ == "__main__":


    bot_thread = threading.Thread(
        target=run_bot,
        daemon=True
    )


    bot_thread.start()


    app.run(
        host="0.0.0.0",
        port=5000
    )