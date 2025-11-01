# strategy.py
from typing import Optional, Dict, List
import pandas as pd
import ta
from config import EMA_FAST, EMA_SLOW, ADX_LEN, ADX_THRESHOLD, HTF_FACTOR, CANDLE_LIMIT
from utils import fetch_binance_klines, log_error, get_prev_signal, update_prev_signal
from datetime import datetime, timezone

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def _adx_series(df: pd.DataFrame, length: int) -> pd.Series:
    try:
        adx_ind = ta.trend.ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=length, fillna=True)
        return adx_ind.adx()
    except Exception as e:
        log_error(f"_adx_series error: {e}")
        return pd.Series([float("nan")] * len(df), index=df.index if not df.empty else pd.RangeIndex(0))

def _rsi_series(df: pd.DataFrame, length: int = 14) -> pd.Series:
    try:
        rsi_ind = ta.momentum.RSIIndicator(close=df["close"], window=length, fillna=True)
        return rsi_ind.rsi()
    except Exception as e:
        log_error(f"_rsi_series error: {e}")
        return pd.Series([float("nan")] * len(df), index=df.index if not df.empty else pd.RangeIndex(0))

def _atr_series(df: pd.DataFrame, length: int = 14) -> pd.Series:
    try:
        atr = ta.volatility.AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=length, fillna=True)
        return atr.average_true_range()
    except Exception as e:
        log_error(f"_atr_series error: {e}")
        return pd.Series([float("nan")] * len(df), index=df.index if not df.empty else pd.RangeIndex(0))

def check_strategy(symbol: str) -> Optional[Dict]:
    """
    Return a single signal record for the latest crossover if conditions match.
    This function fetches up to CANDLE_LIMIT candles (15m) and 1h HTF (also limited).
    """
    try:
        ltf = fetch_binance_klines(symbol, interval="15m", limit=int(CANDLE_LIMIT))
        htf = fetch_binance_klines(symbol, interval="1h", limit=200)

        if ltf.empty or htf.empty:
            log_error(f"{symbol}: missing LTF/HTF data (ltf_empty={ltf.empty}, htf_empty={htf.empty})")
            return None

        # prepare LTF
        ltf = ltf.reset_index(drop=True)
        ltf["close"] = pd.to_numeric(ltf["close"], errors="coerce")
        ltf["high"] = pd.to_numeric(ltf["high"], errors="coerce")
        ltf["low"] = pd.to_numeric(ltf["low"], errors="coerce")
        ltf["volume"] = pd.to_numeric(ltf["volume"], errors="coerce")

        ltf["ema_fast"] = _ema(ltf["close"], EMA_FAST)
        ltf["ema_slow"] = _ema(ltf["close"], EMA_SLOW)
        adx_ser = _adx_series(ltf, ADX_LEN)
        rsi_ser = _rsi_series(ltf, 14)
        atr_ser = _atr_series(ltf, 14)

        vol_ma = ltf["volume"].rolling(20, min_periods=1).mean()

        # HTF computations
        htf = htf.reset_index(drop=True)
        htf["close"] = pd.to_numeric(htf["close"], errors="coerce")
        htf["ema_fast"] = _ema(htf["close"], EMA_FAST)
        htf["ema_slow"] = _ema(htf["close"], EMA_SLOW)

        if len(ltf) < 2 or len(htf) < 1:
            log_error(f"{symbol}: not enough rows (ltf={len(ltf)}, htf={len(htf)})")
            return None

        # latest values
        price = float(ltf["close"].iloc[-1])
        ema_fast_ltf = float(ltf["ema_fast"].iloc[-1])
        ema_slow_ltf = float(ltf["ema_slow"].iloc[-1])
        ema_fast_ltf_prev = float(ltf["ema_fast"].iloc[-2])
        ema_slow_ltf_prev = float(ltf["ema_slow"].iloc[-2])

        adx_latest = float(adx_ser.iloc[-1]) if not adx_ser.empty else float("nan")
        adx_prev = float(adx_ser.iloc[-2]) if len(adx_ser) >= 2 else float("nan")
        adx_slope = (adx_latest - adx_prev) if (not pd.isna(adx_latest) and not pd.isna(adx_prev)) else None

        rsi_latest = float(rsi_ser.iloc[-1]) if not rsi_ser.empty else float("nan")
        atr_latest = float(atr_ser.iloc[-1]) if not atr_ser.empty else float("nan")

        volume_latest = float(ltf["volume"].iloc[-1])
        volume_ma_latest = float(vol_ma.iloc[-1]) if not vol_ma.empty else float("nan")
        volume_ratio = (volume_latest / volume_ma_latest) if (volume_ma_latest and volume_ma_latest > 0) else None

        # HTF latest
        ema_fast_htf = float(htf["ema_fast"].iloc[-1])
        ema_slow_htf = float(htf["ema_slow"].iloc[-1])

        # cross detection (last candle only)
        ltf_cross_up = (ema_fast_ltf_prev < ema_slow_ltf_prev) and (ema_fast_ltf >= ema_slow_ltf)
        ltf_cross_down = (ema_fast_ltf_prev > ema_slow_ltf_prev) and (ema_fast_ltf <= ema_slow_ltf)

        adx_ok = (not pd.isna(adx_latest)) and (adx_latest >= ADX_THRESHOLD)
        htf_long_ok = ema_fast_htf >= HTF_FACTOR * ema_slow_htf
        htf_short_ok = ema_slow_htf >= HTF_FACTOR * ema_fast_htf

        long_condition = ltf_cross_up and adx_ok and htf_long_ok
        short_condition = ltf_cross_down and adx_ok and htf_short_ok

        if not (long_condition or short_condition):
            return None

        # slopes percent
        try:
            ema_fast_slope = (ema_fast_ltf - ema_fast_ltf_prev) / ema_fast_ltf_prev * 100.0
        except Exception:
            ema_fast_slope = None
        try:
            ema_slow_slope = (ema_slow_ltf - ema_slow_ltf_prev) / ema_slow_ltf_prev * 100.0
        except Exception:
            ema_slow_slope = None

        if long_condition:
            ltf_factor = (ema_fast_ltf / ema_slow_ltf) if ema_slow_ltf != 0 else None
        else:
            ltf_factor = (ema_slow_ltf / ema_fast_ltf) if ema_fast_ltf != 0 else None

        htf_factor = (ema_fast_htf / ema_slow_htf) if ema_slow_htf != 0 else None

        ltf_trend_bias = "buy" if ema_fast_ltf > ema_slow_ltf else "sell"
        htf_trend_bias = "buy" if ema_fast_htf > ema_slow_htf else "sell"

        prev = get_prev_signal(symbol)
        prev_signal_type = prev.get("signal") if prev else None
        prev_time = prev.get("checked_at_utc") if prev else None
        signal_gap_hours = None
        if prev_time:
            try:
                prev_ts = pd.to_datetime(prev_time)
                now_ts = pd.Timestamp.utcnow()
                delta = now_ts - prev_ts
                signal_gap_hours = delta.total_seconds() / 3600.0
            except Exception:
                signal_gap_hours = None

        rec = {
            "checked_at_utc": pd.Timestamp.utcnow().isoformat(),
            "symbol": symbol,
            "signal": "LONG" if long_condition else "SHORT",
            "price": price,

            "ema_fast_ltf": ema_fast_ltf,
            "ema_slow_ltf": ema_slow_ltf,
            "ema_fast_slope": ema_fast_slope,
            "ema_slow_slope": ema_slow_slope,

            "adx_ltf": adx_latest,
            "adx_slope": adx_slope,

            "rsi_ltf": rsi_latest,
            "atr_ltf": atr_latest,
            "price_to_atr": (price / atr_latest) if (atr_latest and atr_latest > 0) else None,

            "volume_latest": volume_latest,
            "volume_ma": volume_ma_latest,
            "volume_ratio": volume_ratio,

            "ema_fast_htf": ema_fast_htf,
            "ema_slow_htf": ema_slow_htf,

            "ltf_trend_bias": ltf_trend_bias,
            "htf_trend_bias": htf_trend_bias,

            "ltf_factor": ltf_factor,
            "htf_factor": htf_factor,

            "prev_signal": prev_signal_type,
            "signal_gap_hours": signal_gap_hours
        }

        # update local prev-signal cache (so next run can compute gap)
        try:
            update_prev_signal(symbol, {"signal": rec["signal"], "checked_at_utc": rec["checked_at_utc"]})
        except Exception as e:
            log_error(f"update_prev_signal failed: {repr(e)}")

        return rec

    except Exception as e:
        log_error(f"check_strategy({symbol}) error: {repr(e)}")
        return None

