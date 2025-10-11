"""
main.py
EMA+ADX Multi-Coin Scanner:
 - Evaluates strategy.py across configured COINS
 - Sends Telegram alerts on valid signals
 - Logs results to signals_journal.csv
"""

import os
from datetime import datetime, timezone
from strategy import check_strategy
from alert import send_telegram
from utils import append_journal, log_error
from config import COINS, JOURNAL_FILE

def main():
    print("🚀 Starting EMA+ADX Multi-Coin Scanner...\n")
    print(f"🕒 Run start: {datetime.now(timezone.utc).isoformat()} UTC")
    print(f"📊 Monitoring {len(COINS)} coins...\n")

    for symbol in COINS:
        print(f"🔍 Checking {symbol}...")
        try:
            result = check_strategy(symbol)

            if result:
                # Append to CSV
                append_journal(JOURNAL_FILE, result)
                print(f"✅ Logged {result['signal']} signal for {symbol}")

                # Send Telegram alert
                msg = (
                    f"📈 <b>{symbol}</b> — <b>{result['signal']}</b> Signal\n"
                    f"💰 Price: {result['price']}\n"
                    f"ADX: {result['adx_ltf']:.2f}\n"
                    f"LTF Trend: {'Bullish' if result['ltf_trend_bias'] > 0 else 'Bearish'}\n"
                    f"HTF Trend: {'Bullish' if result['htf_trend_bias'] > 0 else 'Bearish'}\n"
                    f"🕒 {result['checked_at_utc']}"
                )
                send_telegram(msg)

            else:
                print(f"😴 No valid signal for {symbol}")

        except Exception as e:
            log_error(f"main loop error on {symbol}: {repr(e)}")

    print("\n✅ Scan complete — results saved (if any).\n")


if __name__ == "__main__":
    main()
