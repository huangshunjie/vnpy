"""
market_behavior/utils/calculator.py
统计计算工具 — Phase 1 骨架
Phase 2+: 实现窗口计数 / 均值 / 标准差等统计函数
"""
from __future__ import annotations
from typing import List, Sequence


def count_true(flags: Sequence[bool]) -> int:
    """统计序列中 True 的个数。"""
    return sum(1 for f in flags if f)


def rolling_count(values: Sequence[float],
                  condition_fn,
                  window: int) -> int:
    """
    在最近 window 根数据中统计满足 condition_fn 的次数。
    condition_fn: (value) -> bool
    """
    data = list(values)[-window:]
    return sum(1 for v in data if condition_fn(v))


def rolling_max(values: Sequence[float], window: int) -> float:
    """最近 window 期最大值。"""
    data = list(values)[-window:]
    return max(data) if data else 0.0


def rolling_min(values: Sequence[float], window: int) -> float:
    """最近 window 期最小值。"""
    data = list(values)[-window:]
    return min(data) if data else 0.0


def rolling_mean(values: Sequence[float], window: int) -> float:
    """最近 window 期均值。"""
    data = list(values)[-window:]
    return sum(data) / len(data) if data else 0.0


def rolling_std(values: Sequence[float], window: int) -> float:
    """最近 window 期标准差。"""
    import math
    data = list(values)[-window:]
    if len(data) < 2:
        return 0.0
    mean = sum(data) / len(data)
    variance = sum((x - mean) ** 2 for x in data) / (len(data) - 1)
    return math.sqrt(variance)


def consecutive_count(flags: Sequence[bool]) -> int:
    """
    从最后一个元素往前数，连续 True 的个数。
    用于判断连续上涨/下跌天数。
    """
    count = 0
    for f in reversed(list(flags)):
        if f:
            count += 1
        else:
            break
    return count


def max_consecutive_count(flags) -> int:
    """序列中最长连续 True 段的长度。
    用于量能检测：均值抬升后末尾段可能不满足，但中间段存在连续 N 天放量。
    """
    max_run = cur_run = 0
    for f in flags:
        if f:
            cur_run += 1
            if cur_run > max_run:
                max_run = cur_run
        else:
            cur_run = 0
    return max_run
