# XAUUSD Scalping Signal Bot

## Overview

A Telegram bot that provides real-time XAUUSD (Gold) trading signals using a scalping strategy. The bot operates 24/7, connecting to Deriv's WebSocket API for live price data and generating BUY/SELL signals based on technical analysis (EMA 50, RSI 3, ADX 55). Signals are automatically broadcast to active Telegram users with position tracking, profit/loss calculations, and trading statistics.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Components

**Entry Point** (`main.py`)
- Async bot runner with graceful shutdown handling
- Initializes all components and manages lifecycle

**WebSocket Client** (`src/websocket_client.py`)
- Maintains persistent connection to Deriv WebSocket API (`wss://ws.derivws.com`)
- Streams real-time tick data and OHLC candles for M1 and M5 timeframes
- Auto-reconnect functionality for 24/7 operation
- Maintains 100-candle history buffer per timeframe

**Technical Indicators** (`src/indicators.py`)
- EMA 50 calculation for trend direction
- RSI 3 for momentum entry/exit detection
- ADX 55 for trend strength filtering (signals only when ADX > 30)
- Uses NumPy and Pandas for calculations

**Signal Generator** (`src/signal_generator.py`)
- Scans both M1 and M5 timeframes continuously
- Implements buy logic: price above EMA 50, RSI exiting oversold, ADX > 30
- Implements sell logic: price below EMA 50, RSI exiting overbought, ADX > 30
- Anti-duplication system to prevent repeated signals
- Callback system for signal distribution

**Telegram Bot** (`src/telegram_bot.py`)
- Built with python-telegram-bot library (async)
- Commands: /start, /dashboard, /stats, /getsignal, etc.
- Live dashboard with 5-second auto-updates
- Broadcasts signals to all active users
- Per-user manual signal requests

**Position Tracker** (`src/position_tracker.py`)
- Monitors open positions every 5 seconds
- Automatic TP/SL detection ($3 each, 1:1 risk-reward)
- Real-time PnL calculation
- WIN/LOSS result notifications
- JSON persistence for positions

**User Manager** (`src/user_manager.py`)
- Per-user state isolation
- Activity tracking and preferences
- JSON persistence for user data

**Statistics Manager** (`src/statistics.py`)
- Trade recording and history
- Winrate and PnL calculations
- JSON persistence for statistics

### Data Flow

1. WebSocket receives ticks and candles from Deriv
2. Indicators calculate EMA/RSI/ADX on updated candle data
3. Signal Generator evaluates conditions each second
4. Valid signals trigger callbacks to Telegram Bot
5. Bot broadcasts to active users and creates positions
6. Position Tracker monitors until TP/SL hit
7. Statistics Manager records completed trades

### Configuration

All settings managed via environment variables and `config/config.py`:
- Telegram bot token and admin ID
- Deriv WebSocket URL and symbol (frxXAUUSD)
- Indicator periods (EMA 50, RSI 3, ADX 55)
- TP/SL values, update intervals
- File paths for data and logs

### Data Storage

JSON files in `data/` directory:
- `positions.json` - Active and closed positions
- `statistics.json` - Trade history and metrics
- `users.json` - User states and preferences

Logs written to `logs/bot.log`.

## External Dependencies

### APIs and Services

**Deriv WebSocket API**
- URL: `wss://ws.derivws.com/websockets/v3?app_id=1089`
- Purpose: Real-time XAUUSD price data (ticks and OHLC candles)
- No authentication required for public data

**Telegram Bot API**
- Requires bot token from @BotFather
- Used for all user interaction, signal delivery, and dashboards

### Python Dependencies

- `python-telegram-bot==20.7` - Telegram bot framework (async)
- `websockets==11.0` - WebSocket client for Deriv connection
- `numpy==1.24.3` - Numerical calculations for indicators
- `pandas==2.0.3` - Data manipulation for EMA/RSI calculations
- `python-dotenv==1.0.0` - Environment variable loading
- `aiofiles==23.2.0` - Async file operations

### Environment Variables Required

```
TELEGRAM_BOT_TOKEN=<your-bot-token>
ADMIN_USER_ID=<your-telegram-user-id>
```

Optional overrides available for indicator periods, TP/SL values, and intervals.