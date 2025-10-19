# utils.py
import requests
import pandas as pd
import os
from datetime import datetime, timezone
from config import REQUEST_TIMEOUT, LOG_FILE
from sheets_logger import append_to_google_sheets  # ✅ new import

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
    Append record to CSV and Google Sheet (if configured).
    """
    try:
        # Write locally
        df = pd.DataFrame([record])
        write_header = not os.path.exists(path)
        df.to_csv(path, mode="a", header=write_header, index=False)

        # Sync to Google Sheets
        append_to_google_sheets(record)

    except Exception as e:
        log_error(f"append_journal error: {repr(e)}")

def log_error(msg: str):
    try:
        ts = datetime.now(timezone.utc).isoformat()
        line = f"[{ts}] {msg}\n"
        with open(LOG_FILE, "a") as f:
            f.write(line)
    except Exception:
        print("[CRITICAL] Failed to write log file:", LOG_FILE)
    print("[ERROR]", msg)
