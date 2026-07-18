"""
strategy_condition/indicators/trend.py
趋势类指标：MA斜率 / 周线MA斜率 / 均线多头排列 / N日新高
直接调用 market_behavior/engine/signal_engine.py 的纯函数。
"""
from __future__ import annotations
from typing import List, Tuple
import math

from vnpy.market_behavior.engine.signal_engine import ma_slope as _ma_slope


def calc_ma_slope(closes: List[float], ma_period: int = 20,
                  slope_window: int = 10) -> float:
    """MA 线性斜率（%/bar），复用 signal_engine.ma_slope。"""
    return _ma_slope(closes, ma_period, slope_window)


def check_ma_slope(closes: List[float], ma_period: int = 20,
                   slope_window: int = 10,
                   min_slope: float = 0.0) -> Tuple[bool, float]:
    """
    日线 MA 斜率是否 >= min_slope。
    返回 (passed, score)，score = 斜率归一化到 [0,1]。
    """
    slope = _ma_slope(closes, ma_period, slope_window)
    if math.isnan(slope):
        return False, 0.0
    passed = slope >= min_slope
    # 归一化：斜率每超出 min_slope 0.5 个百分点，score 加 0.1，上限 1.0
    score = min(max((slope - min_slope) / (abs(min_slope) + 0.5), 0.0), 1.0)
    return passed, score if passed else 0.0


def check_weekly_ma_slope(weekly_closes: List[float],
                          ma_period: int = 13,
                          slope_window: int = 5,
                          min_slope: float = 0.0) -> Tuple[bool, float]:
    """
    周线 MA 斜率是否 >= min_slope。
    weekly_closes 由 MultiTFEngine 提供。
    """
    slope = _ma_slope(weekly_closes, ma_period, slope_window)
    if math.isnan(slope):
        return False, 0.0
    passed = slope >= min_slope
    score  = min(max((slope - min_slope) / (abs(min_slope) + 0.5), 0.0), 1.0)
    return passed, score if passed else 0.0


def check_ma_alignment(closes: List[float],
                        periods: List[int] = None) -> Tuple[bool, float]:
    """
    均线多头排列：MA(periods[0]) > MA(periods[1]) > ... > MA(periods[-1])
    默认 MA5 > MA10 > MA20 > MA60。
    """
    if periods is None:
        periods = [5, 10, 20, 60]
    if len(closes) < max(periods):
        return False, 0.0
    ma_vals = []
    for p in periods:
        ma_vals.append(sum(closes[-p:]) / p)
    # 检查严格递减
    passed = all(ma_vals[i] > ma_vals[i + 1] for i in range(len(ma_vals) - 1))
    if not passed:
        return False, 0.0
    # score：最小差距占较小均线的比例，表示排列强度
    gaps = [(ma_vals[i] - ma_vals[i + 1]) / ma_vals[i + 1]
            for i in range(len(ma_vals) - 1)]
    score = min(min(gaps) / 0.02, 1.0)   # 差距 >= 2% 时满分
    return True, max(score, 0.0)


def check_new_high_n(closes: List[float], highs: List[float],
                     n: int = 20) -> Tuple[bool, float]:
    """
    收盘价是否突破近 n 日最高价（不含当日）。
    """
    if len(closes) < n + 1 or len(highs) < n + 1:
        return False, 0.0
    recent_high = max(highs[-n - 1:-1])
    passed      = closes[-1] > recent_high
    if not passed:
        return False, 0.0
    score = min((closes[-1] - recent_high) / recent_high / 0.03, 1.0)
    return True, max(score, 0.0)
