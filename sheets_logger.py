# sheets_logger.py
# Header-safe Google Sheets helper for appending & updating rows.

import os
import json
import gspread
from google.oauth2 import service_account
from typing import List, Tuple, Dict

# The canonical header order used by both main.py and post_analysis.py
HEADERS: List[str] = [
    "checked_at_utc","symbol","signal","price",
    "ema_fast_ltf","ema_slow_ltf","ema_fast_slope","ema_slow_slope",
    "adx_ltf","adx_slope","rsi_ltf","atr_ltf","price_to_atr",
    "volume_latest","volume_ma","volume_ratio",
    "ema_fast_htf","ema_slow_htf",
    "ltf_trend_bias","htf_trend_bias","ltf_factor","htf_factor",
    "prev_signal","signal_gap_hours",
    "best_opening_price","max_movement_price","trade_time_hrs","pct_increase","status"
]

# export as COLUMNS for compatibility
COLUMNS = HEADERS

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")


def _get_creds():
    if not SERVICE_JSON:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not set in environment.")
    creds_dict = json.loads(SERVICE_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return creds


def _get_sheet():
    """
    Returns the first worksheet (sheet1) object.
    """
    if not SHEET_ID:
        raise RuntimeError("GOOGLE_SHEET_ID not set in environment.")
    creds = _get_creds()
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet


def ensure_headers():
    """
    Ensure the sheet's first row equals HEADERS. If there is a mismatch, replace the header row.
    This prevents column drift.
    """
    sheet = _get_sheet()
    existing = sheet.row_values(1)
    if existing != HEADERS:
        # replace header row
        # delete first row then insert HEADERS at row 1
        try:
            # If sheet already has some rows, update row 1
            if len(existing) >= 1:
                sheet.delete_rows(1)
        except Exception:
            pass
        sheet.insert_row(HEADERS, index=1)
        print("✅ Sheet headers re-written to canonical HEADERS.")
    else:
        print("✅ Sheet headers already aligned.")


def append_row_with_headers(record: dict) -> bool:
    """
    Append a row to the sheet using HEADERS order. Missing keys are filled with "".
    Returns True on success.
    """
    sheet = _get_sheet()
    ensure_headers()
    row = [record.get(k, "") for k in HEADERS]
    sheet.append_row(row, value_input_option="USER_ENTERED")
    return True


def find_pending_records() -> List[Tuple[int, Dict]]:
    """
    Return list of (row_index, record_dict) for rows that need post-analysis.
    Criteria: status not 'analyzed' (case-insensitive) OR pct_increase empty.
    row_index is the 1-based sheet row index.
    """
    sheet = _get_sheet()
    ensure_headers()
    all_records = sheet.get_all_records()  # returns list of dicts (header -> value)
    pending = []
    for i, rec in enumerate(all_records, start=2):  # data starts at row 2
        status = (rec.get("status") or "").strip().lower()
        pct = rec.get("pct_increase")
        # consider pending if not analyzed or pct_increase blank
        if status != "analyzed" or pct in (None, "", " "):
            pending.append((i, rec))
    return pending


def find_latest_signal_row(symbol: str):
    """
    Return the row index (1-based) of the latest row for symbol, or None.
    """
    sheet = _get_sheet()
    ensure_headers()
    vals = sheet.get_all_records()
    last_row = None
    for i, rec in enumerate(vals, start=2):
        if (rec.get("symbol") or "").strip().upper() == symbol.strip().upper():
            last_row = i
    return last_row


def update_cells_by_header(row_idx: int, updates: dict):
    """
    Update multiple cells on row row_idx using HEADERS to map header->col index.
    updates: dict of header_name -> value
    """
    sheet = _get_sheet()
    ensure_headers()
    header_row = sheet.row_values(1)
    # build list of (cell, value)
    to_write = []
    for k, v in updates.items():
        if k not in header_row:
            print(f"⚠️ Column '{k}' not found in sheet headers; skipping.")
            continue
        col_idx = header_row.index(k) + 1
        to_write.append(((row_idx, col_idx), v))

    # perform updates (batch update to save requests)
    if not to_write:
        return False

    cell_list = []
    for (r, c), val in to_write:
        cell_list.append(gspread.Cell(r, c, val))
    sheet.update_cells(cell_list, value_input_option="USER_ENTERED")
    return True
