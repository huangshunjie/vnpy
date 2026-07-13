"""
execution_engine/utils/math_utils.py

价格 / 数量计算工具函数（Phase 4）。
"""

from __future__ import annotations

import math


def round_to_tick(price: float, tick_size: float) -> float:
    """将价格对齐到最小变动单位。"""
    if tick_size <= 0:
        return price
    return round(round(price / tick_size) * tick_size, 10)


def round_to_lot(volume: float, lot_size: float = 1.0) -> float:
    """将数量向下取整到最小交易单位。"""
    if lot_size <= 0:
        return volume
    return math.floor(volume / lot_size) * lot_size


def calc_notional(price: float, volume: float, multiplier: float = 1.0) -> float:
    """计算名义价值。"""
    return price * volume * multiplier


def calc_pnl(
    entry_price: float,
    exit_price:  float,
    volume:      float,
    direction:   str,
    multiplier:  float = 1.0,
) -> float:
    """
    计算单边持仓的 PnL。

    Parameters
    ----------
    direction : "LONG" 或 "SHORT"
    """
    if direction == "LONG":
        return (exit_price - entry_price) * volume * multiplier
    else:
        return (entry_price - exit_price) * volume * multiplier


def calc_return_pct(entry: float, exit_: float, direction: str) -> float:
    """计算收益率（方向调整后）。"""
    if entry <= 0:
        return 0.0
    if direction == "LONG":
        return (exit_ - entry) / entry
    else:
        return (entry - exit_) / entry


def weight_to_volume(
    weight:      float,
    nav:         float,
    price:       float,
    lot_size:    float = 1.0,
) -> float:
    """
    将目标权重换算为手数。

    volume = floor(weight × nav / price / lot_size) × lot_size
    """
    if price <= 0 or nav <= 0:
        return 0.0
    raw = weight * nav / price
    return round_to_lot(raw, lot_size)


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法，分母为 0 时返回 default。"""
    if denominator == 0.0:
        return default
    return numerator / denominator


def clamp(value: float, lo: float, hi: float) -> float:
    """将 value 限定在 [lo, hi] 区间内。"""
    return max(lo, min(hi, value))
