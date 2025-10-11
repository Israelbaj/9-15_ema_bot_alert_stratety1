"""
startup.py
Runs system readiness checks before trading begins:
 - Verifies Telegram bot connectivity
 - Tests CSV journal accessibility
 - Logs and reports results
"""

import os
import csv
import sys
from datetime import datetime, timezone
from alert import send_telegram
from utils import append_journal, log_error
from config import JOURNAL_FILE


def test_telegram():
    """Test Telegram connectivity."""
    print("🧪 Testing Telegram bot connection...")
    test_message = f"✅ Startup Check: Telegram connected at {datetime.now(timezone.utc).isoformat()} UTC"
    try:
        ok = send_telegram(test_message)
        if ok:
            print("📨 Telegram test passed.")
            return True
        else:
            print("❌ Telegram test failed — no confirmation received.")
            log_error("Startup Telegram test failed.")
            return False
    except Exception as e:
        log_error(f"Telegram startup test error: {repr(e)}")
        print(f"❌ Telegram test error: {repr(e)}")
        return False


def test_csv():
    """Test if CSV journaling is writable."""
    print("🧪 Testing CSV journaling...")
    test_record = {
        "symbol": "STARTUPTEST",
        "signal": "TEST",
        "price": 0.0000,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "adx_ltf": 0,
        "ema_fast_ltf": 0.0000,
        "ema_slow_ltf": 0.0000,
        "ema_fast_htf": 0.0000,
        "ema_slow_htf": 0.0000,
        "ltf_trend_bias": "NEUTRAL",
        "htf_trend_bias": "NEUTRAL",
        "adx_strength": "NONE",
    }

    try:
        append_journal(JOURNAL_FILE, test_record)
        if os.path.exists(JOURNAL_FILE):
            print(f"🧾 CSV test passed — {JOURNAL_FILE} accessible.")
            return True
        else:
            print("⚠️ CSV file not found after write attempt.")
            return False
    except Exception as e:
        log_error(f"CSV startup test error: {repr(e)}")
        print(f"❌ CSV test failed: {repr(e)}")
        return False


def run_startup_checks():
    """Run both Telegram and CSV checks before strategy execution."""
    print("\n🚀 Running startup system checks...\n")

    telegram_ok = test_telegram()
    csv_ok = test_csv()

    if telegram_ok and csv_ok:
        send_telegram("🚀 Startup complete: All systems operational.")
        print("\n✅ All startup checks passed — system ready.\n")
        return True
    else:
        send_telegram("❌ Startup failed: check Telegram or CSV configuration.")
        print("\n⚠️ Startup check failed — see logs for details.\n")
        return False


if __name__ == "__main__":
    success = run_startup_checks()
    if not success:
        sys.exit(1)
