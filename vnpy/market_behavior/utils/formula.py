"""
market_behavior/utils/formula.py
通用公式 — Phase 1 骨架
Phase 2+: 实现实体比 / 影线比 / 振幅等基础计算
"""
from __future__ import annotations
from typing import Sequence


def body_ratio(open_: float, close: float,
               high: float, low: float) -> float:
    """实体占振幅比: abs(close-open) / (high-low)"""
    rng = high - low
    if rng <= 0:
        return 0.0
    return abs(close - open_) / rng


def upper_shadow_ratio(open_: float, close: float,
                       high: float, low: float) -> float:
    """上影线比: (high - max(open,close)) / (high-low)"""
    rng = high - low
    if rng <= 0:
        return 0.0
    return (high - max(open_, close)) / rng


def lower_shadow_ratio(open_: float, close: float,
                       high: float, low: float) -> float:
    """下影线比: (min(open,close) - low) / (high-low)"""
    rng = high - low
    if rng <= 0:
        return 0.0
    return (min(open_, close) - low) / rng


def change_pct(close: float, prev_close: float) -> float:
    """涨跌幅: (close - prev_close) / prev_close * 100"""
    if prev_close <= 0:
        return 0.0
    return (close - prev_close) / prev_close * 100


def amplitude_pct(high: float, low: float, prev_close: float) -> float:
    """振幅: (high - low) / prev_close * 100"""
    if prev_close <= 0:
        return 0.0
    return (high - low) / prev_close * 100
