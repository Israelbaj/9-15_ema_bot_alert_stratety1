"""
main.py

Orchestrator:
 - loops over COINS
 - uses strategy.check_strategy to evaluate each
 - journals results (CSV)
 - sends Telegram alert for matches
"""

import time
from config import COINS, CHECK_INTERVAL, JOURNAL_FILE
from strategy import check_strategy
from utils import append_journal, log_error
from alert import send_telegram
from datetime import datetime, timezone
import json

def format_alert(rec: dict) -> str:
    """Format a readable HTML message for Telegram from the rec dict."""
    s = rec["signal"]
    return (
        f"🔔 <b>{rec['symbol']}</b> — <b>{s}</b>\n"
        f"Time (UTC): {rec['checked_at_utc']}\n"
        f"Price: {rec['price']:.6f}\n"
        f"ADX (15m): {rec.get('adx_ltf')}\n"
        f"EMA 9/15 (15m): {rec.get('ema_fast_ltf'):.4f} / {rec.get('ema_slow_ltf'):.4f}\n"
        f"EMA 9/15 (1h): {rec.get('ema_fast_htf'):.4f} / {rec.get('ema_slow_htf'):.4f}\n"
        f"LTF bias / HTF bias: {rec.get('ltf_trend_bias')} / {rec.get('htf_trend_bias')}\n"
        f"ADX strength: {rec.get('adx_strength')}\n"
    )

def main():
    print("Starting EMA+ADX multi-coin scanner...")
    while True:
        cycle_start = time.time()
        for coin in COINS:
            try:
                rec = check_strategy(coin)
                if rec:
                    # Append to CSV (rich record)
                    append_journal(JOURNAL_FILE, rec)

                    # Send Telegram
                    msg = format_alert(rec)
                    ok = send_telegram(msg)
                    if not ok:
                        log_error(f"Telegram failed for {coin} (signal={rec['signal']})")

                    # print to console (compact JSON)
                    print(f"[{datetime.now(timezone.utc).isoformat()}] SIGNAL {coin} -> {rec['signal']}")
                    # optionally also show rec as JSON for immediate debugging
                    # print(json.dumps(rec, indent=2, default=str))

            except Exception as e:
                log_error(f"Main loop error for {coin}: {repr(e)}")

        # sleep until next cycle (approx)
        elapsed = time.time() - cycle_start
        to_sleep = max(0, CHECK_INTERVAL - elapsed)
        print(f"Cycle completed in {elapsed:.2f}s — sleeping {to_sleep:.1f}s\n")
        time.sleep(to_sleep)

if __name__ == "__main__":
    main()
