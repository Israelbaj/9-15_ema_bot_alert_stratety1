# sheets_logger.py
import os
import json
import time
import gspread
from google.oauth2 import service_account
from typing import List, Tuple, Dict, Optional

# canonical headers
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

COLUMNS = HEADERS

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# cached sheet client + worksheet for the run (minimizes read calls)
_SHEET = None
_CREDS = None
_LAST_HEADER_CHECK = 0

# sheet op counters (module-level)
SHEET_OPS = 0

def _get_creds():
    global _CREDS
    if _CREDS:
        return _CREDS
    if not SERVICE_JSON:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not set in environment.")
    creds_dict = json.loads(SERVICE_JSON)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    _CREDS = creds
    return creds

def _get_sheet():
    """
    Return cached sheet object (sheet1). Minimize calls to Google's API.
    """
    global _SHEET
    if _SHEET is not None:
        return _SHEET
    if not SHEET_ID:
        raise RuntimeError("GOOGLE_SHEET_ID not set in environment.")
    creds = _get_creds()
    client = gspread.authorize(creds)
    sp = client.open_by_key(SHEET_ID)
    _SHEET = sp.sheet1
    return _SHEET

def ensure_headers(force: bool = False):
    """
    Ensure first row equals HEADERS. If mismatch or forced, rewrite header row.
    Minimizes read calls by caching last check for 30s.
    """
    global _LAST_HEADER_CHECK, SHEET_OPS
    now = time.time()
    if not force and (now - _LAST_HEADER_CHECK) < 30:
        return
    sheet = _get_sheet()
    existing = sheet.row_values(1)
    SHEET_OPS += 1
    if existing != HEADERS:
        try:
            if len(existing) >= 1:
                sheet.delete_rows(1)
            sheet.insert_row(HEADERS, index=1)
            SHEET_OPS += 2
            print("✅ Sheet headers re-written to canonical HEADERS.")
        except Exception as e:
            print("⚠️ Failed to rewrite headers:", e)
            raise
    else:
        print("✅ Sheet headers already aligned.")
    _LAST_HEADER_CHECK = time.time()

def append_row_with_headers(record: dict) -> bool:
    """
    Append a single row in HEADERS order.
    """
    sheet = _get_sheet()
    ensure_headers()
    row = [record.get(k, "") for k in HEADERS]
    sheet.append_row(row, value_input_option="USER_ENTERED")  # one API write
    global SHEET_OPS
    SHEET_OPS += 1
    return True

def append_rows_with_headers(records: List[dict]) -> bool:
    """
    Append multiple rows as a single batch (sheet.append_rows).
    Each row will be in HEADERS order. This uses fewer requests.
    """
    if not records:
        return True
    sheet = _get_sheet()
    ensure_headers()
    rows = [[r.get(k, "") for k in HEADERS] for r in records]
    # append_rows performs fewer requests vs many append_row
    sheet.append_rows(rows, value_input_option="USER_ENTERED")
    global SHEET_OPS
    SHEET_OPS += 1
    return True

def get_all_records():
    """
    Return list of dicts (gspread get_all_records).
    WARNING: this is a read API call; caller should be careful and throttle.
    """
    sheet = _get_sheet()
    global SHEET_OPS
    SHEET_OPS += 1
    return sheet.get_all_records()

def find_pending_records() -> List[Tuple[int, Dict]]:
    """
    Return list of (row_index, record_dict) for rows that need post-analysis.
    Criteria: status not 'analyzed' or pct_increase blank.
    """
    ensure_headers()
    all_records = get_all_records()
    pending = []
    for i, rec in enumerate(all_records, start=2):
        status = (rec.get("status") or "").strip().lower()
        pct = rec.get("pct_increase")
        if status != "analyzed" or pct in (None, "", " "):
            pending.append((i, rec))
    return pending

def update_cells_by_header(row_idx: int, updates: dict) -> bool:
    """
    Batch-update cells on a single row using header mapping.
    """
    sheet = _get_sheet()
    ensure_headers()
    header_row = sheet.row_values(1)
    global SHEET_OPS
    SHEET_OPS += 1
    to_write = []
    for k, v in updates.items():
        if k not in header_row:
            print(f"⚠️ Column '{k}' not found in sheet headers; skipping.")
            continue
        col_idx = header_row.index(k) + 1
        to_write.append(((row_idx, col_idx), v))
    if not to_write:
        return False
    cell_list = [gspread.Cell(r, c, val) for (r, c), val in to_write]
    sheet.update_cells(cell_list, value_input_option="USER_ENTERED")
    SHEET_OPS += 1
    return True

def find_latest_signal_row(symbol: str) -> Optional[int]:
    """
    Return last row number for symbol or None. Uses get_all_records (read).
    """
    vals = get_all_records()
    last_row = None
    for i, rec in enumerate(vals, start=2):
        if (rec.get("symbol") or "").strip().upper() == symbol.strip().upper():
            last_row = i
    return last_row

