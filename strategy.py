# strategy.py
from typing import Optional, Dict, List
import pandas as pd
import ta
from config import EMA_FAST, EMA_SLOW, ADX_LEN, ADX_THRESHOLD, HTF_FACTOR
from config import LAST_SIGNALS_FILE
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

def _find_crossovers(ema_fast: pd.Series, ema_slow: pd.Series) -> List[int]:
    """
    Return list of indices where a crossover occurs (index corresponds to ema series index).
    We detect cross up when fast crosses from below to >= slow, cross down when fast crosses from above to <= slow.
    """
    idxs = []
    # require at least 2 points
    for i in range(1, len(ema_fast)):
        prev_fast = ema_fast.iloc[i-1]
        prev_slow = ema_slow.iloc[i-1]
        cur_fast = ema_fast.iloc[i]
        cur_slow = ema_slow.iloc[i]
        if pd.isna(prev_fast) or pd.isna(prev_slow) or pd.isna(cur_fast) or pd.isna(cur_slow):
            continue
        if (prev_fast < prev_slow) and (cur_fast >= cur_slow):
            idxs.append(i)
        elif (prev_fast > prev_slow) and (cur_fast <= cur_slow):
            idxs.append(i)
    return idxs

def check_strategy(symbol: str) -> Optional[List[Dict]]:
    """
    Return list of signal records (possibly multiple crossovers within lookback window).
    Each record is a dict aligned to HEADERS.
    """
    try:
        ltf = fetch_binance_klines(symbol, interval="15m", limit=300)
        htf = fetch_binance_klines(symbol, interval="1h", limit=300)

        if ltf.empty or htf.empty:
            log_error(f"{symbol}: missing LTF/HTF data (ltf_empty={ltf.empty}, htf_empty={htf.empty})")
            return None

        ltf = ltf.reset_index(drop=True)
        for c in ["close", "high", "low", "volume"]:
            ltf[c] = pd.to_numeric(ltf[c], errors="coerce")

        ltf["ema_fast"] = _ema(ltf["close"], EMA_FAST)
        ltf["ema_slow"] = _ema(ltf["close"], EMA_SLOW)
        adx_ser = _adx_series(ltf, ADX_LEN)
        rsi_ser = _rsi_series(ltf, 14)
        atr_ser = _atr_series(ltf, 14)
        vol_ma = ltf["volume"].rolling(20, min_periods=1).mean()

        htf = htf.reset_index(drop=True)
        htf["close"] = pd.to_numeric(htf["close"], errors="coerce")
        htf["ema_fast"] = _ema(htf["close"], EMA_FAST)
        htf["ema_slow"] = _ema(htf["close"], EMA_SLOW)

        # find all crossovers on LTF
        cross_idx = _find_crossovers(ltf["ema_fast"], ltf["ema_slow"])
        if not cross_idx:
            return None

        results = []
        for i in cross_idx:
            # compute values at index i (the crossover candle)
            price = float(ltf["close"].iloc[i])
            ema_fast_ltf = float(ltf["ema_fast"].iloc[i])
            ema_slow_ltf = float(ltf["ema_slow"].iloc[i])
            # previous EMAs (for slope)
            ema_fast_ltf_prev = float(ltf["ema_fast"].iloc[i-1]) if i-1 >= 0 else None
            ema_slow_ltf_prev = float(ltf["ema_slow"].iloc[i-1]) if i-1 >= 0 else None

            adx_latest = float(adx_ser.iloc[i]) if not adx_ser.empty and i < len(adx_ser) else float("nan")
            adx_prev = float(adx_ser.iloc[i-1]) if i-1 >= 0 and i-1 < len(adx_ser) else float("nan")
            adx_slope = (adx_latest - adx_prev) if (not pd.isna(adx_latest) and not pd.isna(adx_prev)) else None

            rsi_latest = float(rsi_ser.iloc[i]) if not rsi_ser.empty and i < len(rsi_ser) else float("nan")
            atr_latest = float(atr_ser.iloc[i]) if not atr_ser.empty and i < len(atr_ser) else float("nan")

            volume_latest = float(ltf["volume"].iloc[i])
            volume_ma_latest = float(vol_ma.iloc[i]) if not vol_ma.empty and i < len(vol_ma) else float("nan")
            volume_ratio = (volume_latest / volume_ma_latest) if (volume_ma_latest and volume_ma_latest > 0) else None

            # Use HTF latest values (we can use last HTF row)
            ema_fast_htf = float(htf["ema_fast"].iloc[-1])
            ema_slow_htf = float(htf["ema_slow"].iloc[-1])

            # determine direction of this crossover
            is_long = (ema_fast_ltf_prev < ema_slow_ltf_prev) and (ema_fast_ltf >= ema_slow_ltf)

            # slopes percent
            try:
                ema_fast_slope = (ema_fast_ltf - (ema_fast_ltf_prev or ema_fast_ltf)) / (ema_fast_ltf_prev or ema_fast_ltf) * 100.0
            except Exception:
                ema_fast_slope = None
            try:
                ema_slow_slope = (ema_slow_ltf - (ema_slow_ltf_prev or ema_slow_ltf)) / (ema_slow_ltf_prev or ema_slow_ltf) * 100.0
            except Exception:
                ema_slow_slope = None

            # factors direction-aware
            if is_long:
                ltf_factor = (ema_fast_ltf / ema_slow_ltf) if ema_slow_ltf != 0 else None
            else:
                ltf_factor = (ema_slow_ltf / ema_fast_ltf) if ema_fast_ltf != 0 else None

            htf_factor = (ema_fast_htf / ema_slow_htf) if ema_slow_htf != 0 else None

            ltf_trend_bias = "buy" if ema_fast_ltf > ema_slow_ltf else "sell"
            htf_trend_bias = "buy" if ema_fast_htf > ema_slow_htf else "sell"

            # prev signal
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

            checked_at = ltf["timestamp"].iloc[i].isoformat()

            rec = {
                "checked_at_utc": checked_at,
                "symbol": symbol,
                "signal": "LONG" if is_long else "SHORT",
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
                "signal_gap_hours": signal_gap_hours,
                # placeholders for post_analysis to fill later
                "best_opening_price": "",
                "max_movement_price": "",
                "trade_time_hrs": "",
                "pct_increase": "",
                "status": ""
            }

            # update prev-signal cache (last seen crossover)
            try:
                update_prev_signal(symbol, {"signal": rec["signal"], "checked_at_utc": rec["checked_at_utc"]})
            except Exception as e:
                log_error(f"update_prev_signal failed: {repr(e)}")

            results.append(rec)

        return results

    except Exception as e:
        log_error(f"check_strategy({symbol}) error: {repr(e)}")
        return None


