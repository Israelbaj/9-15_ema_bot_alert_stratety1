# strategy.py
from typing import List, Dict, Optional
import pandas as pd
import ta
from config import EMA_FAST, EMA_SLOW, ADX_LEN, ADX_THRESHOLD, HTF_FACTOR, LAST_SIGNALS_FILE
from utils import fetch_binance_klines, log_error, get_prev_signal, update_prev_signal
from datetime import datetime, timezone

# how many LTF candles to scan for historical crossovers
HIST_LOOKBACK = 300  # controlled by CANDLE_LIMIT too

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

def check_strategy(symbol: str) -> List[Dict]:
    """
    Returns list of records (one per crossover detected in the last HIST_LOOKBACK candles).
    Each record matches the HEADERS order used by sheets_logger.
    """
    recs: List[Dict] = []
    try:
        ltf = fetch_binance_klines(symbol, interval="15m", limit=HIST_LOOKBACK)
        htf = fetch_binance_klines(symbol, interval="1h", limit=HIST_LOOKBACK // 4)

        if ltf.empty:
            log_error(f"{symbol}: missing LTF data.")
            return recs

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

        if not htf.empty:
            htf = htf.reset_index(drop=True)
            htf["close"] = pd.to_numeric(htf["close"], errors="coerce")
            htf["ema_fast"] = _ema(htf["close"], EMA_FAST)
            htf["ema_slow"] = _ema(htf["close"], EMA_SLOW)

        # previous logged signal timestamp for this symbol (to avoid duplicate logging)
        prev = get_prev_signal(symbol)
        prev_ts = pd.to_datetime(prev.get("checked_at_utc")) if prev and prev.get("checked_at_utc") else None

        # iterate through the LTF series and find crossovers (from older to newer)
        for i in range(1, len(ltf)):
            try:
                prev_fast = float(ltf.loc[i-1, "ema_fast"])
                prev_slow = float(ltf.loc[i-1, "ema_slow"])
                curr_fast = float(ltf.loc[i, "ema_fast"])
                curr_slow = float(ltf.loc[i, "ema_slow"])
            except Exception:
                continue

            # detect crossover at index i (time = ltf.timestamp[i])
            cross_up = (prev_fast < prev_slow) and (curr_fast >= curr_slow)
            cross_down = (prev_fast > prev_slow) and (curr_fast <= curr_slow)
            if not (cross_up or cross_down):
                continue

            ts = pd.to_datetime(ltf.loc[i, "timestamp"])

            # skip if this crossover is at or before prev logged signal (avoid duplicates)
            if prev_ts is not None and ts <= prev_ts:
                continue

            # compute per-crossover metrics using values at candle i
            price = float(ltf.loc[i, "close"])
            ema_fast_ltf = curr_fast
            ema_slow_ltf = curr_slow

            adx_latest = float(adx_ser.iloc[i]) if i < len(adx_ser) else float("nan")
            adx_prev = float(adx_ser.iloc[i-1]) if i-1 < len(adx_ser) else float("nan")
            adx_slope = (adx_latest - adx_prev) if (not pd.isna(adx_latest) and not pd.isna(adx_prev)) else None

            rsi_latest = float(rsi_ser.iloc[i]) if i < len(rsi_ser) else float("nan")
            atr_latest = float(atr_ser.iloc[i]) if i < len(atr_ser) else float("nan")

            volume_latest = float(ltf.loc[i, "volume"])
            volume_ma_latest = float(vol_ma.iloc[i]) if i < len(vol_ma) else float("nan")
            volume_ratio = (volume_latest / volume_ma_latest) if (volume_ma_latest and volume_ma_latest > 0) else None

            # HTF snapshot (take latest HTF values if available)
            ema_fast_htf = float(htf["ema_fast"].iloc[-1]) if not htf.empty else None
            ema_slow_htf = float(htf["ema_slow"].iloc[-1]) if not htf.empty else None

            # slope percent (safe)
            try:
                ema_fast_slope = (ema_fast_ltf - prev_fast) / prev_fast * 100.0
            except Exception:
                ema_fast_slope = None
            try:
                ema_slow_slope = (ema_slow_ltf - prev_slow) / prev_slow * 100.0
            except Exception:
                ema_slow_slope = None

            # direction-aware factors
            if cross_up:
                ltf_factor = (ema_fast_ltf / ema_slow_ltf) if ema_slow_ltf != 0 else None
                signal_type = "LONG"
            else:
                ltf_factor = (ema_slow_ltf / ema_fast_ltf) if ema_fast_ltf != 0 else None
                signal_type = "SHORT"

            htf_factor = (ema_fast_htf / ema_slow_htf) if (ema_fast_htf is not None and ema_slow_htf not in (0, None)) else None

            ltf_trend_bias = "buy" if ema_fast_ltf > ema_slow_ltf else "sell"
            htf_trend_bias = "buy" if (ema_fast_htf is not None and ema_fast_htf > ema_slow_htf) else "sell"

            # build record (note: checked_at_utc uses the candle timestamp for reproducibility)
            rec = {
                "checked_at_utc": ts.isoformat(),
                "symbol": symbol,
                "signal": signal_type,
                "price": price,
                "ema_fast_ltf": round(ema_fast_ltf, 8),
                "ema_slow_ltf": round(ema_slow_ltf, 8),
                "ema_fast_slope": round(ema_fast_slope, 8) if ema_fast_slope is not None else "",
                "ema_slow_slope": round(ema_slow_slope, 8) if ema_slow_slope is not None else "",
                "adx_ltf": round(adx_latest, 6) if not pd.isna(adx_latest) else "",
                "adx_slope": round(adx_slope, 6) if adx_slope is not None else "",
                "rsi_ltf": round(rsi_latest, 6) if not pd.isna(rsi_latest) else "",
                "atr_ltf": round(atr_latest, 6) if not pd.isna(atr_latest) else "",
                "price_to_atr": round((price / atr_latest), 6) if (atr_latest and atr_latest > 0) else "",
                "volume_latest": round(volume_latest, 8),
                "volume_ma": round(volume_ma_latest, 8) if not pd.isna(volume_ma_latest) else "",
                "volume_ratio": round(volume_ratio, 6) if volume_ratio is not None else "",
                "ema_fast_htf": round(ema_fast_htf, 8) if ema_fast_htf is not None else "",
                "ema_slow_htf": round(ema_slow_htf, 8) if ema_slow_htf is not None else "",
                "ltf_trend_bias": ltf_trend_bias,
                "htf_trend_bias": htf_trend_bias,
                "ltf_factor": round(ltf_factor, 8) if ltf_factor is not None else "",
                "htf_factor": round(htf_factor, 8) if htf_factor is not None else "",
                "prev_signal": prev.get("signal") if prev else "",
                "signal_gap_hours": "",
                "best_opening_price": "",
                "max_movement_price": "",
                "trade_time_hrs": "",
                "pct_increase": "",
                "status": ""
            }

            recs.append(rec)

            # update prev signal to this crossover so further crossovers in the past not re-logged
            try:
                update_prev_signal(symbol, {"signal": rec["signal"], "checked_at_utc": rec["checked_at_utc"]})
            except Exception as e:
                log_error(f"update_prev_signal failed: {repr(e)}")

        return recs

    except Exception as e:
        log_error(f"check_strategy({symbol}) error: {repr(e)}")
        return recs

