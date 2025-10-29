"""
main.py
Collects live EMA(9/15) crossover data + RSI + Volume for journaling.
Currently:
 - ADX relaxed (threshold = 0)
 - HTF factor = 0.1
 - No alerts or CSV logging (commented for later)
 - Writes directly to Google Sheets
"""

import pandas as pd
import ta
from config import EMA_FAST, EMA_SLOW, ADX_LEN, ADX_THRESHOLD, HTF_FACTOR
from utils import fetch_binance_klines, log_error
from sheets_logger import append_row
# from telegram_bot import send_telegram_alert  # 🚫 Commented out (for later)
# from csv_logger import write_signal_csv        # 🚫 Commented out (for later)

# --------------------------------------------------
# --- Helper functions ---
# --------------------------------------------------

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def _adx_series(df: pd.DataFrame, length: int) -> pd.Series:
    try:
        adx = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=length, fillna=True)
        return adx.adx()
    except Exception as e:
        log_error(f"_adx_series error: {e}")
        return pd.Series([float("nan")] * len(df), index=df.index)

def _rsi_series(df: pd.DataFrame, length: int = 14) -> pd.Series:
    try:
        rsi = ta.momentum.RSIIndicator(df["close"], window=length, fillna=True)
        return rsi.rsi()
    except Exception as e:
        log_error(f"_rsi_series error: {e}")
        return pd.Series([float("nan")] * len(df), index=df.index)

# --------------------------------------------------
# --- Strategy core ---
# --------------------------------------------------

def check_strategy(symbol: str):
    try:
        # fetch 15m (ltf) and 1h (htf) data
        ltf = fetch_binance_klines(symbol, interval="15m", limit=200)
        htf = fetch_binance_klines(symbol, interval="1h", limit=200)

        if ltf.empty or htf.empty:
            log_error(f"{symbol}: missing data")
            return None

        ltf = ltf.reset_index(drop=True)
        htf = htf.reset_index(drop=True)

        # compute EMAs
        ltf["ema_fast"] = _ema(ltf["close"], EMA_FAST)
        ltf["ema_slow"] = _ema(ltf["close"], EMA_SLOW)
        htf["ema_fast"] = _ema(htf["close"], EMA_FAST)
        htf["ema_slow"] = _ema(htf["close"], EMA_SLOW)

        # ADX, RSI, volume
        ltf["adx"] = _adx_series(ltf, ADX_LEN)
        ltf["rsi"] = _rsi_series(ltf)
        ltf["volume"] = ltf["volume"]

        # detect crossover
        ema_fast_ltf = ltf["ema_fast"].iloc[-1]
        ema_slow_ltf = ltf["ema_slow"].iloc[-1]
        ema_fast_prev = ltf["ema_fast"].iloc[-2]
        ema_slow_prev = ltf["ema_slow"].iloc[-2]

        ltf_cross_up = (ema_fast_prev < ema_slow_prev) and (ema_fast_ltf >= ema_slow_ltf)
        ltf_cross_down = (ema_fast_prev > ema_slow_prev) and (ema_fast_ltf <= ema_slow_ltf)

        # HTF alignment
        ema_fast_htf = htf["ema_fast"].iloc[-1]
        ema_slow_htf = htf["ema_slow"].iloc[-1]
        htf_long_ok = ema_fast_htf >= HTF_FACTOR * ema_slow_htf
        htf_short_ok = ema_slow_htf >= HTF_FACTOR * ema_fast_htf

        adx_latest = ltf["adx"].iloc[-1]
        price = float(ltf["close"].iloc[-1])

        # conditions
        long_condition = ltf_cross_up and htf_long_ok
        short_condition = ltf_cross_down and htf_short_ok
        if not (long_condition or short_condition):
            return None

        # compute factors (direction-sensitive)
        if long_condition:
            ltf_factor = ema_fast_ltf / ema_slow_ltf
            htf_factor = ema_fast_htf / ema_slow_htf
        else:
            ltf_factor = ema_slow_ltf / em_

