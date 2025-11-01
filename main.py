import time
from datetime import datetime, timezone
from strategy import check_strategy
from utils import append_to_sheets_only, append_journal, log_error, API_CALLS, api_limit_reached
from config import COINS, JOURNAL_FILE, COLLECTION_MODE, RUNTIME_LIMIT_MINUTES

def main():
    start_ts = time.time()
    print("🚀 Starting EMA+ADX Multi-Coin Scanner...\n")
    print(f"🕒 Run start: {datetime.now(timezone.utc).isoformat()} UTC")
    print(f"📊 Monitoring {len(COINS)} coins...\n")

    total_found = 0

    for symbol in COINS:
        elapsed = time.time() - start_ts
        if elapsed >= (int(RUNTIME_LIMIT_MINUTES) * 60):
            print(f"⏱ Runtime limit reached ({elapsed:.1f}s) - stopping.")
            break

        if api_limit_reached():
            print(f"🛑 API call limit reached — stopping. API calls so far: {API_CALLS}")
            break

        print(f"🔍 Checking {symbol}...")
        try:
            signals = check_strategy(symbol)

            if not signals:
                print(f"😴 No new signals for {symbol}")
                continue

            for rec in signals:
                append_to_sheets_only(rec)
                total_found += 1
                print(f"☁️ Logged {rec['signal']} crossover for {symbol} @ {rec['price']}")

                if not COLLECTION_MODE:
                    append_journal(JOURNAL_FILE, rec)

        except Exception as e:
            log_error(f"main loop error on {symbol}: {repr(e)}")

    print(f"\n✅ Scan complete — {total_found} total signals logged.\n")

if __name__ == "__main__":
    main()
