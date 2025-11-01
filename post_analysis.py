# post_analysis.py
import pandas as pd
from datetime import datetime, timezone
from sheets_logger import _get_sheet, find_pending_records, update_cells_by_header
from utils import fetch_binance_klines, log_error, API_CALLS, api_limit_reached

def analyze_pending():
    sheet = _get_sheet()
    pending = find_pending_records()
    if not pending:
        print("No pending records to analyze.")
        return

    # Build map of rows per symbol
    all_records = sheet.get_all_records()
    symbol_rows = {}
    for idx, rec in enumerate(all_records, start=2):
        sym = (rec.get("symbol") or "").strip().upper()
        if sym:
            symbol_rows.setdefault(sym, []).append((idx, rec))

    for row_idx, rec in pending:
        # check API limit before each analysis
        if api_limit_reached():
            print(f"API call limit reached ({API_CALLS}) - stopping post-analysis.")
            break

        try:
            symbol = (rec.get("symbol") or "").strip().upper()
            checked_at = rec.get("checked_at_utc")
            signal_type = (rec.get("signal") or "").upper()
            entry_price = float(rec.get("price") or 0.0)

            if not symbol or not checked_at:
                print(f"Skipping row {row_idx}: missing symbol/checked_at.")
                continue

            # next signal row (first later row for same symbol)
            next_row = None
            rows_for_symbol = symbol_rows.get(symbol, [])
            for idx, r in rows_for_symbol:
                if idx <= row_idx:
                    continue
                next_row = (idx, r)
                break

            start_ts = pd.to_datetime(checked_at)
            if next_row:
                try:
                    end_ts = pd.to_datetime(next_row[1].get("checked_at_utc"))
                except Exception:
                    end_ts = pd.Timestamp.utcnow()
            else:
                end_ts = pd.Timestamp.utcnow()

            # respect API/candle limits inside fetch
            df = fetch_binance_klines(symbol, interval="15m", limit=300)
            if df.empty:
                print(f"No price data for {symbol} to analyze.")
                continue

            mask = (df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)
            window = df.loc[mask].reset_index(drop=True)
            if window.empty:
                print(f"No candles in analysis window for {symbol} between {start_ts} and {end_ts}.")
                continue

            if signal_type.startswith("LONG"):
                best_opening_price = float(window["low"].min())
                max_movement_price = float(window["high"].max())
                idx_max = window["high"].idxmax()
                time_of_max = window.loc[idx_max, "timestamp"]
                trade_time_hrs = (pd.to_datetime(time_of_max) - pd.to_datetime(checked_at)).total_seconds() / 3600.0
                pct_increase = ((max_movement_price / entry_price) - 1.0) * 100.0 if entry_price else None
            else:
                best_opening_price = float(window["high"].max())
                max_movement_price = float(window["low"].min())
                idx_min = window["low"].idxmin()
                time_of_min = window.loc[idx_min, "timestamp"]
                trade_time_hrs = (pd.to_datetime(time_of_min) - pd.to_datetime(checked_at)).total_seconds() / 3600.0
                pct_increase = ((entry_price / max_movement_price) - 1.0) * 100.0 if entry_price and max_movement_price else None

            updates = {
                "best_opening_price": round(best_opening_price, 8),
                "max_movement_price": round(max_movement_price, 8),
                "trade_time_hrs": round(trade_time_hrs, 6) if trade_time_hrs is not None else "",
                "pct_increase": round(pct_increase, 6) if pct_increase is not None else "",
                "status": "analyzed"
            }

            ok = update_cells_by_header(row_idx, updates)
            if ok:
                print(f"Updated analysis for {symbol} (row {row_idx}).")
            else:
                print(f"No updates applied for row {row_idx} (maybe missing columns).")

        except Exception as e:
            log_error(f"post_analysis error for row {row_idx}: {repr(e)}")

if __name__ == "__main__":
    analyze_pending()
