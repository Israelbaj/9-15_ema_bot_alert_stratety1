# main.py
import time
import os
from datetime import datetime, timezone
from strategy import check_strategy
# from alert import send_telegram   # commented for collection mode (uncomment to re-enable)
from utils import append_to_sheets_only, append_journal, log_error, API_CALLS, api_limit_reached
from config import COINS, JOURNAL_FILE, COLLECTION_MODE, RUNTIME_LIMIT_MINUTES

def main():
    start_ts = time.time()
    print("🚀 Starting EMA+ADX Multi-Coin Scanner...\n")
    print(f"🕒 Run start: {datetime.now(timezone.utc).isoformat()} UTC")
    print(f"📊 Monitoring {len(COINS)} coins...\n")

    for symbol in COINS:
        # runtime cap
        elapsed = time.time() - start_ts
        if elapsed >= (int(RUNTIME_LIMIT_MINUTES) * 60):
            print(f"⏱ Runtime limit reached ({elapsed:.1f}s) - stopping further checks.")
            break

        # API cap
        if api_limit_reached():
            print(f"🛑 API call limit reached - stopping scanning. API calls so far: {API_CALLS}")
            break

        print(f"🔍 Checking {symbol}...")
        try:
            result = check_strategy(symbol)
            if result:
                append_to_sheets_only(result)
                print(f"☁️ Appended {result['signal']} for {symbol} to Google Sheet")

                if not COLLECTION_MODE:
                    append_journal(JOURNAL_FILE, result)
                    print(f"✅ Logged {result['signal']} for {symbol} to CSV")

                # Telegram intentionally left commented for collection
                # msg = f"📈 {symbol} - {result['signal']} @ {result['price']}"
                # send_telegram(msg)

            else:
                print(f"😴 No valid signal for {symbol}")

        except Exception as e:
            log_error(f"main loop error on {symbol}: {repr(e)}")

    print("\n✅ Scan complete — results saved (if any).\n")

if __name__ == "__main__":
    main()

