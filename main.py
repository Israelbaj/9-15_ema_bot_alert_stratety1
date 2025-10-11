"""
main.py
Single-run orchestrator:
 - loops over COINS once per execution
 - uses strategy.check_strategy to evaluate each
 - journals results (CSV)
 - sends Telegram alert for matches
 - runs startup.py test once before trading begins
"""

from datetime import datetime, timezone
import time
import sys
import os

from config import COINS, CHECK_INTERVAL, JOURNAL_FILE
from strategy import check_strategy
from utils import append_journal, log_error
from alert import send_telegram
from startup import run_startup_checks  # ✅ New import


def format_alert(rec: dict) -> str:
    """Formats alert message for Telegram."""
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
    print("🚀 EMA+ADX Multi-Coin Scanner (Single Run)")
    print(f"🧭 Tracking coins: {', '.join(COINS)}")
    print(f"🕒 Started at: {datetime.now(timezone.utc).isoformat()} UTC\n")
    sys.stdout.flush()

    # ✅ Run startup test once before anything else
    if not run_startup_checks():
        print("❌ Startup test failed — aborting execution.")
        sys.exit(1)

    cycle_start = time.time()

    for coin in COINS:
        try:
            print(f"🔍 Checking {coin} ...")
            sys.stdout.flush()

            rec = check_strategy(coin)

            if rec:
                append_journal(JOURNAL_FILE, rec)
                msg = format_alert(rec)
                ok = send_telegram(msg)

                if ok:
                    print(f"📩 Telegram alert sent for {coin} ({rec['signal']})")
                else:
                    log_error(f"Telegram failed for {coin} (signal={rec['signal']})")

                print(f"[{datetime.now(timezone.utc).isoformat()}] ✅ SIGNAL {coin} -> {rec['signal']}")
            else:
                print(f"⚪ No signal for {coin}")

            sys.stdout.flush()

        except Exception as e:
            log_error(f"Main loop error for {coin}: {repr(e)}")
            print(f"❌ Error while processing {coin}: {repr(e)}")

    elapsed = time.time() - cycle_start
    print(f"\n✅ Cycle completed in {elapsed:.2f}s — job finished.\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
