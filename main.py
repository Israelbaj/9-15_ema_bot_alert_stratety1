# main.py
import time
import sys
from datetime import datetime, timezone
from strategy import check_strategy
# from alert import send_telegram  # keep commented in collection mode
from utils import append_to_sheets_only, append_many_to_sheets, log_error, API_CALLS, api_limit_reached, update_prev_signal
from sheets_logger import SHEET_OPS
from config import COINS, JOURNAL_FILE, COLLECTION_MODE, RUNTIME_LIMIT_MINUTES, API_CALL_LIMIT

BATCH_SIZE = 10  # how many rows to batch append to sheets at once

def main():
    start_ts = time.time()
    print("🚀 Starting EMA+ADX Multi-Coin Scanner...\n")
    print(f"🕒 Run start: {datetime.now(timezone.utc).isoformat()} UTC")
    print(f"📊 Monitoring {len(COINS)} coins...\n")

    batch = []
    for symbol in COINS:
        elapsed = time.time() - start_ts
        if elapsed >= (int(RUNTIME_LIMIT_MINUTES) * 60):
            print(f"⏱ Runtime limit reached ({elapsed:.1f}s) - saving state & stopping.")
            break

        if api_limit_reached():
            print(f"🛑 Binance API call limit reached ({API_CALLS}/{API_CALL_LIMIT}) - stopping scan.")
            break

        print(f"🔍 Checking {symbol}...")
        try:
            rec = check_strategy(symbol)
            if rec:
                batch.append(rec)
                print(f"Detected {rec['signal']} for {symbol} @ {rec['price']}")
                # update prev-signal immediately (small local file)
                try:
                    update_prev_signal(symbol, {"signal": rec["signal"], "checked_at_utc": rec["checked_at_utc"]})
                except Exception as e:
                    log_error(f"update_prev_signal failed inside main: {repr(e)}")

            # flush batch if large
            if len(batch) >= BATCH_SIZE:
                try:
                    append_many_to_sheets(batch)
                    print(f"☁️ Flushed {len(batch)} records to Google Sheets")
                    batch = []
                except Exception as e:
                    log_error(f"Batch append failed: {repr(e)}")
        except Exception as e:
            log_error(f"main loop error on {symbol}: {repr(e)}")

    # final flush
    if batch:
        try:
            append_many_to_sheets(batch)
            print(f"☁️ Flushed final {len(batch)} records to Google Sheets")
        except Exception as e:
            log_error(f"Final batch append failed: {repr(e)}")

    print("\n✅ Scan complete — results (if any) saved.\n")

if __name__ == "__main__":
    main()
