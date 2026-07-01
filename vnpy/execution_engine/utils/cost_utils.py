"""
execution_engine/utils/cost_utils.py

成本计算工具函数（Phase 4）。

提供独立于 CostEngine 的轻量级成本估算函数，
供 SignalAdapter / Report Tab 快速调用。
"""

from __future__ import annotations

import math


def estimate_commission(
    notional:        float,
    rate:            float = 0.0003,
    fixed:           float = 0.0,
    volume:          float = 0.0,
    fixed_per_lot:   float = 0.0,
) -> float:
    """
    快速估算手续费。

    优先级：fixed_per_lot > fixed > rate_on_notional
    """
    if fixed_per_lot > 0 and volume > 0:
        return fixed_per_lot * volume
    if fixed > 0:
        return fixed
    return notional * rate


def estimate_slippage_cost(
    price:     float,
    volume:    float,
    ticks:     int   = 1,
    tick_size: float = 0.01,
    multiplier: float = 1.0,
) -> float:
    """固定 Tick 滑点成本估算。"""
    return price * 0 + ticks * tick_size * volume * multiplier  # price 保留供调用方参考


def estimate_impact_cost(
    price:         float,
    volume:        float,
    daily_vol:     float = 0.015,
    daily_volume:  float = 10000.0,
    impact_factor: float = 0.3,
    multiplier:    float = 1.0,
) -> float:
    """
    square-root 市场冲击成本估算。

    impact = factor × σ × √(Q/V) × P × Q × multiplier
    """
    if daily_volume <= 0 or volume <= 0:
        return 0.0
    participation = volume / daily_volume
    return (impact_factor * daily_vol * math.sqrt(participation)
            * price * volume * multiplier)


def estimate_total_cost(
    price:         float,
    volume:        float,
    multiplier:    float = 1.0,
    commission_rate: float = 0.0003,
    ticks:         int   = 1,
    tick_size:     float = 0.01,
    daily_vol:     float = 0.015,
    daily_volume:  float = 10000.0,
    impact_factor: float = 0.3,
) -> dict[str, float]:
    """
    一站式成本估算，返回各分项和合计。

    Returns
    -------
    dict with keys: commission / slippage / impact / total / cost_pct
    """
    notional   = price * volume * multiplier
    commission = estimate_commission(notional, commission_rate)
    slippage   = estimate_slippage_cost(price, volume, ticks, tick_size, multiplier)
    impact     = estimate_impact_cost(price, volume, daily_vol, daily_volume,
                                       impact_factor, multiplier)
    total      = commission + slippage + impact
    cost_pct   = total / notional if notional > 0 else 0.0
    return {
        "commission": commission,
        "slippage":   slippage,
        "impact":     impact,
        "total":      total,
        "cost_pct":   cost_pct,
        "notional":   notional,
    }


def breakeven_move(
    total_cost: float,
    volume:     float,
    multiplier: float = 1.0,
) -> float:
    """
    盈亏平衡价格移动幅度（绝对值）。

    = total_cost / (volume × multiplier)
    """
    denom = volume * multiplier
    if denom <= 0:
        return 0.0
    return total_cost / denom
