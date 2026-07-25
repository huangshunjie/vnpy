"""
strategy_condition/indicators/deviation.py
均线偏离指标：MA乖离率、MA间距、超涨过滤
"""
from __future__ import annotations
from typing import List, Tuple


def _calc_ma(closes: List[float], period: int) -> float:
    """计算简单移动平均"""
    if len(closes) < period:
        return 0.0
    return sum(closes[-period:]) / period


def check_dev_ma(closes: List[float], ma_period: int = 10,
                 max_dev_pct: float = 5.0) -> Tuple[bool, float]:
    """
    MA乖离率过滤：abs(close - MA) / MA <= max_dev_pct%
    返回True表示乖离率在合理范围内（未超涨/超跌）
    """
    ma = _calc_ma(closes, ma_period)
    if ma <= 0:
        return False, 0.0
    dev = (closes[-1] - ma) / ma * 100.0
    abs_dev = abs(dev)
    passed = abs_dev <= max_dev_pct
    # score: 越靠近均线分越高
    score = max(1.0 - abs_dev / max_dev_pct, 0.0) if passed else 0.0
    return passed, score


def check_dev_ma5(closes: List[float],
                  max_dev_pct: float = 5.0) -> Tuple[bool, float]:
    """MA5乖离率"""
    return check_dev_ma(closes, 5, max_dev_pct)


def check_dev_ma10(closes: List[float],
                   max_dev_pct: float = 5.0) -> Tuple[bool, float]:
    """MA10乖离率"""
    return check_dev_ma(closes, 10, max_dev_pct)


def check_dev_ma20(closes: List[float],
                   max_dev_pct: float = 8.0) -> Tuple[bool, float]:
    """MA20乖离率"""
    return check_dev_ma(closes, 20, max_dev_pct)


def check_dev_ma10_ma20(closes: List[float],
                        max_distance_pct: float = 5.0) -> Tuple[bool, float]:
    """
    MA10与MA20之间的距离百分比 <= max_distance_pct%
    用于过滤均线发散过大的情况
    """
    if len(closes) < 20:
        return False, 0.0
    ma10 = _calc_ma(closes, 10)
    ma20 = _calc_ma(closes, 20)
    if ma20 <= 0:
        return False, 0.0
    distance = abs(ma10 - ma20) / ma20 * 100.0
    passed = distance <= max_distance_pct
    score = max(1.0 - distance / max_distance_pct, 0.0) if passed else 0.0
    return passed, score


def check_dev_overbought(closes: List[float], ma_period: int = 10,
                         max_above_pct: float = 10.0) -> Tuple[bool, float]:
    """
    超涨过滤：价格超过MA的百分比 <= max_above_pct%
    返回True表示未超涨（可以买入）
    """
    ma = _calc_ma(closes, ma_period)
    if ma <= 0:
        return False, 0.0
    above = (closes[-1] - ma) / ma * 100.0
    passed = above <= max_above_pct
    score = max(1.0 - above / max_above_pct, 0.0) if passed else 0.0
    return passed, score


def check_dev_ma_distance(closes: List[float],
                          fast_period: int = 5, slow_period: int = 20,
                          max_distance_pct: float = 8.0) -> Tuple[bool, float]:
    """
    均线距离过滤：快线与慢线间距 <= max_distance_pct%
    """
    if len(closes) < slow_period:
        return False, 0.0
    ma_fast = _calc_ma(closes, fast_period)
    ma_slow = _calc_ma(closes, slow_period)
    if ma_slow <= 0:
        return False, 0.0
    distance = abs(ma_fast - ma_slow) / ma_slow * 100.0
    passed = distance <= max_distance_pct
    score = max(1.0 - distance / max_distance_pct, 0.0) if passed else 0.0
    return passed, score