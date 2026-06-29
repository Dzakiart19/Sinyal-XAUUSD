import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', 'YOUR_BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_USER_ID', '123456789'))

    # Webhook / Server
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')          # e.g. https://your-app.replit.app
    WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', '')    # optional secret token
    PORT = int(os.getenv('PORT', 8080))                 # Cloud Run default port

    # Deriv WebSocket
    DERIV_WS_URL = os.getenv('DERIV_WS_URL', 'wss://ws.derivws.com/websockets/v3?app_id=1089')
    SYMBOL = 'frxXAUUSD'

    # Risk Management
    DEFAULT_TP = float(os.getenv('DEFAULT_TP', 3.0))
    DEFAULT_SL = float(os.getenv('DEFAULT_SL', 3.0))

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
