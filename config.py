"""
config.py
Central configuration for the EMA+ADX scanner.

Edit values here (coin list, intervals, thresholds, telegram).
"""

# --- Telegram ---
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = "8242923581:AAGsYpi8594_OFAojev29hBLxrHx57XXb1g"
TELEGRAM_CHAT_ID = "5135907311"

# --- Coins to monitor (Binance symbols) ---
COINS = ["SOLUSDT", "ETHUSDT", "BTCUSDT", "XRPUSDT", "DOGEUSDT"]

# --- Timeframes ---
LTF_INTERVAL = "15m"   # lower timeframe for entry signals
HTF_INTERVAL = "1h"    # higher timeframe for trend alignment

# --- Strategy parameters (matches your Pine) ---
EMA_FAST = 9
EMA_SLOW = 15
ADX_LEN = 14
ADX_THRESHOLD = 18.0
HTF_FACTOR = 0.99750   # 1h alignment factor (Pine used 0.99750)

# --- Risk / journal ---
RISK_USD = 1.0
RR_RATIO = 2.5
LOOKBACK_SL = 10

# --- Operation ---
CHECK_INTERVAL = 60 * 15  # run every 15 minutes (match LTF cadence) - change if you want faster tests
JOURNAL_FILE = "signals_journal.csv"
LOG_FILE = "bot_errors.log"

# --- HTTP request timeout ---
REQUEST_TIMEOUT = 10  # seconds for Binance / Telegram
