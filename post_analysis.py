from datetime import datetime
import pandas as pd
from sheets_logger import find_pending_records, _get_sheet, COLUMNS
from utils import fetch_binance_klines, log_error

def analyze_pending():
    sheet = _get_sheet()
    pending = find_pending_records()
    if not pending:
        print("No pending records to analyze.")
        return

    all_records = sheet.get_all_records()
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

            rows_for_symbol = symbol_rows.get(symbol, [])
            next_row = None
            for idx, r in rows_for_symbol:
                if idx <= row_idx:
                    continue
                next_row = (idx, r)
                break

            start_ts = pd.to_datetime(checked_at)
            end_ts = pd.Timestamp.utcnow()
            if next_row:
                try:
                    end_ts = pd.to_datetime(next_row[1].get("checked_at_utc"))
                except Exception:
                    pass

            df = fetch_binance_klines(symbol, interval="15m", limit=1000)
            if df.empty:
                print(f"No price data for {symbol}")
                continue

            mask = (df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)
            window = df.loc[mask]
            if window.empty:
                print(f"No candles in range for {symbol}")
                continue

            if signal_type.upper().startswith("LONG"):
                best_opening_price = float(window["low"].min())
                max_movement_price = float(window["high"].max())
                pct_increase = ((max_movement_price / entry_price) - 1.0) * 100.0
                time_of_max = window.loc[window["high"].idxmax(), "timestamp"]
                trade_time_hrs = (pd.to_datetime(time_of_max) - pd.to_datetime(checked_at)).total_seconds() / 3600.0
            else:
                best_opening_price = float(window["high"].max())
                max_movement_price = float(window["low"].min())
                pct_increase = ((entry_price / max_movement_price) - 1.0) * 100.0
                time_of_min = window.loc[window["low"].idxmin(), "timestamp"]
                trade_time_hrs = (pd.to_datetime(time_of_min) - pd.to_datetime(checked_at)).total_seconds() / 3600.0

            def col_index(name):
                try:
                    return COLUMNS.index(name) + 1
                except ValueError:
                    return None

            updates = {
                "best_opening_price": best_opening_price,
                "max_movement_price": max_movement_price,
                "trade_time_hrs": round(trade_time_hrs, 4),
                "pct_increase": round(pct_increase, 4),
                "status": "analyzed",
            }

            for k, v in updates.items():
                ci = col_index(k)
                if ci:
                    sheet.update_cell(row_idx, ci, v)

            print(f"✅ Updated {symbol} (row {row_idx})")

        except Exception as e:
            log_error(f"post_analysis error for row {row_idx}: {repr(e)}")

if __name__ == "__main__":
    analyze_pending()
