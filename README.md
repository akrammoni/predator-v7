# Predator v7 🎯📈

`predator-v7` is a lightweight, asynchronous Bitcoin (BTC) algorithmic trading alert bot. It continuously streams real-time price feeds, tracks momentum fluctuations using a custom rolling price window, and broadcasts precise entry and exit signals directly to a designated Telegram channel.

**Designed and developed by Akram Moni.**

## ⚡ Features
- **Dual-Source Price Aggregation:** Pulls ultra-fast spot prices from the Binance API, with an automatic failover fallback to the CoinGecko API to ensure zero downtime.
- **Momentum-Based Signaling:** Tracks a strict rolling matrix of recent price updates to instantly detect sharp upward volatility (`> 0.1%`) for `BUY` triggers.
- **Automated Risk Controls:** Built-in hard Take-Profit (+$40) and Stop-Loss (-$25) parameters to automatically manage simulated position risk.
- **Live Diagnostics (Heartbeat):** Dispatches minute-by-minute heartbeat logs directly to Telegram containing active asset pricing or connection sanity checks.
- **Always-On Web Server:** Embedded with a background Flask daemon thread to keep the script running indefinitely on cloud environments like Render, Koyeb, or Heroku.

## 🛠️ Technology Stack
- **Language:** Python 3.10+
- **Framework:** Flask (for web server keep-alives)
- **APIs Used:** Binance API, CoinGecko API, Telegram Bot API
- **Concurrency:** Native Python `threading` 

## ⚙️ Deployment & Setup

### 1. Environment Variables
To securely run this engine, you must inject your credentials into your hosting provider's environment variables or use a local `.env` file:

```env
BOT_TOKEN="your_telegram_bot_token_here"
