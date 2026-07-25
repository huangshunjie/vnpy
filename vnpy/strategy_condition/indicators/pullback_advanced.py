"""
strategy_condition/indicators/pullback_advanced.py
回调升级：回踩各均线、距离均线百分比、回撤幅度、首次回踩、缩量回调、阴线回调、强势回调评分
"""
from __future__ import annotations
from typing import List, Tuple


def _calc_ma(closes: List[float], period: int) -> float:
    if len(closes) < period:
        return 0.0
    return sum(closes[-period:]) / period


def check_pullback_to_ma_n(closes: List[float], ma_period: int = 10,
                           tol_pct: float = 2.0) -> Tuple[bool, float]:
    """
    回踩MA(N)：价格接近均线
    abs(close - MA) / MA <= tol_pct%
    """
    ma = _calc_ma(closes, ma_period)
    if ma <= 0:
        return False, 0.0
    distance = abs(closes[-1] - ma) / ma * 100.0
    passed = distance <= tol_pct
    score = max(1.0 - distance / tol_pct, 0.0) if passed else 0.0
    return passed, score


def check_ma_distance_pct(closes: List[float], ma_period: int = 10,
                          max_distance_pct: float = 2.0) -> Tuple[bool, float]:
    """
    距离均线百分比：close距离MA的百分比 <= max_distance_pct%
    """
    return check_pullback_to_ma_n(closes, ma_period, max_distance_pct)


def check_retracement_pct(closes: List[float], highs: List[float],
                          n: int = 20, min_ret: float = -15.0,
                          max_ret: float = -3.0) -> Tuple[bool, float]:
    """
    回撤幅度：从N日最高点回撤的百分比在[min_ret, max_ret]区间
    """
    if len(highs) < n or not closes:
        return False, 0.0
    peak = max(highs[-n:])
    if peak <= 0:
        return False, 0.0
    ret = (closes[-1] - peak) / peak * 100.0
    passed = min_ret <= ret <= max_ret
    if not passed:
        return False, 0.0
    # score: 越接近max_ret(回撤浅)分越高
    score = 1.0 - abs(ret - max_ret) / abs(min_ret - max_ret)
    return True, min(max(score, 0.0), 1.0)


def check_first_pullback(closes: List[float], ma_period: int = 10,
                         tol_pct: float = 2.0,
                         lookback: int = 20) -> Tuple[bool, float]:
    """
    首次回踩：在lookback窗口内，当前是第一次接近MA
    之前（lookback内）价格一直远离MA，现在首次回到MA附近
    """
    if len(closes) < ma_period + lookback:
        return False, 0.0
    # 检查当前是否接近MA
    ma_now = _calc_ma(closes, ma_period)
    if ma_now <= 0:
        return False, 0.0
    dist_now = abs(closes[-1] - ma_now) / ma_now * 100.0
    if dist_now > tol_pct:
        return False, 0.0
    # 检查前面lookback-1根K线是否都远离MA
    touch_count = 0
    for i in range(2, min(lookback, len(closes) - ma_period)):
        idx = len(closes) - i
        ma_i = sum(closes[idx - ma_period + 1:idx + 1]) / ma_period
        if ma_i <= 0:
            continue
        dist = abs(closes[idx] - ma_i) / ma_i * 100.0
        if dist <= tol_pct:
            touch_count += 1
    # 首次回踩：之前很少接触(允许1次误差)
    passed = touch_count <= 1
    score = 1.0 if passed else 0.0
    return passed, score


def check_shrink_pullback(closes: List[float], opens: List[float],
                          volumes: List[float],
                          pullback_days: int = 3,
                          vol_period: int = 10,
                          max_vol_ratio: float = 0.7) -> Tuple[bool, float]:
    """
    缩量回调：最近pullback_days天为阴线且成交量缩小
    """
    if len(closes) < pullback_days + 1 or len(volumes) < vol_period + pullback_days:
        return False, 0.0
    # 检查最近几天是否阴线居多
    yin_count = sum(1 for i in range(-pullback_days, 0)
                    if closes[i] < opens[i])
    if yin_count < pullback_days * 0.6:
        return False, 0.0
    # 检查量能是否缩小
    recent_vol = sum(volumes[-pullback_days:]) / pullback_days
    hist_vol = sum(volumes[-(vol_period + pullback_days):-pullback_days]) / vol_period
    if hist_vol <= 0:
        return False, 0.0
    ratio = recent_vol / hist_vol
    passed = ratio <= max_vol_ratio
    score = max(1.0 - ratio / max_vol_ratio, 0.0) if passed else 0.0
    return passed, score


def check_yin_pullback(closes: List[float], opens: List[float],
                       n: int = 3) -> Tuple[bool, float]:
    """
    阴线回调：最近N天阴线数量 >= N*0.6
    """
    if len(closes) < n or len(opens) < n:
        return False, 0.0
    yin_count = sum(1 for i in range(-n, 0) if closes[i] < opens[i])
    threshold = int(n * 0.6)
    passed = yin_count >= threshold
    score = yin_count / n if passed else 0.0
    return passed, score


def check_strong_pullback_score(closes: List[float], opens: List[float],
                                highs: List[float], volumes: List[float],
                                ma_period: int = 10) -> Tuple[bool, float]:
    """
    强势回调评分(0~1):
    - 接近均线 (0.3)
    - 缩量 (0.3)
    - 阴线回调 (0.2)
    - 回撤幅度适中 (0.2)
    """
    score = 0.0
    _, s1 = check_pullback_to_ma_n(closes, ma_period, 3.0)
    score += s1 * 0.3
    _, s2 = check_shrink_pullback(closes, opens, volumes, 3, 10, 0.8)
    score += s2 * 0.3
    _, s3 = check_yin_pullback(closes, opens, 3)
    score += s3 * 0.2
    _, s4 = check_retracement_pct(closes, highs, 20, -15.0, -2.0)
    score += s4 * 0.2
    passed = score >= 0.5
    return passed, min(score, 1.0)