# main.py
import time
import os
from datetime import datetime, timezone
from strategy import check_strategy
# from alert import send_telegram   # commented for collection mode (uncomment to re-enable)
from utils import append_journal, log_error, API_CALLS, api_limit_reached, load_run_state, save_run_state
from utils import update_prev_signal, get_prev_signal
from sheets_logger import append_row_with_headers
from config import COINS, JOURNAL_FILE, COLLECTION_MODE, RUNTIME_LIMIT_MINUTES

def main():
    start_ts = time.time()
    state = load_run_state() or {}
    # state keys used: "last_symbol_index" (0-based), "phase" ("main" or "post"), "timestamp"
    last_idx = int(state.get("last_symbol_index", 0))

    print("🚀 Starting EMA+ADX Multi-Coin Scanner...\n")
    print(f"🕒 Run start: {datetime.now(timezone.utc).isoformat()} UTC")
    print(f"📊 Monitoring {len(COINS)} coins...\n")

    for i in range(last_idx, len(COINS)):
        symbol = COINS[i]
        elapsed = time.time() - start_ts
        if elapsed >= (int(RUNTIME_LIMIT_MINUTES) * 60):
            print(f"⏱ Runtime limit reached ({elapsed:.1f}s) - saving progress and stopping.")
            state["last_symbol_index"] = i
            state["phase"] = "main"
            state["timestamp"] = datetime.now(timezone.utc).isoformat()
            save_run_state(state)
            return

        if api_limit_reached():
            print(f"🛑 API call limit reached - saving progress and stopping. API calls so far: {API_CALLS}")
            state["last_symbol_index"] = i
            state["phase"] = "main"
            state["timestamp"] = datetime.now(timezone.utc).isoformat()
            save_run_state(state)
            return

        print(f"🔍 Checking {symbol}...")
        try:
            result = check_strategy(symbol)
            if result:
                # Prevent trivial duplicates: check local prev file; if same signal and same checked_at -> skip
                prev = get_prev_signal(symbol)
                if prev and prev.get("signal") == result.get("signal") and prev.get("checked_at_utc") == result.get("checked_at_utc"):
                    print(f"↩️ Duplicate signal for {symbol} (same as last saved) — skipping append.")
                else:
                    ok = append_row_with_headers(result)
                    if ok:
                        print(f"☁️ Appended {result['signal']} for {symbol} to Google Sheet")
                        # update local prev cache
                        try:
                            update_prev_signal(symbol, {"signal": result["signal"], "checked_at_utc": result["checked_at_utc"]})
                        except Exception as e:
                            log_error(f"update_prev_signal failed: {repr(e)}")
                        if not COLLECTION_MODE:
                            append_journal(JOURNAL_FILE, result)
                    else:
                        # append failed (likely Sheets API issue like 429). Save progress and exit gracefully
                        print("⚠️ Append to sheet failed (possible sheets quota). Saving progress and stopping.")
                        state["last_symbol_index"] = i
                        state["phase"] = "main"
                        state["timestamp"] = datetime.now(timezone.utc).isoformat()
                        save_run_state(state)
                        return
            else:
                print(f"😴 No valid signal for {symbol}")
        except Exception as e:
            log_error(f"main loop error on {symbol}: {repr(e)}")

    # finished scanning all coins: reset last_symbol_index and mark phase to post-analysis next
    state["last_symbol_index"] = 0
    state["phase"] = "post"
    state["timestamp"] = datetime.now(timezone.utc).isoformat()
    save_run_state(state)
    print("\n✅ Scan complete — results saved (if any).\n")

if __name__ == "__main__":
    main()
