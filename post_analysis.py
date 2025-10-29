import time
from datetime import datetime, timezone
import pandas as pd
from sheets_logger import find_pending_records, _get_sheet, COLUMNS
from utils import fetch_binance_klines, log_error


def analyze_pending():
    print("🔍 Starting post-analysis phase...")
    sheet = _get_sheet()
    pending = find_pending_records()
    if not pending:
        print("✅ No pending trades to analyze.")
        return

    all_records = sheet.get_all_records()
    symbol_rows = {}
    for idx, rec in enumerate(all_records, start=2):  # header = row 1
        sym = rec.get("symbol")
        if sym:
            symbol_rows.setdefault(sym, []).append((idx, rec))

    for row_idx, rec in pending:
        try:
            symbol = rec.get("symbol")
            checked_at = rec.get("checked_at_utc")
            signal_type = str(rec.get("signal") or "").upper()
            entry_price = float(rec.get("price") or 0)

            if not symbol or not checked_at or not entry_price:
                print(f"⚠️ Skipping row {row_idx} — incomplete data.")
                continue

            # find next signal for same symbol
            rows_for_symbol = symbol_rows.get(symbol, [])
            next_row = None
            for idx, r in rows_for_symbol:
                if idx > row_idx:
                    next_row = (idx, r)
                    break

            start_ts = pd.to_datetime(checked_at, utc=True)
            end_ts = pd.to_datetime(
                next_row[1].get("checked_at_utc"), utc=True
            ) if next_row else pd.Timestamp.utcnow()

            # Fetch 5m candles
            df = fetch_binance_klines(symbol, interval="5m", limit=1000)
            if df.empty:
                print(f"⚠️ No data for {symbol}.")
                continue

            # filter between timestamps
            window = df[(df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)]
            if window.empty:
                print(f"⚠️ No valid window for {symbol} between {start_ts} and {end_ts}.")
                continue

            if "LONG" in signal_type:
                best_opening_price = float(window["low"].min())
                max_movement_price = float(window["high"].max())
                pct_increase = (
                    ((max_movement_price / entry_price) - 1.0) * 100.0
                    if entry_price else None
                )
                idx_max = window["high"].idxmax()
                trade_time_hrs = (
                    (pd.to_datetime(window.loc[idx_max, "timestamp"]) - start_ts)
                    .total_seconds() / 3600.0
                )
            else:
                best_opening_price = float(window["high"].max())
                max_movement_price = float(window["low"].min())
                pct_increase = (
                    ((entry_price / max_movement_price) - 1.0) * 100.0
                    if entry_price and max_movement_price else None
                )
                idx_min = window["low"].idxmin()
                trade_time_hrs = (
                    (pd.to_datetime(window.loc[idx_min, "timestamp"]) - start_ts)
                    .total_seconds() / 3600.0
                )

            def col_index(name):
                try:
                    return COLUMNS.index(name) + 1
                except ValueError:
                    return None

            updates = {
                "best_opening_price": round(best_opening_price, 8),
                "max_movement_price": round(max_movement_price, 8),
                "trade_time_hrs": round(trade_time_hrs, 4),
                "pct_increase": round(pct_increase, 4) if pct_increase is not None else "",
                "status": "analyzed"
            }

            # push updates to Google Sheet
            for key, val in updates.items():
                ci = col_index(key)
                if ci:
                    sheet.update_cell(row_idx, ci, val)
            print(f"✅ {symbol} updated successfully (row {row_idx}).")

        except Exception as e:
            log_error(f"post_analysis error for {symbol or 'unknown'} row {row_idx}: {repr(e)}")
            print(f"❌ Error analyzing row {row_idx}: {e}")


if __name__ == "__main__":
    analyze_pending()
