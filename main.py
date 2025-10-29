# main.py
import os
from datetime import datetime, timezone
from strategy import check_strategy
# from alert import send_telegram   # commented for collection mode (uncomment when re-enabling alerts)
from utils import append_journal, append_to_sheets_only, log_error
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
                # === Primary collection path (active) ===
                append_to_sheets_only(result)
                print(f"☁️ Appended {result['signal']} for {symbol} to Google Sheet")

                # === Local CSV (disabled during collection to avoid churn) ===
                # append_journal(JOURNAL_FILE, result)  # <-- uncomment to re-enable CSV journaling

                # === Telegram alert: keep code but commented for now ===
                # msg = f"📈 {symbol} - {result['signal']} @ {result['price']}"
                # send_telegram(msg)  # <-- uncomment to re-enable alerts

            else:
                print(f"😴 No valid signal for {symbol}")

        except Exception as e:
            log_error(f"main loop error on {symbol}: {repr(e)}")

    print("\n✅ Scan complete — results saved (if any).\n")

if __name__ == "__main__":
    main()
