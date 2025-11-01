# post_analysis.py
import pandas as pd
from datetime import datetime, timezone
from sheets_logger import find_pending_records, update_cells_by_header
from utils import fetch_binance_klines, log_error, API_CALLS, api_limit_reached, load_run_state, save_run_state
from config import CANDLE_LIMIT, RUNTIME_LIMIT_MINUTES

def analyze_pending():
    start_ts = datetime.now().timestamp()
    state = load_run_state() or {}
    pending = find_pending_records()
    if not pending:
        print("No pending records to analyze.")
        # flip state to main for next run
        state["phase"] = "main"
        state["last_symbol_index"] = 0
        save_run_state(state)
        return

    # Build a list of rows per symbol for determining next-signal end windows
    try:
        # to minimize reads we use find_pending_records only once, and we will not call get_all_records repeatedly
        # find_pending_records returned row indices + dicts; build map of subsequent rows using the sheet only once:
        # (we'll fetch all records for mapping - this is one heavier read)
        # Note: find_pending_records already does get_all_records; but if sheet quotas are tight this may fail and returns []
        pass
    except Exception:
        pass

    # Re-fetch all records once to build symbol map (small additional read)
    from sheets_logger import _get_sheet
    try:
        sheet = _get_sheet()
        all_records = sheet.get_all_records()
    except Exception as e:
        log_error(f"Unable to read all records for post-analysis: {repr(e)}")
        return

    symbol_rows = {}
    for idx, rec in enumerate(all_records, start=2):
        sym = (rec.get("symbol") or "").strip().upper()
        if sym:
            symbol_rows.setdefault(sym, []).append((idx, rec))

    # iterate pending items
    for row_idx, rec in pending:
        elapsed_minutes = (datetime.now().timestamp() - start_ts) / 60.0
        if elapsed_minutes >= int(RUNTIME_LIMIT_MINUTES):
            print(f"⏱ Post-analysis runtime limit reached ({elapsed_minutes:.1f} min). Saving state and stopping.")
            state["phase"] = "post"
            state["last_symbol_index"] = 0
            state["timestamp"] = datetime.now(timezone.utc).isoformat()
            save_run_state(state)
            return

        if api_limit_reached():
            print(f"🛑 API call limit reached ({API_CALLS}). Saving state and stopping post-analysis.")
            state["phase"] = "post"
            state["last_symbol_index"] = 0
            state["timestamp"] = datetime.now(timezone.utc).isoformat()
            save_run_state(state)
            return

        try:
            symbol = (rec.get("symbol") or "").strip().upper()
            checked_at = rec.get("checked_at_utc")
            signal_type = (rec.get("signal") or "").upper()
            entry_price = float(rec.get("price") or 0.0)

            if not symbol or not checked_at:
                print(f"Skipping row {row_idx}: missing symbol/checked_at.")
                continue

            # Find next signal row (first later row for same symbol)
            next_row = None
            rows_for_symbol = symbol_rows.get(symbol, [])
            for idx2, r in rows_for_symbol:
                if idx2 <= row_idx:
                    continue
                next_row = (idx2, r)
                break

            start_ts_dt = pd.to_datetime(checked_at)
            if next_row:
                try:
                    end_ts_dt = pd.to_datetime(next_row[1].get("checked_at_utc"))
                except Exception:
                    end_ts_dt = pd.Timestamp.utcnow()
            else:
                end_ts_dt = pd.Timestamp.utcnow()

            # respect API/candle limits inside fetch
            df = fetch_binance_klines(symbol, interval="15m", limit=int(CANDLE_LIMIT))
            if df.empty:
                print(f"No price data for {symbol} to analyze (or API limit reached).")
                continue

            mask = (df["timestamp"] >= start_ts_dt) & (df["timestamp"] <= end_ts_dt)
            window = df.loc[mask].reset_index(drop=True)
            if window.empty:
                print(f"No candles in analysis window for {symbol} between {start_ts_dt} and {end_ts_dt}.")
                # still mark as analyzed to avoid repeated attempts? We'll keep it unmarked so it can be retried later.
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
                print(f"No updates applied for row {row_idx} (maybe missing columns or Sheets quota). Saving state and stopping.")
                state["phase"] = "post"
                state["last_symbol_index"] = 0
                state["timestamp"] = datetime.now(timezone.utc).isoformat()
                save_run_state(state)
                return

        except Exception as e:
            log_error(f"post_analysis error for row {row_idx}: {repr(e)}")

    # finished post-analysis pass
    state["phase"] = "main"
    state["last_symbol_index"] = 0
    state["timestamp"] = datetime.now(timezone.utc).isoformat()
    save_run_state(state)
    print("✅ Post-analysis pass complete.")

if __name__ == "__main__":
    analyze_pending()

