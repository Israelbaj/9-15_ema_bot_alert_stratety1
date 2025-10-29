# utils.py
import requests
import pandas as pd
import os
import json
from datetime import datetime, timezone
from config import REQUEST_TIMEOUT, LOG_FILE, JOURNAL_FILE, COLLECTION_MODE, LAST_SIGNALS_FILE
from sheets_logger import append_to_google_sheets

BINANCE_BASE_URL = os.getenv("BINANCE_BASE_URL", "https://data-api.binance.vision")

def fetch_binance_klines(symbol: str, interval: str, limit: int = 500) -> pd.DataFrame:
    url = f"{BINANCE_BASE_URL}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        raw = resp.json()

        df = pd.DataFrame(raw, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "num_trades", "taker_base_vol",
            "taker_quote_vol", "ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df[["timestamp", "open", "high", "low", "close", "volume"]]
    except Exception as e:
        log_error(f"fetch_binance_klines failed for {symbol} interval {interval}: {repr(e)}")
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

def append_journal(path: str, record: dict):
    """
    Local CSV logging helper (kept but not used in COLLECTION_MODE).
    """
    try:
        if COLLECTION_MODE:
            # collection mode: skip local CSV writes to reduce churn. (comment out if you want CSV)
            return
        df = pd.DataFrame([record])
        write_header = not os.path.exists(path)
        df.to_csv(path, mode="a", header=write_header, index=False)
    except Exception as e:
        log_error(f"append_journal error: {repr(e)}")

def append_to_sheets_only(record: dict):
    """
    Primary path used during collection: write directly to Google Sheets.
    """
    try:
        append_to_google_sheets(record)
    except Exception as e:
        log_error(f"append_to_sheets_only failed: {repr(e)}")

def log_error(msg: str):
    try:
        ts = datetime.now(timezone.utc).isoformat()
        line = f"[{ts}] {msg}\n"
        with open(LOG_FILE, "a") as f:
            f.write(line)
    except Exception:
        print("[CRITICAL] Failed to write log file:", LOG_FILE)
    print("[ERROR]", msg)

# small local cache for previous signal per symbol
def get_prev_signal(symbol: str) -> dict:
    try:
        if not os.path.exists(LAST_SIGNALS_FILE):
            return {}
        with open(LAST_SIGNALS_FILE, "r") as f:
            data = json.load(f)
        return data.get(symbol, {})
    except Exception:
        return {}

def update_prev_signal(symbol: str, payload: dict):
    try:
        data = {}
        if os.path.exists(LAST_SIGNALS_FILE):
            with open(LAST_SIGNALS_FILE, "r") as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = {}
        data[symbol] = payload
        with open(LAST_SIGNALS_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        log_error(f"update_prev_signal error: {repr(e)}")

