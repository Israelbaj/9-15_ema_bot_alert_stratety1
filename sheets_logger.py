# sheets_logger.py
import os
import json
from datetime import datetime
import gspread
from google.oauth2 import service_account
from config import GOOGLE_SHEET_ID, GOOGLE_SERVICE_ACCOUNT_JSON

# Master column order for the sheet (extendable)
COLUMNS = [
    "checked_at_utc", "symbol", "signal", "price",
    "ema_fast_ltf", "ema_slow_ltf", "ema_fast_slope", "ema_slow_slope",
    "adx_ltf", "adx_slope", "rsi_ltf", "atr_ltf", "price_to_atr",
    "volume_latest", "volume_ma", "volume_ratio",
    "ema_fast_htf", "ema_slow_htf",
    "ltf_trend_bias", "htf_trend_bias",
    "ltf_factor", "htf_factor",
    "prev_signal", "signal_gap_hours",
    "best_opening_price", "max_movement_price", "trade_time_hrs", "pct_increase", "status"
]

def _get_sheet():
    if not GOOGLE_SHEET_ID or not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise RuntimeError("Google Sheets credentials not set.")
    creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
    return sheet

def append_to_google_sheets(record: dict) -> bool:
    """
    Append a single record dict to the sheet using COLUMNS order.
    If sheet is empty or header missing, it will try to create header first.
    """
    try:
        sheet = _get_sheet()
        # Ensure header exists
        header = sheet.row_values(1)
        if not header or header[0] == '':
            sheet.insert_row(COLUMNS, index=1)
        # Build row in column order
        row = [record.get(col, "") for col in COLUMNS]
        sheet.append_row(row, value_input_option="USER_ENTERED")
        print(f"☁️ Synced {record.get('symbol')} → Google Sheet")
        return True
    except Exception as e:
        print(f"[ERROR] Google Sheets sync failed: {repr(e)}")
        return False

def find_pending_records():
    """
    Return list of tuples (row_index, record_dict) where status is empty or 'pending'.
    Row_index is 1-based sheet row index.
    """
    try:
        sheet = _get_sheet()
        records = sheet.get_all_records()
        pending = []
        for idx, rec in enumerate(records, start=2):  # start=2 because row 1 is header
            status = (rec.get("status") or "").strip().lower()
            if status in ("", "pending"):
                pending.append((idx, rec))
        return pending
    except Exception as e:
        print(f"[ERROR] find_pending_records failed: {repr(e)}")
        return []

