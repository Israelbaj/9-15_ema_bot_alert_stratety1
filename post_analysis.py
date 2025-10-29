# post_analysis.py
import time
from datetime import datetime, timezone
from sheets_logger import find_pending_records, _get_sheet, COLUMNS
from utils import fetch_binance_klines, log_error
import pandas as pd

def analyze_pending():
    sheet = _get_sheet()
    pending = find_pending_records()
    if not pending:
        print("No pending records to analyze.")
        return

    # get all records to detect next signals per symbol (we use the sheet data)
    all_records = sheet.get_all_records()

    # Build map of latest signal row index per symbol (so we can detect "next signal")
    symbol_rows = {}
    for idx, rec in enumerate(all_records, start=2):
        sym = rec.get("symbol")
        if sym:
            symbol_rows.setdefault(sym, []).append((idx, rec))

    for row_idx, rec in pending:
        try:
            symbol = rec.get("symbol")
            checked_at = rec.get("checked_at_utc")
            signal_type = rec.get("signal")
            entry_price = float(rec.get("price") or 0)

            # find the "next" signal row for this symbol after this checked_at (if any)
            rows_for_symbol = symbol_rows.get(symbol, [])
            next_row = None
            for idx, r in rows_for_symbol:
                if idx <= row_idx:
                    continue
                # choose the first later signal (assuming sheet appended in time order)
                next_row = (idx, r)
                break

            # Time window: start = checked_at, end = next_signal_time if exists else now
            start_ts = pd.to_datetime(checked_at)
            end_ts = pd.Timestamp.utcnow()
            if next_row:
                # parse the next row's checked_at_utc
                try:
                    end_ts = pd.to_datetime(next_row[1].get("checked_at_utc"))
                except Exception:
                    end_ts = pd.Timestamp.utcnow()

            # fetch klines from start to end (use 15m or 5m as needed)
            # convert to millis and compute limit; simplest: fetch 1000 and then slice
            df = fetch_binance_klines(symbol, interval="15m", limit=1000)
            if df.empty:
                print(f"No price data for {symbol} to analyze.")
                continue

            # keep only rows between start_ts and end_ts
            mask = (df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)
            window = df.loc[mask]
            if window.empty:
                print(f"No price candles in window for {symbol}")
                continue

            # For LONG: best_opening_price = min(low), max_movement_price = max(high)
            # For SHORT: best_opening_price = max(high), max_movement_price = min(low)
            if signal_type and signal_type.upper().startswith("LONG"):
                best_opening_price = float(window["low"].min())
                max_movement_price = float(window["high"].max())
                # pct increase relative to entry
                pct_increase = ((max_movement_price / entry_price) - 1.0) * 100.0 if entry_price else None
                # trade_time: time from entry to time of max_movement_price
                idx_max = window["high"].idxmax()
                time_of_max = window.loc[idx_max, "timestamp"]
                trade_time_hrs = (pd.to_datetime(time_of_max) - pd.to_datetime(checked_at)).total_seconds() / 3600.0
            else:
                # SHORT
                best_opening_price = float(window["high"].max())
                max_movement_price = float(window["low"].min())
                pct_increase = ((entry_price / max_movement_price) - 1.0) * 100.0 if entry_price and max_movement_price else None
                idx_min = window["low"].idxmin()
                time_of_min = window.loc[idx_min, "timestamp"]
                trade_time_hrs = (pd.to_datetime(time_of_min) - pd.to_datetime(checked_at)).total_seconds() / 3600.0

            # Update sheet row columns: find column indices based on COLUMNS list
            def col_index(name):
                try:
                    return COLUMNS.index(name) + 1  # 1-based
                except ValueError:
                    return None

            updates = {
                "best_opening_price": best_opening_price,
                "max_movement_price": max_movement_price,
                "trade_time_hrs": round(trade_time_hrs, 6) if trade_time_hrs is not None else "",
                "pct_increase": round(pct_increase, 6) if pct_increase is not None else "",
                "status": "analyzed"
            }

            for k, v in updates.items():
                ci = col_index(k)
                if ci:
                    sheet.update_cell(row_idx, ci, v)

            print(f"Updated analysis for {symbol} (row {row_idx}).")

        except Exception as e:
            log_error(f"post_analysis error for row {row_idx}: {repr(e)}")

if __name__ == "__main__":
    analyze_pending()
