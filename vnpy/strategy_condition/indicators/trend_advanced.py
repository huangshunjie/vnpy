"""
strategy_condition/indicators/trend_advanced.py
趋势升级指标：趋势强度、趋势持续天数、价格站上均线、趋势未破坏、均线粘合、趋势评分
"""
from __future__ import annotations
from typing import List, Tuple


def _calc_ma(closes: List[float], period: int) -> float:
    if len(closes) < period:
        return 0.0
    return sum(closes[-period:]) / period


def check_price_above_ma(closes: List[float], ma_period: int = 20) -> Tuple[bool, float]:
    """价格站上均线: close > MA(period)"""
    ma = _calc_ma(closes, ma_period)
    if ma <= 0:
        return False, 0.0
    passed = closes[-1] > ma
    # score: 超出越多分越高，上限5%对应满分
    above_pct = (closes[-1] - ma) / ma * 100.0
    score = min(above_pct / 5.0, 1.0) if passed else 0.0
    return passed, max(score, 0.0)


def check_trend_strength(closes: List[float],
                         periods: List[int] = None) -> Tuple[bool, float]:
    """
    均线趋势强度：多条均线多头排列程度评分
    每对均线满足短期>长期得1分，总分归一化
    """
    if periods is None:
        periods = [5, 10, 20, 30]
    if len(closes) < max(periods):
        return False, 0.0
    mas = [_calc_ma(closes, p) for p in periods]
    pairs = 0
    aligned =0
    for i in range(len(mas) - 1):
        pairs += 1
        if mas[i] > mas[i + 1]:
            aligned += 1
    if pairs == 0:
        return False, 0.0
    score = aligned / pairs
    passed = score >= 0.75  # 至少75%的均线对保持多头
    return passed, score


def check_trend_days(closes: List[float], ma_period: int = 20,
                     min_days: int = 5) -> Tuple[bool, float]:
    """
    趋势持续天数：连续站上MA的天数 >= min_days
    """
    if len(closes) < ma_period + min_days:
        return False, 0.0
    count = 0
    for i in range(len(closes) - 1, ma_period - 1, -1):
        ma = sum(closes[i - ma_period + 1:i + 1]) / ma_period
        if closes[i] > ma:
            count += 1
        else:
            break
    passed = count >= min_days
    score = min(count / (min_days * 2.0), 1.0) if passed else 0.0
    return passed, score


def check_trend_intact(closes: List[float], highs: List[float],
                       lows: List[float], ma_period: int = 20,
                       n: int = 10) -> Tuple[bool, float]:
    """
    趋势未破坏：近N日最低价未跌破MA(period)
    """
    if len(closes) < ma_period + n or len(lows) < n:
        return False, 0.0
    # 计算近N日每日的MA值，检查low是否都在MA之上
    intact = True
    min_margin = float('inf')
    for i in range(-n, 0):
        idx = len(closes) + i
        if idx < ma_period:
            continue
        ma = sum(closes[idx - ma_period + 1:idx + 1]) / ma_period
        low = lows[len(lows) + i]
        margin = (low - ma) / ma * 100.0
        if low < ma:
            intact = False
            break
        min_margin = min(min_margin, margin)
    if not intact:
        return False, 0.0
    score = min(min_margin / 3.0, 1.0)  # 最小margin 3%对应满分
    return True, max(score, 0.0)


def check_ma_bindong(closes: List[float],
                     periods: List[int] = None,
                     max_spread_pct: float = 2.0) -> Tuple[bool, float]:
    """
    均线粘合：所有均线之间的最大价差 <= max_spread_pct%
    用于判断横盘蓄势
    """
    if periods is None:
        periods = [5, 10, 20, 30]
    if len(closes) < max(periods):
        return False, 0.0
    mas = [_calc_ma(closes, p) for p in periods]
    ma_min = min(mas)
    ma_max = max(mas)
    if ma_min <= 0:
        return False, 0.0
    spread = (ma_max - ma_min) / ma_min * 100.0
    passed = spread <= max_spread_pct
    score = max(1.0 - spread / max_spread_pct, 0.0) if passed else 0.0
    return passed, score


def check_trend_score(closes: List[float], highs: List[float],
                      lows: List[float]) -> Tuple[bool, float]:
    """
    趋势综合评分(0~1):
    - 多头排列 (0.3)
    - 价格站上MA20 (0.25)
    - 趋势持续天数 (0.25)
    - 趋势未破坏 (0.2)
    """
    score = 0.0
    _, s1 = check_trend_strength(closes, [5, 10, 20, 30])
    score += s1 * 0.3
    _, s2 = check_price_above_ma(closes, 20)
    score += s2 * 0.25
    _, s3 = check_trend_days(closes, 20, 3)
    score += s3 * 0.25
    _, s4 = check_trend_intact(closes, highs, lows, 20, 5)
    score += s4 * 0.2
    passed = score >= 0.6
    return passed, min(score, 1.0)