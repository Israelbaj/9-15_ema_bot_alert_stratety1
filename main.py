# main.py (unchanged logic, just kept here for completeness)
import os
from datetime import datetime, timezone
from strategy import check_strategy
# from alert import send_telegram   # commented for collection mode
from utils import append_to_sheets_only, log_error
from config import COINS, JOURNAL_FILE, COLLECTION_MODE

def main():
    print("🚀 Starting EMA+ADX Multi-Coin Scanner...\n")
    print(f"🕒 Run start: {datetime.now(timezone.utc).isoformat()} UTC")
    print(f"📊 Monitoring {len(COINS)} coins...\n")

    for symbol in COINS:
        print(f"🔍 Checking {symbol}...")
        try:
            result = check_strategy(symbol)

            if result:
                append_to_sheets_only(result)
                print(f"☁️ Appended {result['signal']} for {symbol} to Google Sheet")
                # append_journal(JOURNAL_FILE, result)  # CSV disabled in collection mode
                # send_telegram(msg)  # Telegram disabled in collection mode
            else:
                print(f"😴 No valid signal for {symbol}")

        except Exception as e:
            log_error(f"main loop error on {symbol}: {repr(e)}")

    print("\n✅ Scan complete — results saved (if any).\n")

if __name__ == "__main__":
    main()

