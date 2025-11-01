# utils.py
import os
import json
import pandas as pd
import requests
from datetime import datetime, timezone
from config import REQUEST_TIMEOUT, LOG_FILE, API_CALL_LIMIT, CANDLE_LIMIT, LAST_SIGNALS_FILE
from sheets_logger import append_row_with_headers

BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "https://data-api.binance.vision")

# module-level API counter for this process run
API_CALLS = 0

def _inc_api_call():
    global API_CALLS
    API_CALLS += 1
    return API_CALLS

def api_limit_reached():
    try:
        return API_CALLS >= int(API_CALL_LIMIT)
    except Exception:
        return False

def fetch_binance_klines(symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    """
    Fetch Binance klines with API call counting and candle limit enforcement.
    If API_CALL_LIMIT reached, returns empty DataFrame.
    """
    global API_CALLS
    if api_limit_reached():
        log_error(f"API call limit reached ({API_CALLS}/{API_CALL_LIMIT}) - skipping fetch for {symbol}")
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    # enforce candle limit
    req_limit = min(int(limit), int(CANDLE_LIMIT))
    url = f"{BINANCE_BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": req_limit}
    try:
        _inc_api_call()
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        raw = resp.json()
        df = pd.DataFrame(raw, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "num_trades",
            "taker_base_vol", "taker_quote_vol", "ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df[["timestamp", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        log_error(f"fetch_binance_klines failed for {symbol} interval {interval}: {repr(e)}")
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

def append_journal(path: str, record: dict):
    """Legacy CSV write, still available if re-enabled."""
    try:
        df = pd.DataFrame([record])
        write_header = not os.path.exists(path)
        df.to_csv(path, mode="a", header=write_header, index=False)
    except Exception as e:
        log_error(f"append_journal error: {repr(e)}")

def append_to_sheets_only(record: dict):
    """Append a single record to Google Sheets safely (header aligned)."""
    try:
        append_row_with_headers(record)
    except Exception as e:
        log_error(f"append_to_sheets_only error: {repr(e)}")

def log_error(msg: str):
    try:
        ts = datetime.now(timezone.utc).isoformat()
        line = f"[{ts}] {msg}\n"
        with open(LOG_FILE, "a") as f:
            f.write(line)
    except Exception:
        print("[CRITICAL] Failed to write log file:", LOG_FILE)
    print("[ERROR]", msg)

# -------------------------
# prev signal persistence
# -------------------------
def get_prev_signal(symbol: str):
    """
    Return the last saved signal record for symbol as dict or None.
    Format: {"symbol":..., "signal":..., "checked_at_utc":...}
    """
    if not os.path.exists(LAST_SIGNALS_FILE):
        return None
    try:
        df = pd.read_csv(LAST_SIGNALS_FILE)
        df = df[df["symbol"].astype(str).str.upper() == symbol.upper()]
        if df.empty:
            return None
        row = df.iloc[-1].to_dict()
        # normalize keys
        return {
            "symbol": row.get("symbol"),
            "signal": row.get("signal"),
            "checked_at_utc": row.get("checked_at_utc")
        }
    except Exception as e:
        log_error(f"get_prev_signal error: {repr(e)}")
        return None

def update_prev_signal(symbol: str, rec: dict):
    """
    rec should contain at least {"signal":..., "checked_at_utc":...}
    Stores a small CSV with last signals per symbol (one row per symbol).
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "symbol": symbol,
            "signal": rec.get("signal"),
            "checked_at_utc": rec.get("checked_at_utc", now)
        }
        if not os.path.exists(LAST_SIGNALS_FILE):
            pd.DataFrame([record]).to_csv(LAST_SIGNALS_FILE, index=False)
            return
        df = pd.read_csv(LAST_SIGNALS_FILE)
        # remove old row for symbol, append new
        df = df[df["symbol"].astype(str).str.upper() != symbol.upper()]
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        df.to_csv(LAST_SIGNALS_FILE, index=False)
    except Exception as e:
        log_error(f"update_prev_signal error: {repr(e)}")

