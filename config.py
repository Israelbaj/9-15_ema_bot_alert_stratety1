# config.py
import os

# --- API / runtime limits (safe defaults; override via env) ---
# total Binance calls per run
API_CALL_LIMIT = int(os.getenv("API_CALL_LIMIT") or 200)
# max candles in one kline request (we're working on 15m timeframe)
CANDLE_LIMIT = int(os.getenv("CANDLE_LIMIT") or 300)
# max runtime for the runner process in minutes (first run: 5; later you can reduce)
RUNTIME_LIMIT_MINUTES = int(os.getenv("RUNTIME_LIMIT_MINUTES") or 5)
# safe margin for Google Sheets read requests per minute (used only for decision-making)
SHEETS_SAFE_READS_PER_MIN = int(os.getenv("SHEETS_SAFE_READS_PER_MIN") or 55)

# --- Standard bot config (unchanged defaults, override with env as needed) ---
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

COINS = [c.strip().replace('"', '').replace("'", '') for c in os.getenv("COINS", "SOLUSDT,ETHUSDT,BTCUSDT,XRPUSDT,DOGEUSDT").split(",")]

LTF_INTERVAL = os.getenv("LTF_INTERVAL", "15m")
HTF_INTERVAL = os.getenv("HTF_INTERVAL", "1h")

EMA_FAST = int(os.getenv("EMA_FAST") or 9)
EMA_SLOW = int(os.getenv("EMA_SLOW") or 15)
ADX_LEN = int(os.getenv("ADX_LEN") or 14)
ADX_THRESHOLD = float(os.getenv("ADX_THRESHOLD") or 0.0)
HTF_FACTOR = float(os.getenv("HTF_FACTOR") or 0.1)

RISK_USD = float(os.getenv("RISK_USD") or 1.0)
RR_RATIO = float(os.getenv("RR_RATIO") or 2.5)
LOOKBACK_SL = int(os.getenv("LOOKBACK_SL") or 10)

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL") or 720)
JOURNAL_FILE = os.getenv("JOURNAL_FILE") or "signals_journal.csv"
LOG_FILE = os.getenv("LOG_FILE") or "error.log"

GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT") or 10)

# collection mode: only Google Sheets (True) or allow CSV/logging/telegram (False)
COLLECTION_MODE = (os.getenv("COLLECTION_MODE") or "True").lower() in ("1", "true", "yes")

# local persistence for last signals + run state
LAST_SIGNALS_FILE = os.getenv("LAST_SIGNALS_FILE") or "last_signals.csv"
RUN_STATE_FILE = os.getenv("RUN_STATE_FILE") or "run_state.json"


