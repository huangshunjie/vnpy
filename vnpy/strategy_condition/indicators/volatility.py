"""
strategy_condition/indicators/volatility.py
波动类指标：ATR 相对振幅 / 布林带宽度
"""
from __future__ import annotations
from typing import List, Tuple
import math

from vnpy.market_behavior.engine.signal_engine import (
    atr       as _atr,
    bollinger as _boll,
)


def check_atr_ratio(closes: List[float],
                    highs:  List[float],
                    lows:   List[float],
                    period:    int   = 14,
                    min_ratio: float = 1.0,
                    max_ratio: float = 9999.0) -> Tuple[bool, float]:
    """ATR / 收盘价 * 100（%）在 [min_ratio, max_ratio] 之间"""
    atr_val = _atr(highs, lows, closes, period)
    if math.isnan(atr_val) or closes[-1] <= 0:
        return False, 0.0
    ratio  = atr_val / closes[-1] * 100
    passed = min_ratio <= ratio <= max_ratio
    score  = min(ratio / (min_ratio * 2 if min_ratio > 0 else ratio + 1), 1.0)
    return passed, score if passed else 0.0


def check_boll_width(closes: List[float],
                     period:    int   = 20,
                     std_mult:  float = 2.0,
                     min_width: float = 0.05,
                     max_width: float = 9999.0) -> Tuple[bool, float]:
    """布林带宽度（(上轨-下轨)/中轨）在 [min_width, max_width] 之间"""
    boll = _boll(closes, period, std_mult)
    w    = boll["width"]
    if math.isnan(w):
        return False, 0.0
    passed = min_width <= w <= max_width
    score  = min(w / (max_width if max_width < 9999 else w + 1), 1.0)
    return passed, score if passed else 0.0
