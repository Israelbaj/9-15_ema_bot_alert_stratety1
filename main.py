# main.py
import time
import os
from datetime import datetime, timezone
from strategy import check_strategy
# from alert import send_telegram   # uncomment to re-enable alerts
from utils import append_to_sheets_only, append_journal, log_error, api_limit_reached, API_CALLS
from config import COINS, JOURNAL_FILE, COLLECTION_MODE, RUNTIME_LIMIT_MINUTES

def main():
    start_ts = time.time()
    print("🚀 Starting EMA+ADX Multi-Coin Scanner...\n")
    print(f"🕒 Run start: {datetime.now(timezone.utc).isoformat()} UTC")
    print(f"📊 Monitoring {len(COINS)} coins...\n")

    for symbol in COINS:
        # enforce runtime limit
        elapsed = time.time() - start_ts
        if elapsed >= (int(RUNTIME_LIMIT_MINUTES) * 60):
            print(f"⏱ Runtime limit reached ({elapsed:.1f}s) - stopping further checks.")
            break

        # check API limit
        if api_limit_reached():
            print(f"🛑 API call limit reached - stopping scanning. API calls so far: {API_CALLS}")
            break

        print(f"🔍 Checking {symbol}...")
        try:
            recs = check_strategy(symbol)
            if not recs:
                print(f"😴 No valid signal for {symbol}")
                continue

            for rec in recs:
                # append to Google Sheets
                append_to_sheets_only(rec)
                print(f"☁️ Appended {rec['signal']} for {symbol} at {rec['checked_at_utc']} to Google Sheet")

                # optionally also write CSV (disabled in collection mode)
                if not COLLECTION_MODE:
                    append_journal(JOURNAL_FILE, rec)
                    print(f"✅ Logged {rec['signal']} for {symbol} to CSV")

                # keep telegram code in place (commented) for future re-enable
                # msg = f"📈 {symbol} - {rec['signal']} @ {rec['price']} ({rec['checked_at_utc']})"
                # send_telegram(msg)

        except Exception as e:
            log_error(f"main loop error on {symbol}: {repr(e)}")

    print("\n✅ Scan complete — results saved (if any).\n")

if __name__ == "__main__":
    main()
