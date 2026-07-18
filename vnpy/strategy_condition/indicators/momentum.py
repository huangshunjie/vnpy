"""
strategy_condition/indicators/momentum.py
动量类指标：MACD金叉/死叉 / RSI范围 / N日收益率
"""
from __future__ import annotations
from typing import List, Tuple
import math

from vnpy.market_behavior.engine.signal_engine import (
    is_golden_cross as _golden,
    is_death_cross  as _death,
    rsi             as _rsi,
)


def check_macd_golden(closes: List[float],
                      fast: int = 12, slow: int = 26,
                      signal: int = 9) -> Tuple[bool, float]:
    """MACD DIF 上穿 DEA（金叉）"""
    if len(closes) < slow + signal + 2:
        return False, 0.0
    passed = _golden(closes, fast, slow, signal)
    return passed, 1.0 if passed else 0.0


def check_macd_death(closes: List[float],
                     fast: int = 12, slow: int = 26,
                     signal: int = 9) -> Tuple[bool, float]:
    """MACD DIF 下穿 DEA（死叉）"""
    if len(closes) < slow + signal + 2:
        return False, 0.0
    passed = _death(closes, fast, slow, signal)
    return passed, 1.0 if passed else 0.0


def check_rsi_range(closes: List[float],
                    period: int = 14,
                    min_rsi: float = 30.0,
                    max_rsi: float = 70.0) -> Tuple[bool, float]:
    """RSI 在 [min_rsi, max_rsi] 范围内"""
    val = _rsi(closes, period)
    if math.isnan(val):
        return False, 0.0
    passed = min_rsi <= val <= max_rsi
    mid    = (min_rsi + max_rsi) / 2
    half   = (max_rsi - min_rsi) / 2 + 1e-9
    score  = max(1.0 - abs(val - mid) / half, 0.0)
    return passed, score if passed else 0.0


def check_return_n_days(closes: List[float],
                        n: int = 10,
                        min_return: float = 5.0) -> Tuple[bool, float]:
    """过去 N 日累计收益率（%）>= min_return"""
    if len(closes) < n + 1:
        return False, 0.0
    ref  = closes[-n - 1]
    if ref <= 0:
        return False, 0.0
    ret  = (closes[-1] - ref) / ref * 100
    passed = ret >= min_return
    score  = min(max(ret / (min_return * 2 + 1e-9), 0.0), 1.0)
    return passed, score if passed else 0.0
