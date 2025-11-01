# main.py
import time
import os
from datetime import datetime, timezone
from strategy import check_strategy
# from alert import send_telegram   # commented for collection mode
from utils import append_to_sheets_only, append_journal, log_error, API_CALLS, api_limit_reached
from config import COINS, JOURNAL_FILE, COLLECTION_MODE, RUNTIME_LIMIT_MINUTES, API_CALL_LIMIT, CANDLE_LIMIT
from sheets_logger import append_rows_with_headers
from state_manager import save_state, load_state

def main():
    start_ts = time.time()
    state = load_state() or {}
    processed = state.get("processed_symbols", [])
    print("🚀 Starting EMA+ADX Multi-Coin Scanner...\n")
    print(f"🕒 Run start: {datetime.now(timezone.utc).isoformat()} UTC")
    print(f"📊 Monitoring {len(COINS)} coins...\n")

    batch_to_append = []

    for symbol in COINS:
        # skip if already processed in previous partial run
        if symbol in processed:
            print(f"⏭ Skipping previously processed symbol (resume): {symbol}")
            continue

        elapsed = time.time() - start_ts
        if elapsed >= (float(RUNTIME_LIMIT_MINUTES) * 60):
            print(f"⏱ Runtime limit reached ({elapsed:.1f}s) - saving state and exiting.")
            # save state: processed list so next run resumes
            state["processed_symbols"] = processed
            save_state(state)
            return

        if api_limit_reached():
            print(f"🛑 API call limit reached - saving state and exiting. API calls so far: {API_CALLS}")
            state["processed_symbols"] = processed
            save_state(state)
            return

        print(f"🔍 Checking {symbol}...")
        try:
            recs = check_strategy(symbol)
            if recs:
                # collect into batch
                for r in recs:
                    batch_to_append.append(r)
                print(f"☁️ Queued {len(recs)} signal(s) for {symbol}")
                # mark as processed so we don't duplicate if saved mid-run
                processed.append(symbol)

            else:
                print(f"😴 No valid signal(s) for {symbol}")
                processed.append(symbol)

        except Exception as e:
            log_error(f"main loop error on {symbol}: {repr(e)}")
            processed.append(symbol)

        # If batch is large, flush to sheet now to avoid memory and reduce risk
        if len(batch_to_append) >= 10:
            try:
                append_rows_with_headers(batch_to_append)
                print(f"☁️ Flushed {len(batch_to_append)} rows to Google Sheet.")
                batch_to_append = []
            except Exception as e:
                log_error(f"batch append failed: {repr(e)}")
                # save & exit to avoid repeated errors
                state["processed_symbols"] = processed
                save_state(state)
                return

    # flush any remaining rows
    if batch_to_append:
        try:
            append_rows_with_headers(batch_to_append)
            print(f"☁️ Flushed {len(batch_to_append)} rows to Google Sheet.")
        except Exception as e:
            log_error(f"final batch append failed: {repr(e)}")
            # still save state
            state["processed_symbols"] = processed
            save_state(state)
            return

    # clear saved state on successful completion
    save_state({})
    print("\n✅ Scan complete — results saved (if any).\n")

if __name__ == "__main__":
    main()

