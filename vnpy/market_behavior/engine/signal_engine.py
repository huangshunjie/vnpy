from __future__ import annotations
import math
from typing import Any, Dict, List, Tuple


def _ema(values, period):
    if not values or period <= 0:
        return []
    k = 2.0 / (period + 1)
    r = [values[0]]
    for v in values[1:]:
        r.append(v * k + r[-1] * (1 - k))
    return r


def macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow:
        e = [float(chr(110)+chr(97)+chr(110))] * len(closes)
        return dict(dif=e, dea=e, hist=e)
    ef  = _ema(closes, fast)
    es  = _ema(closes, slow)
    dif = [f - s for f, s in zip(ef, es)]
    dea = _ema(dif, signal)
    return dict(dif=dif, dea=dea, hist=[(d - e) * 2 for d, e in zip(dif, dea)])


def ma_slope(closes, ma_period=13, slope_window=5):
    if len(closes) < ma_period + slope_window:
        return float(chr(110)+chr(97)+chr(110))
    mv = [sum(closes[i - ma_period:i]) / ma_period
          for i in range(len(closes) - slope_window + 1, len(closes) + 1)
          if i >= ma_period]
    if len(mv) < 2:
        return float(chr(110)+chr(97)+chr(110))
    n  = len(mv)
    xs = list(range(n))
    xm = sum(xs) / n
    ym = sum(mv) / n
    num = sum((x - xm) * (y - ym) for x, y in zip(xs, mv))
    den = sum((x - xm) ** 2 for x in xs)
    return 0.0 if (den == 0 or ym == 0) else num / den / ym * 100


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return float(chr(110)+chr(97)+chr(110))
    ch = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    ag = sum(max(c, 0) for c in ch[:period]) / period
    al = sum(max(-c, 0) for c in ch[:period]) / period
    for c in ch[period:]:
        ag = (ag * (period - 1) + max(c, 0)) / period
        al = (al * (period - 1) + max(-c, 0)) / period
    return 100.0 if al == 0 else 100 - 100 / (1 + ag / al)


def atr(highs, lows, closes, period=14):
    if len(closes) < 2 or len(highs) < period:
        return float(chr(110)+chr(97)+chr(110))
    trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
           for i in range(1, len(closes))]
    if len(trs) < period:
        return float(chr(110)+chr(97)+chr(110))
    v = sum(trs[:period]) / period
    for t in trs[period:]:
        v = (v * (period - 1) + t) / period
    return v


def bollinger(closes, period=20, std_mult=2.0):
    nan = float(chr(110)+chr(97)+chr(110))
    if len(closes) < period:
        return dict(mid=nan, upper=nan, lower=nan, width=nan)
    w   = closes[-period:]
    mid = sum(w) / period
    std = math.sqrt(sum((x - mid) ** 2 for x in w) / period)
    u, l = mid + std_mult * std, mid - std_mult * std
    return dict(mid=mid, upper=u, lower=l, width=(u - l) / mid if mid > 0 else nan)


def is_golden_cross(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal + 2:
        return False
    m = macd(closes, fast, slow, signal)
    d, e = m[chr(100)+chr(105)+chr(102)], m[chr(100)+chr(101)+chr(97)]
    return len(d) >= 2 and d[-1] > e[-1] and d[-2] <= e[-2]


def is_death_cross(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal + 2:
        return False
    m = macd(closes, fast, slow, signal)
    d, e = m[chr(100)+chr(105)+chr(102)], m[chr(100)+chr(101)+chr(97)]
    return len(d) >= 2 and d[-1] < e[-1] and d[-2] >= e[-2]


def detect_pullback(closes, highs, mode=None, window=10,
                    min_drop=-8.0, max_drop=-2.0,
                    ma_period=20, ma_tol_pct=2.0):
    if mode is None:
        mode = chr(112)+chr(99)+chr(116)+'_drop'
    if len(closes) < max(window, ma_period) + 1:
        return False, 0.0
    half = abs(max_drop - min_drop) / 2 + 1e-9
    mid  = (min_drop + max_drop) / 2
    if mode == chr(112)+chr(99)+chr(116)+chr(95)+chr(100)+chr(114)+chr(111)+chr(112):
        ref  = closes[-window - 1] if len(closes) > window else closes[0]
        drop = (closes[-1] - ref) / ref * 100 if ref > 0 else 0.0
        ok   = min_drop <= drop <= max_drop
        return ok, max(0.0, 1.0 - abs(drop - mid) / half) if ok else 0.0
    elif mode == chr(102)+chr(114)+chr(111)+chr(109)+'_high':
        peak = max(highs[-window:]) if highs else closes[-1]
        dd   = (closes[-1] - peak) / peak * 100 if peak > 0 else 0.0
        ok   = min_drop <= dd <= max_drop
        return ok, max(0.0, 1.0 - abs(dd - mid) / half) if ok else 0.0
    elif mode == chr(116)+chr(111)+'_ma':
        if len(closes) < ma_period:
            return False, 0.0
        ma_val = sum(closes[-ma_period:]) / ma_period
        if ma_val <= 0:
            return False, 0.0
        dist = (closes[-1] - ma_val) / ma_val * 100
        ok   = abs(dist) <= ma_tol_pct
        sl   = ma_slope(closes, ma_period)
        if not math.isnan(sl) and sl <= 0:
            return False, 0.0
        return ok, max(0.0, 1.0 - abs(dist) / (ma_tol_pct + 1e-9)) if ok else 0.0
    return False, 0.0


class SignalEngine:
    def __init__(self, log_fn=None, main_engine=None):
        self._log         = log_fn or print
        self._main_engine = main_engine
        self._candle_buf  = None

    def set_main_engine(self, e):   self._main_engine = e
    def set_candle_buffer(self, b): self._candle_buf  = b

    def init(self):
        self._log('[SignalEngine] init()')

    def start(self):
        self._log('[SignalEngine] start()')

    def stop(self):
        self._log('[SignalEngine] stop()')

    def _c(self, sym, n=300):
        return self._candle_buf.get_closes(sym, n) if self._candle_buf else []

    def _b(self, sym, n=300):
        return self._candle_buf.get(sym, n) if self._candle_buf else []

    def get_macd(self, sym, fast=12, slow=26, sig=9, n=300):
        return macd(self._c(sym, n), fast, slow, sig)

    def get_ma_slope(self, sym, ma_period=13, slope_window=5, n=200):
        return ma_slope(self._c(sym, n), ma_period, slope_window)

    def get_rsi(self, sym, period=14, n=100):
        return rsi(self._c(sym, n), period)

    def get_atr(self, sym, period=14, n=100):
        bars = self._b(sym, n)
        return float(chr(110)+chr(97)+chr(110)) if not bars else atr(
            [b.high for b in bars], [b.low for b in bars],
            [b.close for b in bars], period)

    def get_bollinger(self, sym, period=20, std_mult=2.0, n=100):
        return bollinger(self._c(sym, n), period, std_mult)

    def is_macd_golden(self, sym, fast=12, slow=26, sig=9):
        return is_golden_cross(self._c(sym, slow + sig + 10), fast, slow, sig)

    def is_macd_death(self, sym, fast=12, slow=26, sig=9):
        return is_death_cross(self._c(sym, slow + sig + 10), fast, slow, sig)

    def check_pullback(self, sym, mode=None, window=10,
                       min_drop=-8.0, max_drop=-2.0,
                       ma_period=20, ma_tol_pct=2.0, n=200):
        if mode is None:
            mode = chr(112)+chr(99)+chr(116)+'_drop'
        bars = self._b(sym, n)
        return detect_pullback([b.close for b in bars], [b.high for b in bars],
                               mode, window, min_drop, max_drop, ma_period, ma_tol_pct)

    def summary(self):
        return dict(engine='SignalEngine', buffer=self._candle_buf is not None)
