# config.py
import os

# Telegram
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Coins to monitor
COINS = [c.strip().replace('"', '').replace("'", '') for c in os.getenv(
    "COINS", "SOLUSDT,ETHUSDT,BTCUSDT,XRPUSDT,DOGEUSDT").split(",")]

# Timeframes
LTF_INTERVAL = os.getenv("LTF_INTERVAL", "15m")
HTF_INTERVAL = os.getenv("HTF_INTERVAL", "1h")

# Strategy params
EMA_FAST = int(os.getenv("EMA_FAST") or 9)
EMA_SLOW = int(os.getenv("EMA_SLOW") or 15)
ADX_LEN = int(os.getenv("ADX_LEN") or 14)
# relaxed defaults for data collection
ADX_THRESHOLD = float(os.getenv("ADX_THRESHOLD") or 0.0)
HTF_FACTOR = float(os.getenv("HTF_FACTOR") or 0.1)

# Risk / journal
RISK_USD = float(os.getenv("RISK_USD") or 1.0)
RR_RATIO = float(os.getenv("RR_RATIO") or 2.5)
LOOKBACK_SL = int(os.getenv("LOOKBACK_SL") or 10)

# Operation
# run frequency is controlled in GitHub Actions; runtime limit for single run:
try:
    RUNTIME_LIMIT_MINUTES = int(os.getenv("RUNTIME_LIMIT_MINUTES") or 2)  # minutes
except Exception:
    RUNTIME_LIMIT_MINUTES = 2

JOURNAL_FILE = os.getenv("JOURNAL_FILE") or "signals_journal.csv"
LOG_FILE = os.getenv("LOG_FILE") or "bot_errors.log"

# Google Sheets
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# HTTP / timeout
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT") or 10)

# API / candle limits (safeguards)
try:
    API_CALL_LIMIT = int(os.getenv("API_CALL_LIMIT") or 200)   # total Binance calls per run
except Exception:
    API_CALL_LIMIT = 200
try:
    CANDLE_LIMIT = int(os.getenv("CANDLE_LIMIT") or 300)      # max candles per request
except Exception:
    CANDLE_LIMIT = 300

# Data collection mode: True -> Google Sheets only (no CSV/Telegram)
COLLECTION_MODE = (os.getenv("COLLECTION_MODE") or "True").lower() in ("1", "true", "yes")

# Local small cache for previous signals
LAST_SIGNALS_FILE = os.getenv("LAST_SIGNALS_FILE") or "last_signals.csv"


