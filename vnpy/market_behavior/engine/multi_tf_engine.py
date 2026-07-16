from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Any
import math


class WeeklyBar:
    __slots__ = ("symbol", "week_start", "open", "high", "low", "close", "volume")

    def __init__(self, symbol, week_start, open_, high, low, close, volume):
        self.symbol     = symbol
        self.week_start = week_start
        self.open       = open_
        self.high       = high
        self.low        = low
        self.close      = close
        self.volume     = volume


def _week_start(dt: datetime) -> datetime:
    return (dt - timedelta(days=dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)


class MultiTFEngine:
    DEFAULT_WEEKLY_KEEP = 200

    def __init__(self, log_fn=None, main_engine=None):
        self._log         = log_fn or print
        self._main_engine = main_engine
        self._candle_buf  = None
        self._signal_eng  = None
        self._weekly: Dict[str, List[WeeklyBar]] = defaultdict(list)

    def set_main_engine(self, e):   self._main_engine = e
    def set_candle_buffer(self, b): self._candle_buf  = b
    def set_signal_engine(self, s): self._signal_eng  = s

    def init(self):  self._log("[MultiTFEngine] init()")
    def start(self): self._log("[MultiTFEngine] start()")
    def stop(self):  self._log("[MultiTFEngine] stop()")

    def build_weekly(self, symbol: str) -> None:
        if not self._candle_buf:
            return
        bars = self._candle_buf.get(symbol, 1000)
        if not bars:
            return
        weekly: List[WeeklyBar] = []
        cur_week = None
        wo = wh = wl = wc = wv = ws = None
        for bar in bars:
            wk = _week_start(bar.dt)
            if wk != cur_week:
                if cur_week is not None:
                    weekly.append(WeeklyBar(symbol, ws, wo, wh, wl, wc, wv))
                cur_week, ws = wk, wk
                wo, wh, wl, wc, wv = bar.open, bar.high, bar.low, bar.close, float(bar.volume)
            else:
                wh = max(wh, bar.high)
                wl = min(wl, bar.low)
                wc = bar.close
                wv += float(bar.volume)
        if cur_week is not None:
            weekly.append(WeeklyBar(symbol, ws, wo, wh, wl, wc, wv))
        self._weekly[symbol] = weekly[-self.DEFAULT_WEEKLY_KEEP:]

    def update_weekly(self, symbol: str) -> None:
        if not self._candle_buf:
            return
        bar = self._candle_buf.latest(symbol)
        if bar is None:
            return
        wk    = _week_start(bar.dt)
        cache = self._weekly[symbol]
        if cache and cache[-1].week_start == wk:
            w = cache[-1]
            w.high   = max(w.high, bar.high)
            w.low    = min(w.low, bar.low)
            w.close  = bar.close
            w.volume += float(bar.volume)
        else:
            cache.append(WeeklyBar(symbol, wk, bar.open, bar.high,
                                   bar.low, bar.close, float(bar.volume)))
            if len(cache) > self.DEFAULT_WEEKLY_KEEP:
                cache.pop(0)

    def get_weekly_bars(self, symbol: str, n: int = 100) -> List[WeeklyBar]:
        self.build_weekly(symbol)
        cache = self._weekly.get(symbol, [])
        return cache[-n:] if len(cache) >= n else cache

    def get_weekly_closes(self, symbol: str, n: int = 100) -> List[float]:
        return [b.close for b in self.get_weekly_bars(symbol, n)]

    def get_weekly_ma_slope(self, symbol: str,
                            ma_period: int = 13, slope_window: int = 5) -> float:
        from .signal_engine import ma_slope
        closes = self.get_weekly_closes(symbol, ma_period + slope_window + 5)
        return ma_slope(closes, ma_period, slope_window)

    def is_weekly_ma_rising(self, symbol: str,
                            ma_period: int = 13, min_slope: float = 0.0) -> bool:
        slope = self.get_weekly_ma_slope(symbol, ma_period)
        return not math.isnan(slope) and slope >= min_slope

    def summary(self) -> dict:
        return {"engine": "MultiTFEngine", "symbols": len(self._weekly)}
