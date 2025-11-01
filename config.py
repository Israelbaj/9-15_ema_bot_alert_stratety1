# config.py
import os

# Telegram (keep these env names)
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Coins to monitor
COINS = [
    c.strip().replace('"', '').replace("'", '')
    for c in os.getenv("COINS", "SOLUSDT,ETHUSDT,BTCUSDT,XRPUSDT,DOGEUSDT").split(",")
]

# Timeframes
LTF_INTERVAL = os.getenv("LTF_INTERVAL", "15m")
HTF_INTERVAL = os.getenv("HTF_INTERVAL", "1h")

# Strategy parameters
EMA_FAST = int(os.getenv("EMA_FAST") or 9)
EMA_SLOW = int(os.getenv("EMA_SLOW") or 15)
ADX_LEN = int(os.getenv("ADX_LEN") or 14)
ADX_THRESHOLD = float(os.getenv("ADX_THRESHOLD") or 0.0)
HTF_FACTOR = float(os.getenv("HTF_FACTOR") or 0.1)

# Risk / journal settings
RISK_USD = float(os.getenv("RISK_USD") or 1.0)
RR_RATIO = float(os.getenv("RR_RATIO") or 2.5)
LOOKBACK_SL = int(os.getenv("LOOKBACK_SL") or 10)

# Operation intervals
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL") or 14400)  # 4 hours = 14400s
JOURNAL_FILE = os.getenv("JOURNAL_FILE", "signals_journal.csv")
LOG_FILE = os.getenv("LOG_FILE", "bot_errors.log")

# Google Sheets
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# HTTP / timeout
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT") or 10)

# API limits & candles
API_CALL_LIMIT = int(os.getenv("API_CALL_LIMIT") or 200)  # total Binance calls per run
CANDLE_LIMIT = int(os.getenv("CANDLE_LIMIT") or 300)      # max candles request
# Runtime limit for GitHub Actions
RUNTIME_LIMIT_MINUTES = int(os.getenv("RUNTIME_LIMIT_MINUTES") or 2) 
# Data collection mode
COLLECTION_MODE = True  # True = disable Telegram/CSV and only log to Sheets

# Cache for previous signals
LAST_SIGNALS_FILE = os.getenv("LAST_SIGNALS_FILE", "last_signals.json")
