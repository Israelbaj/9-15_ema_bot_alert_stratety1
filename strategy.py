"""
strategy.py

Implements the simplified Pine logic in Python:
 - 15m EMA(9,15) & ADX(14) on LTF
 - 1h EMA(9,15) HTF alignment with HTF_FACTOR
 - Signals: LONG_POSSIBLE / SHORT_POSSIBLE / None
 - Returns full context for journaling
"""

from typing import Optional, Dict
import pandas as pd
import ta
from config import EMA_FAST, EMA_SLOW, ADX_LEN, ADX_THRESHOLD, HTF_FACTOR
from utils import fetch_binance_klines, log_error

def _ema(series: pd.Series, span: int) -> pd.Series:
    """EMA via pandas (transparent, easy to inspect)."""
    return series.ewm(span=span, adjust=False).mean()

def _adx_series(df: pd.DataFrame, length: int) -> pd.Series:
    """Return ADX series using ta (requires high, low, close)."""
    try:
        adx_ind = ta.trend.ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=length, fillna=True)
        return adx_ind.adx()
    except Exception as e:
        log_error(f"_adx_series error: {e}")
        return pd.Series([float("nan")] * len(df), index=df.index if not df.empty else pd.RangeIndex(0))


def check_strategy(symbol: str) -> Optional[Dict]:
    """
    Evaluate strategy for one symbol.
    If conditions satisfied, returns a detailed dict (for journal & alert).
    If no signal -> returns None.
    """

    try:
        # --- fetch data ---
        ltf = fetch_binance_klines(symbol, interval="15m", limit=200)
        htf = fetch_binance_klines(symbol, interval="1h", limit=200)

        # Basic validation
        if ltf.empty or htf.empty:
            log_error(f"{symbol}: missing LTF/HTF data (ltf_empty={ltf.empty}, htf_empty={htf.empty})")
            return None

        # compute EMAs on LTF
        ltf = ltf.reset_index(drop=True)
        ltf["ema_fast"] = _ema(ltf["close"], EMA_FAST)
        ltf["ema_slow"] = _ema(ltf["close"], EMA_SLOW)

        # compute ADX on LTF (full series)
        adx_ser = _adx_series(ltf, ADX_LEN)

        # compute EMAs on HTF
        htf = htf.reset_index(drop=True)
        htf["ema_fast"] = _ema(htf["close"], EMA_FAST)
        htf["ema_slow"] = _ema(htf["close"], EMA_SLOW)

        # Ensure enough rows for previous values
        if len(ltf) < 2 or len(htf) < 1:
            log_error(f"{symbol}: not enough rows (ltf={len(ltf)}, htf={len(htf)})")
            return None

        # latest LTF values
        price = float(ltf["close"].iloc[-1])
        ema_fast_ltf = float(ltf["ema_fast"].iloc[-1])
        ema_slow_ltf = float(ltf["ema_slow"].iloc[-1])
        ema_fast_ltf_prev = float(ltf["ema_fast"].iloc[-2])
        ema_slow_ltf_prev = float(ltf["ema_slow"].iloc[-2])

        # LTF ADX latest & prev
        adx_latest = float(adx_ser.iloc[-1]) if not adx_ser.empty else float("nan")
        adx_prev = float(adx_ser.iloc[-2]) if len(adx_ser) >= 2 else float("nan")
        adx_delta = adx_latest - adx_prev if (not pd.isna(adx_latest) and not pd.isna(adx_prev)) else None

        # HTF latest values
        ema_fast_htf = float(htf["ema_fast"].iloc[-1])
        ema_slow_htf = float(htf["ema_slow"].iloc[-1])
        # try to get previous HTF EMA if available (useful to measure HTF slope)
        ema_fast_htf_prev = float(htf["ema_fast"].iloc[-2]) if len(htf) >= 2 else None
        ema_slow_htf_prev = float(htf["ema_slow"].iloc[-2]) if len(htf) >= 2 else None

        # LTF cross detection (ta.crossover/ta.crossunder equivalent)
        ltf_cross_up = (ema_fast_ltf_prev < ema_slow_ltf_prev) and (ema_fast_ltf >= ema_slow_ltf)
        ltf_cross_down = (ema_fast_ltf_prev > ema_slow_ltf_prev) and (ema_fast_ltf <= ema_slow_ltf)

        # ADX pass (lagging classic)
        adx_ok = (not pd.isna(adx_latest)) and (adx_latest >= ADX_THRESHOLD)

        # HTF alignment checks (match your Pine)
        htf_long_ok = ema_fast_htf >= HTF_FACTOR * ema_slow_htf
        htf_short_ok = ema_slow_htf >= HTF_FACTOR * ema_fast_htf

        # final conditions (exact mapping to Pine)
        long_condition = ltf_cross_up and adx_ok and htf_long_ok
        short_condition = ltf_cross_down and adx_ok and htf_short_ok

        if not (long_condition or short_condition):
            # nothing to report
            return None

        # Create enriched record for journaling & alerts
        rec = {
            "checked_at_utc": pd.Timestamp.utcnow().isoformat(),
            "symbol": symbol,
            "signal": "LONG" if long_condition else "SHORT",
            "price": price,

            # LTF indicators
            "ema_fast_ltf": ema_fast_ltf,
            "ema_slow_ltf": ema_slow_ltf,
            "ema_fast_ltf_prev": ema_fast_ltf_prev,
            "ema_slow_ltf_prev": ema_slow_ltf_prev,
            "ema_fast_ltf_delta": ema_fast_ltf - ema_fast_ltf_prev,
            "ema_slow_ltf_delta": ema_slow_ltf - ema_slow_ltf_prev,
            "adx_ltf": adx_latest,
            "adx_ltf_prev": (adx_prev if not pd.isna(adx_prev) else None),
            "adx_delta": (adx_delta if adx_delta is not None else None),

            # HTF indicators
            "ema_fast_htf": ema_fast_htf,
            "ema_slow_htf": ema_slow_htf,
            "ema_fast_htf_prev": ema_fast_htf_prev,
            "ema_slow_htf_prev": ema_slow_htf_prev,

            # biases and meta
            "ltf_trend_bias": (1 if ema_fast_ltf > ema_slow_ltf else -1),
            "htf_trend_bias": (1 if ema_fast_htf > ema_slow_htf else -1),
            "adx_strength": ("Strong" if adx_ok else "Weak"),

            # strategy params to store
            "ema_fast_len": EMA_FAST,
            "ema_slow_len": EMA_SLOW,
            "adx_len": ADX_LEN,
            "adx_threshold": ADX_THRESHOLD,
            "htf_factor": HTF_FACTOR
        }

        return rec

    except Exception as e:
        log_error(f"check_strategy({symbol}) error: {repr(e)}")
        return None
