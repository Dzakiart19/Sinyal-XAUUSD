import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_USER_ID', '123456789'))

    # Server (untuk health check & cron job)
    PORT = int(os.getenv('PORT', 8080))

    # Deriv WebSocket
    DERIV_WS_URL = os.getenv('DERIV_WS_URL', 'wss://ws.derivws.com/websockets/v3?app_id=1089')
    SYMBOL = 'frxXAUUSD'

    # Risk Management — ATR-based dynamic TP/SL
    ATR_PERIOD     = int(os.getenv('ATR_PERIOD', 14))      # periode ATR
    ATR_SL_MULT    = float(os.getenv('ATR_SL_MULT', 1.5))  # SL = ATR × 1.5
    ATR_TP_MULT    = float(os.getenv('ATR_TP_MULT', 1.5))  # TP = ATR × 1.5 (RR 1:1)
    MIN_SL         = float(os.getenv('MIN_SL', 1.0))       # minimum SL $1
    MAX_SL         = float(os.getenv('MAX_SL', 10.0))      # maximum SL $10

    # Technical Indicators
    EMA_PERIOD = int(os.getenv('EMA_PERIOD', 50))
    RSI_PERIOD = int(os.getenv('RSI_PERIOD', 3))
    ADX_PERIOD = int(os.getenv('ADX_PERIOD', 55))
    ADX_THRESHOLD = int(os.getenv('ADX_THRESHOLD', 30))

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
    RSI_EXIT_OVERSOLD = 25
    RSI_EXIT_OVERBOUGHT = 75

    # File paths
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')

    @classmethod
    def init_directories(cls):
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
