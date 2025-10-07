"""
utils.py

Utilities: fetch Binance klines, append to journal CSV, and error logging.
No Telegram calls here (keeps modules separate).
"""

import requests
import pandas as pd
import os
from datetime import datetime, timezone
from config import REQUEST_TIMEOUT, LOG_FILE

# -------------------------
# Global Binance endpoint (region-safe)
# -------------------------
BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "https://data-api.binance.vision")


# -------------------------
# Fetch candlesticks from Binance public API
# -------------------------
def fetch_binance_klines(symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    """
    Fetch Binance klines (OHLCV).
    Returns DataFrame with columns: ['timestamp','open','high','low','close','volume'].
    On error returns empty DataFrame.
    """
    url = f"{BINANCE_BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        raw = resp.json()

        # Build DataFrame
        df = pd.DataFrame(raw, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "num_trades", "taker_base_vol",
            "taker_quote_vol", "ignore"
        ])

        # Convert types & normalize column names
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        # Keep essential columns
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        return df

    except Exception as e:
        log_error(f"fetch_binance_klines failed for {symbol} interval {interval}: {repr(e)}")
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


# -------------------------
# Append one record (dict) to CSV journal (auto-writes header)
# -------------------------
def append_journal(path: str, record: dict):
    """
    Append a dictionary as a row to CSV specified by path.
    If file doesn't exist, header is written.
    """
    try:
        df = pd.DataFrame([record])
        write_header = not os.path.exists(path)
        df.to_csv(path, mode="a", header=write_header, index=False)
    except Exception as e:
        log_error(f"append_journal error: {repr(e)}")


# -------------------------
# Error logging helper
# -------------------------
def log_error(msg: str):
    """
    Append error message to LOG_FILE with ISO timestamp (UTC) and print to console.
    """
    try:
        ts = datetime.now(timezone.utc).isoformat()
        line = f"[{ts}] {msg}\n"
        with open(LOG_FILE, "a") as f:
            f.write(line)
    except Exception:
        # If file write fails, still print
        print("[CRITICAL] Failed to write log file:", LOG_FILE)
    print("[ERROR]", msg)
