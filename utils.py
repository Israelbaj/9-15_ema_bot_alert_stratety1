# utils.py (only the parts relevant to Sheets integration are shown/modified)
import os
import pandas as pd
from datetime import datetime, timezone
from config import REQUEST_TIMEOUT, LOG_FILE
from sheets_logger import append_row_with_headers, COLUMNS
import requests

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
    Legacy CSV write. Still available if you re-enable CSV journaling.
    """
    try:
        df = pd.DataFrame([record])
        write_header = not os.path.exists(path)
        df.to_csv(path, mode="a", header=write_header, index=False)
    except Exception as e:
        log_error(f"append_journal error: {repr(e)}")


def append_to_sheets_only(record: dict):
    """
    Append a single record to Google Sheets using header-safe append.
    Ensures HEADERS are present and uses consistent ordering.
    """
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


