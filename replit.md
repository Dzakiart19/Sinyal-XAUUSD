# XAUUSD Scalping Signal Bot

## Overview

A Telegram bot that provides real-time XAUUSD (Gold) trading signals using a scalping strategy. The bot operates 24/7, connecting to Deriv's WebSocket API for live price data and generating BUY/SELL signals based on technical analysis (EMA 50, RSI 3, ADX 55 + Market Regime Filter). Signals are automatically broadcast to active Telegram users with position tracking, profit/loss calculations, and trading statistics.

## How to Run

```
python main.py
```

Requires `TELEGRAM_BOT_TOKEN` secret to be set (via Replit Secrets).

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Components

**Entry Point** (`main.py`)
- Async bot runner with graceful shutdown handling (SIGINT/SIGTERM)
- Initializes all components and manages lifecycle
- Fail-fast if `TELEGRAM_BOT_TOKEN` not set

**WebSocket Client** (`src/websocket_client.py`)
- Maintains persistent connection to Deriv WebSocket API (`wss://ws.derivws.com`)
- Streams real-time tick data and OHLC candles for M1 and M5 timeframes
- Auto-reconnect on ALL exceptions (not just ConnectionClosed)
- Maintains 100-candle history buffer per timeframe
- Startup timeout: 120 seconds

**Technical Indicators** (`src/indicators.py`)
- EMA 50 — trend direction
- RSI 3 — momentum entry/exit (Cutler variant using SMA of gains/losses)
- ADX 55 — trend strength filter (Wilder's smoothing), threshold > 65
- ATR 14 — dynamic TP/SL sizing (SMA variant)
- Market Regime Filter — ADX(20) vs ADX(60) comparison to detect trending vs ranging

**Signal Generator** (`src/signal_generator.py`)
- Scans M1 and M5 every 1 second
- BUY: price > EMA50, RSI(3) crossover ↑ from < 20, ADX > 65, regime trending
- SELL: price < EMA50, RSI(3) crossover ↓ from > 80, ADX > 65, regime trending
- Filters: NO_TREND, RANGING, NO_SIGNAL all blocked
- Anti-duplication via `processed_candles` set (capped 500)

**Telegram Bot** (`src/telegram_bot.py`)
- Built with python-telegram-bot 20.7 (async, polling mode)
- Commands: /start, /dashboard, /stats, /getsignal, /info, /riset, /help, /stop
- Live dashboard with 5-second auto-updates
- Broadcasts signals to all active users
- HTTP server on port 8080 (/health, /cron/tick)

**Position Tracker** (`src/position_tracker.py`)
- Monitors open positions every 5 seconds via latest tick price
- Dynamic TP/SL based on ATR × multipliers (TP = ATR×3.0, SL = ATR×1.0), clamped $1–$10
- Risk:Reward = 1:3
- WIN/LOSS result notifications via Telegram
- Atomic JSON persistence (temp + rename)
- Restores active positions on bot restart

**User Manager** (`src/user_manager.py`)
- Per-user state isolation and preferences
- Rate limiting for /getsignal: max 1 per minute
- Inactivity cleanup: marked inactive after 7 days
- Atomic JSON persistence

**Statistics Manager** (`src/statistics.py`)
- Trade recording (result, PnL, timeframe, manual/auto)
- Winrate and PnL calculations per user
- Up to 1000 trades per user retained
- Atomic JSON persistence

### Data Flow

1. Deriv WebSocket → tick + OHLC candles (M1 & M5)
2. `calculate_all_indicators()` — EMA, RSI, ADX, ATR, Market Regime
3. `_scan_timeframe()` — every 1s, filter NO_TREND/RANGING/NO_SIGNAL
4. `check_buy/sell_signal()` — strict crossover + ADX > 65 conditions
5. Valid signal → broadcast to all active users → `create_position()`
6. `_tracking_loop()` — every 5s, check tick price vs TP/SL
7. `_close_position()` → `record_trade()` → Telegram result notification

### Strategy Parameters (optimized)

| Parameter | Value |
|---|---|
| EMA period | 50 |
| RSI period | 3 |
| ADX period | 55 |
| ADX threshold | > 65 (strong trend only) |
| ATR period | 14 |
| TP multiplier | ATR × 3.0 |
| SL multiplier | ATR × 1.0 |
| TP/SL min | $1.00 |
| TP/SL max | $10.00 |
| Risk:Reward | 1:3 |
| Regime ADX short | 20 |
| Regime ADX long | 60 |

### Configuration

All settings via environment variables and `config/config.py`. Defaults are production-ready.

### Data Storage

JSON files in `data/` directory (atomic writes via temp+rename):
- `positions.json` — active and closed positions
- `statistics.json` — trade history and metrics
- `users.json` — user states and preferences

Logs: `logs/bot.log`

## Deployment

- **Type:** Autoscale (free tier compatible)
- **Run:** `python main.py`
- **Port:** 8080 (health check at `/health`, cron trigger at `/cron/tick`)
- **Keep-alive:** Ping `https://<your-app>.replit.app/health` setiap 5 menit via cron job eksternal (cron-job.org / UptimeRobot / dll) supaya instance tidak sleep

## External Dependencies

### APIs

- **Deriv WebSocket** — `wss://ws.derivws.com/websockets/v3?app_id=1089` — no auth required for public data
- **Telegram Bot API** — requires `TELEGRAM_BOT_TOKEN` from @BotFather

### Environment Variables Required

```
TELEGRAM_BOT_TOKEN=<bot token from @BotFather>   # REQUIRED — set via Replit Secrets
ADMIN_USER_ID=<your telegram user ID>             # optional
```

Optional overrides for all indicator periods, ATR multipliers, and intervals via env var (see `config/config.py`).

### Python Dependencies

```
python-telegram-bot==20.7
websockets==11.0
numpy>=2.0.0
pandas>=2.0.0
python-dotenv>=1.0.0
aiohttp>=3.9.0
```
