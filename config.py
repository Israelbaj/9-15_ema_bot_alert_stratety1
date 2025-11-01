# config.py
import os

# Telegram
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Coins to monitor (comma separated env var)
COINS = [c.strip().replace('"', '').replace("'", '') for c in os.getenv("COINS", "SOLUSDT,ETHUSDT,BTCUSDT,XRPUSDT,DOGEUSDT").split(",")]

# Timeframes
LTF_INTERVAL = os.getenv("LTF_INTERVAL", "15m")
HTF_INTERVAL = os.getenv("HTF_INTERVAL", "1h")

# Strategy params
EMA_FAST = int(os.getenv("EMA_FAST", 9))
EMA_SLOW = int(os.getenv("EMA_SLOW", 15))
ADX_LEN = int(os.getenv("ADX_LEN", 14))
ADX_THRESHOLD = float(os.getenv("ADX_THRESHOLD", 0))   # relaxed for collection
HTF_FACTOR = float(os.getenv("HTF_FACTOR", 0.1))       # relaxed for collection

# Operation
# Run every n seconds (not used by GitHub schedule, but available)
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 14400))  # 4 hours default for local/testing

# Limits and runtime
API_CALL_LIMIT = int(os.getenv("API_CALL_LIMIT", "200"))     # Binance calls per run (default 200)
CANDLE_LIMIT = int(os.getenv("CANDLE_LIMIT", "300"))        # max candles per fetch
RUNTIME_LIMIT_MINUTES = float(os.getenv("RUNTIME_LIMIT_MINUTES", "5"))  # allow 5 minutes for first run

# Files & logging
JOURNAL_FILE = os.getenv("JOURNAL_FILE", "signals_journal.csv")
LOG_FILE = os.getenv("LOG_FILE", "error.log")
LAST_SIGNALS_FILE = os.getenv("LAST_SIGNALS_FILE", "last_signals.csv")
STATE_FILE = os.getenv("STATE_FILE", "state.json")

# Google Sheets
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

# HTTP / timeout
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 10))

# Collection mode: only Google Sheets (True), else enable CSV & Telegram
COLLECTION_MODE = os.getenv("COLLECTION_MODE", "True").lower() in ("1", "true", "yes")



