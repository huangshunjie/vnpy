"""
strategy_condition/indicators/strength.py
强势股指标：N日涨幅、最大涨幅、阶段新高、涨停次数、大阳线次数、放量突破、强势评分
"""
from __future__ import annotations
from typing import List, Tuple


def check_strength_return_n(closes: List[float], n: int = 20,
                            min_return: float = 20.0) -> Tuple[bool, float]:
    """N日涨幅 >= min_return%"""
    if len(closes) < n + 1:
        return False, 0.0
    ret = (closes[-1] - closes[-n - 1]) / closes[-n - 1] * 100.0
    passed = ret >= min_return
    score = min(ret / (min_return * 2.0 + 1e-9), 1.0) if passed else 0.0
    return passed, score


def check_strength_max_gain(closes: List[float], highs: List[float],
                            n: int = 20, min_gain: float = 30.0) -> Tuple[bool, float]:
    """N日内最大涨幅(最高价/N日前收盘-1) >= min_gain%"""
    if len(closes) < n + 1 or len(highs) < n:
        return False, 0.0
    base = closes[-n - 1]
    if base <= 0:
        return False, 0.0
    max_high = max(highs[-n:])
    gain = (max_high - base) / base * 100.0
    passed = gain >= min_gain
    score = min(gain / (min_gain * 2.0 + 1e-9), 1.0) if passed else 0.0
    return passed, score


def check_strength_stage_high(closes: List[float], highs: List[float],
                              n: int = 60) -> Tuple[bool, float]:
    """当前收盘价是否为N日内阶段新高"""
    if len(closes) < n or len(highs) < n:
        return False, 0.0
    stage_high = max(highs[-n:])
    passed = closes[-1] >= stage_high * 0.98  # 距离新高2%以内
    score = min(closes[-1] / stage_high, 1.0) if passed else 0.0
    return passed, score


def check_strength_limit_up_count(closes: List[float], opens: List[float],
                                  n: int = 20,
                                  min_count: int = 1) -> Tuple[bool, float]:
    """
    N日内涨停次数 >= min_count
    涨停判断：(close - prev_close) / prev_close >= 9.5% 或 high/prev_close >= 1.095
    """
    if len(closes) < n + 1:
        return False, 0.0
    count = 0
    for i in range(-n, 0):
        prev = closes[i - 1]
        if prev <= 0:
            continue
        if (closes[i] - prev) / prev >= 0.095:
            count += 1
    passed = count >= min_count
    score = min(count / (min_count * 2.0 + 1e-9), 1.0) if passed else 0.0
    return passed, score


def check_strength_big_yang_count(closes: List[float], opens: List[float],
                                  n: int = 20, min_count: int = 2,
                                  min_pct: float = 5.0) -> Tuple[bool, float]:
    """N日内大阳线次数(涨幅>=min_pct%) >= min_count"""
    if len(closes) < n + 1 or len(opens) < n:
        return False, 0.0
    count = 0
    for i in range(-n, 0):
        if opens[i] <= 0:
            continue
        chg = (closes[i] - opens[i]) / opens[i] * 100.0
        if chg >= min_pct:
            count += 1
    passed = count >= min_count
    score = min(count / (min_count * 2.0 + 1e-9), 1.0) if passed else 0.0
    return passed, score


def check_strength_vol_break(closes: List[float], volumes: List[float],
                             n: int = 20, vol_ratio: float = 2.0,
                             price_pct: float = 3.0) -> Tuple[bool, float]:
    """N日内存在放量突破(量比>=vol_ratio且涨幅>=price_pct%)"""
    if len(closes) < n + 1 or len(volumes) < n + 1:
        return False, 0.0
    found = False
    best_ratio = 0.0
    for i in range(-n, 0):
        if i -20 < -len(volumes):
            continue
        # 量比：当日量 / 过去20日均量
        start_idx = max(0, len(volumes) + i - 20)
        end_idx = len(volumes) + i
        if end_idx - start_idx < 5:
            continue
        avg_vol = sum(volumes[start_idx:end_idx]) / (end_idx - start_idx)
        if avg_vol <= 0:
            continue
        cur_vol = volumes[len(volumes) + i]
        ratio = cur_vol / avg_vol
        # 涨幅
        prev_c = closes[len(closes) + i - 1]
        if prev_c <= 0:
            continue
        chg = (closes[len(closes) + i] - prev_c) / prev_c * 100.0
        if ratio >= vol_ratio and chg >= price_pct:
            found = True
            best_ratio = max(best_ratio, ratio)
    if not found:
        return False, 0.0
    score = min(best_ratio / (vol_ratio * 2.0), 1.0)
    return True, score


def check_strength_score(closes: List[float], highs: List[float],
                         opens: List[float], volumes: List[float],
                         n: int = 20) -> Tuple[bool, float]:
    """
    强势股综合评分(0~1):
    - N日涨幅 (0.3)
    - 涨停次数 (0.25)
    - 大阳线次数 (0.2)
    - 阶段新高 (0.15)
    - 放量突破 (0.1)
    """
    score = 0.0
    # N日涨幅分
    _, s1 = check_strength_return_n(closes, n, 10.0)
    score += s1 * 0.3
    # 涨停次数分
    _, s2 = check_strength_limit_up_count(closes, opens, n, 1)
    score += s2 * 0.25
    # 大阳线次数分
    _, s3 = check_strength_big_yang_count(closes, opens, n, 1, 5.0)
    score += s3 * 0.2
    # 阶段新高分
    _, s4 = check_strength_stage_high(closes, highs, n)
    score += s4 * 0.15
    # 放量突破分
    _, s5 = check_strength_vol_break(closes, volumes, n, 1.5, 3.0)
    score += s5 * 0.1

    passed = score >= 0.4
    return passed, min(score, 1.0)