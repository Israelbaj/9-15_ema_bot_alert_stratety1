# EMA+ADX Multi-Coin Scanner — Safe-Run Collection Mode

## What it does
- Detects 9/15 EMA crossovers on 15m LTF, collects lots of metrics (ADX, RSI, ATR, volume, HTF EMAs).
- Appends signals to a canonical Google Sheet and then runs post-analysis to compute trade metrics (best open price, max movement, trade_time, pct_increase).
- Safe-run design: enforces Binance API call limits and Google Sheets quota; saves run-state and exits gracefully when approaching limits.

## Quick setup
- Add `GOOGLE_SERVICE_ACCOUNT_JSON` and `GOOGLE_SHEET_ID` to repo secrets.
- Optionally set `COINS` secret (comma-separated), otherwise defaults used.
- Set `RUNTIME_LIMIT_MINUTES`, `API_CALL_LIMIT`, `CANDLE_LIMIT` in workflow env as needed.

## Re-enable alerts / CSV
- In `main.py` uncomment `send_telegram` lines and call to `append_journal(...)` as desired.

## Note on quotas
- Google Sheets has hard read/write quotas. This workflow reduces reads/writes and batches them but may still hit quotas if you append many rows in a single run.
