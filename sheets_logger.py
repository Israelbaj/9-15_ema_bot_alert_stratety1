import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime

COLUMNS = [
    "checked_at_utc", "symbol", "signal", "price",
    "ema_fast_ltf", "ema_slow_ltf", "adx_latest",
    "ema_fast_htf", "ema_slow_htf", "ltf_trend_bias", "htf_trend_bias",
    "ltf_factor", "htf_factor", "rsi", "volume",
    "best_opening_price", "max_movement_price", "trade_time_hrs", "pct_increase", "status"
]

def _get_sheet():
    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not creds_json or not sheet_id:
        raise ValueError("Missing Google Sheets credentials or Sheet ID in environment variables")

    creds = Credentials.from_service_account_info(eval(creds_json))
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    return sh.sheet1

def append_row(data_dict):
    sheet = _get_sheet()
    row = [data_dict.get(col, "") for col in COLUMNS]
    sheet.append_row(row, value_input_option="USER_ENTERED")

def find_pending_records():
    sheet = _get_sheet()
    all_records = sheet.get_all_records()
    pending = []
    for i, rec in enumerate(all_records, start=2):
        if rec.get("status", "").lower() != "analyzed" and rec.get("signal"):
            pending.append((i, rec))
    return pending


