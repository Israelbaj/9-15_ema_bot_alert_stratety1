# config.py
# Minimal env usage: keep secrets in envs, but runtime/limits are fixed constants here
import os

# Telegram (keep these env names - set in GitHub Secrets)
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Coins to monitor (CSV string in env or default list)
COINS = [c.strip().replace('"', '').replace("'", '') for c in os.getenv(
    "COINS", "SOLUSDT,ETHUSDT,BTCUSDT,XRPUSDT,DOGEUSDT"
).split(",")]

# Timeframes
LTF_INTERVAL = "15m"
HTF_INTERVAL = "1h"

# Strategy params
EMA_FAST = 9
EMA_SLOW = 15
ADX_LEN = 14
ADX_THRESHOLD = 0     # relaxed for data collection
HTF_FACTOR = 0.1      # relaxed for data collection

# Risk / journal
RISK_USD = 1.0
RR_RATIO = 2.5
LOOKBACK_SL = 10

# Operation / Limits (embedded constants to avoid empty env parsing issues)
# You can edit these values directly here
API_CALL_LIMIT = 200        # total Binance HTTP calls per run
CANDLE_LIMIT = 300          # max candles requested per klines call
RUNTIME_LIMIT_MINUTES = 2   # stop scanning after this many minutes (GH Action runtime safeguard)
CHECK_INTERVAL_SECONDS = 4 * 60 * 60  # 4 hours between scheduled runs (workflow scheduling controls this)

# Files & logs
JOURNAL_FILE = "signals_journal.csv"
LOG_FILE = "error.log"
LAST_SIGNALS_FILE = "last_signals.csv"

# Google Sheets (keep as secrets)
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# HTTP / timeout
REQUEST_TIMEOUT = 10

# Data collection mode
COLLECTION_MODE = True

