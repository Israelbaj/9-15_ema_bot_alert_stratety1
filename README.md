# EMA+ADX Multi-Coin Telegram Bot

## Description
This bot monitors multiple cryptocurrencies (BTC, ETH, SOL, XRP, DOGE) on Binance using a dual-timeframe EMA+ADX strategy and sends Telegram alerts when trade conditions are met.

## Strategy Logic
- 15-min chart for trade signals
- 1-hour chart for trend alignment
- Entry when:
  - 9 EMA crosses 15 EMA (LTF)
  - ADX ≥ 18
  - 1H EMA alignment confirms trend direction

## Files
- **main.py** — main loop, journaling, alerts
- **config.py** — parameters and settings
- **strategy.py** — EMA/ADX logic
- **utils.py** — data fetch + indicator math
- **alert.py** — Telegram notification logic

## Run
