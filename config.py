# config.py
import os

def _int_env(name, default):
    try:
        v = os.getenv(name, "")
        return int(v) if v != "" else default
    except Exception:
        return default

def _float_env(name, default):
    try:
        v = os.getenv(name, "")
        return float(v) if v != "" else default
    except Exception:
        return default

# Telegram
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Symbols (comma-separated)
COINS = [c.strip().replace('"', '').replace("'", '') for c in os.getenv("COINS", "SOLUSDT,ETHUSDT,BTCUSDT,XRPUSDT,DOGEUSDT").split(",")]

# Timeframes
LTF_INTERVAL = os.getenv("LTF_INTERVAL", "15m")
HTF_INTERVAL = os.getenv("HTF_INTERVAL", "1h")

# Strategy parameters
EMA_FAST = _int_env("EMA_FAST", 9)
EMA_SLOW = _int_env("EMA_SLOW", 15)
ADX_LEN = _int_env("ADX_LEN", 14)
ADX_THRESHOLD = _float_env("ADX_THRESHOLD", 0.0)   # relaxed for collection
HTF_FACTOR = _float_env("HTF_FACTOR", 0.1)         # relaxed for collection

# Limits & runtime
API_CALL_LIMIT = _int_env("API_CALL_LIMIT", 200)   # total Binance calls per run
CANDLE_LIMIT = _int_env("CANDLE_LIMIT", 300)      # max candles per request
SHEET_READ_LIMIT = _int_env("SHEET_READ_LIMIT", 50)   # safe reads per run (conservative)
SHEET_WRITE_LIMIT = _int_env("SHEET_WRITE_LIMIT", 50) # safe writes per run (conservative)
RUNTIME_LIMIT_MINUTES = _int_env("RUNTIME_LIMIT_MINUTES", 5)  # 5 minutes safe-run initially

# Operation
CHECK_INTERVAL = _int_env("CHECK_INTERVAL", 720)   # not used inside GH actions run
JOURNAL_FILE = os.getenv("JOURNAL_FILE", "signals_journal.csv")
LOG_FILE = os.getenv("LOG_FILE", "bot_errors.log")

# Google Sheets
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# HTTP / timeout
REQUEST_TIMEOUT = _int_env("REQUEST_TIMEOUT", 10)

# Data collection mode: True -> only Sheets (no CSV/Telegram)
COLLECTION_MODE = os.getenv("COLLECTION_MODE", "True").lower() in ("1", "true", "yes")

# Local small cache for previous signals
LAST_SIGNALS_FILE = os.getenv("LAST_SIGNALS_FILE", "last_signals.csv")

# State file to resume runs safely
STATE_FILE = os.getenv("STATE_FILE", "run_state.json")


