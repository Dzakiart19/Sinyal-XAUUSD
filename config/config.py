import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    # Bug #8 fix: default 0 is safe (no valid Telegram ID is 0), but guard non-numeric env var
    _admin_raw = os.getenv('ADMIN_USER_ID', '0')
    ADMIN_ID = int(_admin_raw) if _admin_raw.strip().lstrip('-').isdigit() else 0

    # Server (untuk health check & cron job)
    PORT = int(os.getenv('PORT', 8080))

    # Deriv WebSocket
    DERIV_WS_URL = os.getenv('DERIV_WS_URL', 'wss://ws.derivws.com/websockets/v3?app_id=1089')
    SYMBOL = 'frxXAUUSD'

    # Risk Management — ATR-based dynamic TP/SL
    ATR_PERIOD     = int(os.getenv('ATR_PERIOD', 14))      # periode ATR
    ATR_SL_MULT    = float(os.getenv('ATR_SL_MULT', 1.0))  # SL = ATR × 1.0  [optimized]
    ATR_TP_MULT    = float(os.getenv('ATR_TP_MULT', 3.0))  # TP = ATR × 3.0  (RR 3:1) [optimized]
    MIN_SL         = float(os.getenv('MIN_SL', 1.0))        # minimum SL $1
    MAX_SL         = float(os.getenv('MAX_SL', 10.0))       # maximum SL $10
    MIN_TP         = float(os.getenv('MIN_TP', 1.0))        # minimum TP $1
    MAX_TP         = float(os.getenv('MAX_TP', 30.0))       # maximum TP $30 (3× MAX_SL untuk R:R 1:3)

    # Technical Indicators
    EMA_PERIOD = int(os.getenv('EMA_PERIOD', 50))
    RSI_PERIOD = int(os.getenv('RSI_PERIOD', 3))
    ADX_PERIOD = int(os.getenv('ADX_PERIOD', 55))
    ADX_THRESHOLD = int(os.getenv('ADX_THRESHOLD', 65))  # [optimized dari 50→65]

    # Timeframes
    M1_CANDLE_COUNT = int(os.getenv('M1_CANDLE_COUNT', 100))
    M5_CANDLE_COUNT = int(os.getenv('M5_CANDLE_COUNT', 100))

    # Update Intervals (seconds)
    SIGNAL_CHECK_INTERVAL = int(os.getenv('SIGNAL_CHECK_INTERVAL', 1))
    DASHBOARD_UPDATE_INTERVAL = int(os.getenv('DASHBOARD_UPDATE_INTERVAL', 5))
    PRICE_TRACKING_INTERVAL = int(os.getenv('PRICE_TRACKING_INTERVAL', 5))

    # Signal Settings
    RSI_OVERSOLD = 20
    RSI_OVERBOUGHT = 80
    RSI_EXIT_OVERSOLD = 20   # [optimized dari 25→20]
    RSI_EXIT_OVERBOUGHT = 80  # [optimized dari 75→80]

    # Market Regime Filter — deteksi trending vs ranging
    # ADX M1 jangka pendek (20 candle) vs jangka panjang (60 candle)
    # Jika ADX pendek > ADX panjang → pasar sedang TRENDING → boleh masuk
    # Jika ADX pendek < ADX panjang → pasar sedang RANGING → skip sinyal
    REGIME_ADX_SHORT = int(os.getenv('REGIME_ADX_SHORT', 20))   # ADX periode pendek
    REGIME_ADX_LONG  = int(os.getenv('REGIME_ADX_LONG',  60))   # ADX periode panjang
    REGIME_MIN_SLOPE = float(os.getenv('REGIME_MIN_SLOPE', 0.0)) # slope minimum ADX (naik)

    # File paths
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')

    @classmethod
    def init_directories(cls):
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
