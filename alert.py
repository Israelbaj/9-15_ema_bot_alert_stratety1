"""
alert.py

Sends Telegram alerts using config values.
"""

import requests
from config import TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, REQUEST_TIMEOUT
from utils import log_error

def send_telegram(message: str) -> bool:
    """
    Send a message via Telegram bot.
    Returns True if send succeeded, False otherwise.
    """
    if not TELEGRAM_ENABLED:
        return False

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log_error("Telegram enabled but token/chat id not configured.")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            log_error(f"Telegram send failed ({resp.status_code}): {resp.text}")
            return False
        return True
    except Exception as e:
        log_error(f"Telegram exception: {repr(e)}")
        return False
