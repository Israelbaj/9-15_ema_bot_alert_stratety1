# config.py
import os

# Telegram (keep these env names)
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Coins to monitor
COINS = [c.strip().replace('"', '').replace("'", '') for c in os.getenv("COINS", "SOLUSDT,ETHUSDT,BTCUSDT,XRPUSDT,DOGEUSDT").split(",")]

# Timeframes
LTF_INTERVAL = os.getenv("LTF_INTERVAL", "15m")
HTF_INTERVAL = os.getenv("HTF_INTERVAL", "1h")

# Strategy params
EMA_FAST = int(os.getenv("EMA_FAST", 9))
EMA_SLOW = int(os.getenv("EMA_SLOW", 15))
ADX_LEN = int(os.getenv("ADX_LEN", 14))
ADX_THRESHOLD = float(os.getenv("ADX_THRESHOLD", 0))   # relaxed for data collection
HTF_FACTOR = float(os.getenv("HTF_FACTOR", 0.1))       # relaxed for data collection

# Risk / journal
RISK_USD = float(os.getenv("RISK_USD", 1.0))
RR_RATIO = float(os.getenv("RR_RATIO", 2.5))
LOOKBACK_SL = int(os.getenv("LOOKBACK_SL", 10))

# Operation
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 720))   # 12 minutes = 720s if needed
JOURNAL_FILE = os.getenv("JOURNAL_FILE", "signals_journal.csv")
LOG_FILE = os.getenv("LOG_FILE", "bot_errors.log")

# Google Sheets
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# HTTP / timeout
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 10))

# Data collection mode: True -> only Google Sheets (no CSV/Telegram).
# Keep this True while backtesting / collecting. Set False to re-enable CSV & Telegram.
COLLECTION_MODE = True

# Local small cache for previous signals
LAST_SIGNALS_FILE = os.getenv("LAST_SIGNALS_FILE", "last_signals.json")
