from typing import List, Dict
import pandas as pd
import ta
from datetime import datetime, timezone
from config import EMA_FAST, EMA_SLOW, ADX_LEN, ADX_THRESHOLD, HTF_FACTOR
from utils import fetch_binance_klines, log_error

def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()

def _adx_series(df: pd.DataFrame, length: int) -> pd.Series:
    try:
        adx = ta.trend.ADXIndicator(high=df["high"], low=df["low"], close=df["close"], window=length, fillna=True)
        return adx.adx()
    except Exception as e:
        log_error(f"_adx_series error: {e}")
        return pd.Series([float("nan")] * len(df))

def _rsi_series(df: pd.DataFrame, length: int = 14) -> pd.Series:
    try:
        rsi = ta.momentum.RSIIndicator(close=df["close"], window=length, fillna=True)
        return rsi.rsi()
    except Exception as e:
        log_error(f"_rsi_series error: {e}")
        return pd.Series([float("nan")] * len(df))

def _atr_series(df: pd.DataFrame, length: int = 14) -> pd.Series:
    try:
        atr = ta.volatility.AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=length, fillna=True)
        return atr.average_true_range()
    except Exception as e:
        log_error(f"_atr_series error: {e}")
        return pd.Series([float("nan")] * len(df))

def check_strategy(symbol: str) -> List[Dict]:
    """Return all EMA crossover events (LONG/SHORT) from the last ~300 candles."""
    try:
        ltf = fetch_binance_klines(symbol, interval="15m", limit=300)
        htf = fetch_binance_klines(symbol, interval="1h", limit=300)

        if ltf.empty or htf.empty:
            log_error(f"{symbol}: missing LTF/HTF data")
            return []

        # Prepare LTF
        ltf = ltf.reset_index(drop=True)
        for col in ["close", "high", "low", "volume"]:
            ltf[col] = pd.to_numeric(ltf[col], errors="coerce")

        ltf["ema_fast"] = _ema(ltf["close"], EMA_FAST)
        ltf["ema_slow"] = _ema(ltf["close"], EMA_SLOW)
        ltf["adx"] = _adx_series(ltf, ADX_LEN)
        ltf["rsi"] = _rsi_series(ltf)
        ltf["atr"] = _atr_series(ltf)
        ltf["vol_ma"] = ltf["volume"].rolling(20, min_periods=1).mean()

        # Prepare HTF
        htf = htf.reset_index(drop=True)
        htf["ema_fast"] = _ema(htf["close"], EMA_FAST)
        htf["ema_slow"] = _ema(htf["close"], EMA_SLOW)

        results = []

        # Loop through each candle and detect crossovers
        for i in range(1, len(ltf)):
            ema_fast_prev, ema_slow_prev = ltf["ema_fast"].iloc[i - 1], ltf["ema_slow"].iloc[i - 1]
            ema_fast_now, ema_slow_now = ltf["ema_fast"].iloc[i], ltf["ema_slow"].iloc[i]

            cross_up = (ema_fast_prev < ema_slow_prev) and (ema_fast_now >= ema_slow_now)
            cross_down = (ema_fast_prev > ema_slow_prev) and (ema_fast_now <= ema_slow_now)

            if not (cross_up or cross_down):
                continue

            # relaxed filtering for collection mode
            adx_latest = float(ltf["adx"].iloc[i])
            if pd.isna(adx_latest) or adx_latest < ADX_THRESHOLD:
                continue

            # HTF trend bias
            htf_latest = htf.iloc[min(int(i / 4), len(htf) - 1)]
            ema_fast_htf, ema_slow_htf = htf_latest["ema_fast"], htf_latest["ema_slow"]

            long_cond = cross_up and (ema_fast_htf > ema_slow_htf)
            short_cond = cross_down and (ema_fast_htf < ema_slow_htf)

            if not (long_cond or short_cond):
                continue

            rec = {
                "checked_at_utc": pd.Timestamp.utcnow().isoformat(),
                "symbol": symbol,
                "signal": "LONG" if long_cond else "SHORT",
                "price": float(ltf["close"].iloc[i]),
                "ema_fast_ltf": float(ema_fast_now),
                "ema_slow_ltf": float(ema_slow_now),
                "adx_ltf": adx_latest,
                "rsi_ltf": float(ltf["rsi"].iloc[i]),
                "atr_ltf": float(ltf["atr"].iloc[i]),
                "volume_latest": float(ltf["volume"].iloc[i]),
                "volume_ma": float(ltf["vol_ma"].iloc[i]),
                "ema_fast_htf": float(ema_fast_htf),
                "ema_slow_htf": float(ema_slow_htf),
                "ltf_trend_bias": "buy" if ema_fast_now > ema_slow_now else "sell",
                "htf_trend_bias": "buy" if ema_fast_htf > ema_slow_htf else "sell",
                "ltf_factor": (ema_fast_now / ema_slow_now) if ema_slow_now else None,
                "htf_factor": (ema_fast_htf / ema_slow_htf) if ema_slow_htf else None,
                "candle_time": str(ltf["open_time"].iloc[i]) if "open_time" in ltf.columns else None
            }

            results.append(rec)

        return results

    except Exception as e:
        log_error(f"check_strategy({symbol}) error: {repr(e)}")
        return []
