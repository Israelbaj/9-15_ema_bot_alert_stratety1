"""
main.py
Single-run orchestrator:
 - loops over COINS once per execution
 - uses strategy.check_strategy to evaluate each
 - journals results (CSV)
 - sends Telegram alert for matches
 - includes startup test for Telegram + CSV logging
"""

from datetime import datetime, timezone
import time
import sys
from config import COINS, CHECK_INTERVAL, JOURNAL_FILE
from strategy import check_strategy
from utils import append_journal, log_error
from alert import send_telegram
import os


def format_alert(rec: dict) -> str:
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


def test_telegram_and_csv():
    """Send a test message to Telegram and test CSV writing."""
    print("🧪 Running startup tests...\n")

    # Telegram test
    test_msg = f"✅ TEST ALERT — Bot connectivity check at {datetime.now(timezone.utc).isoformat()} UTC"
    telegram_ok = send_telegram(test_msg)
    if telegram_ok:
        print("📨 Telegram test message sent successfully!")
    else:
        print("❌ Telegram test message FAILED — check token/chat ID or Secrets config.")
        log_error("Startup Telegram test failed.")

    # CSV test
    test_record = {
        "symbol": "TESTUSDT",
        "signal": "TEST",
        "price": 123.456,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "adx_ltf": 20,
        "ema_fast_ltf": 1.2345,
        "ema_slow_ltf": 1.2345,
        "ema_fast_htf": 1.2345,
        "ema_slow_htf": 1.2345,
        "ltf_trend_bias": "NEUTRAL",
        "htf_trend_bias": "NEUTRAL",
        "adx_strength": "TEST",
    }

    try:
        append_journal(JOURNAL_FILE, test_record)
        if os.path.exists(JOURNAL_FILE):
            print(f"🧾 CSV test succeeded — record appended to {JOURNAL_FILE}")
        else:
            print("⚠️ CSV file not found after write attempt.")
    except Exception as e:
        log_error(f"CSV write test failed: {repr(e)}")
        print(f"❌ CSV write test failed: {repr(e)}")

    print("\n✅ Startup tests complete.\n")


def main():
    print("🚀 EMA+ADX Multi-Coin Scanner (Single Run)")
    print(f"🧭 Tracking coins: {', '.join(COINS)}")
    print(f"🕒 Started at: {datetime.now(timezone.utc).isoformat()} UTC\n")
    sys.stdout.flush()

    # Run startup test
    test_telegram_and_csv()

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
