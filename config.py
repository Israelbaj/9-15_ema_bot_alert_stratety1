# config.py
# Use environment variables when present (works locally too with defaults)

import os

# --- Telegram (use GitHub secrets in Actions) ---
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")   # set in repo Secrets
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")       # set in repo Secrets

# --- Coins to monitor ---
COINS = os.getenv("COINS", "SOLUSDT,ETHUSDT,BTCUSDT,XRPUSDT,DOGEUSDT").split(",")

# --- Timeframes ---
LTF_INTERVAL = os.getenv("LTF_INTERVAL", "15m")
HTF_INTERVAL = os.getenv("HTF_INTERVAL", "1h")

# --- Strategy parameters (defaults match your Pine) ---
EMA_FAST = int(os.getenv("EMA_FAST", 9))
EMA_SLOW = int(os.getenv("EMA_SLOW", 15))
ADX_LEN = int(os.getenv("ADX_LEN", 14))
ADX_THRESHOLD = float(os.getenv("ADX_THRESHOLD", 18.0))
HTF_FACTOR = float(os.getenv("HTF_FACTOR", 0.9975))

# --- Risk / journal ---
RISK_USD = float(os.getenv("RISK_USD", 1.0))
RR_RATIO = float(os.getenv("RR_RATIO", 2.5))
LOOKBACK_SL = int(os.getenv("LOOKBACK_SL", 10))

# --- Operation ---
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 900))   # default 15 minutes
JOURNAL_FILE = os.getenv("JOURNAL_FILE", "signals_journal.csv")
LOG_FILE = os.getenv("LOG_FILE", "bot_errors.log")

# --- HTTP / timeout ---
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 10))
