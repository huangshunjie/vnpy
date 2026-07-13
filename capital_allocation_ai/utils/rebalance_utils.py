"""
capital_allocation_ai/utils/rebalance_utils.py  (Phase 5)

再平衡工具函数。

实现：
  - should_rebalance          触发判断（偏差阈值）
  - compute_rebalance_trades  再平衡交易量计算
  - estimate_rebalance_cost   交易成本估算
  - compute_deviation         当前 vs 目标偏差
  - compute_drift_score       综合漂移评分
  - check_scheduled_trigger   定时触发检查
  - check_risk_trigger        风险触发检查
  - check_score_trigger       评分变化触发检查

❌ 无 IO，无网络，无线程，纯计算
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Sequence


# ─────────────────────────────────────────────────────────────────────────────
#  偏差计算
# ─────────────────────────────────────────────────────────────────────────────

def compute_deviation(
    current: dict[str, float],
    target:  dict[str, float],
) -> dict[str, float]:
    """
    计算当前配置与目标配置的绝对偏差。

    Returns
    -------
    dict  {alpha_id: delta}  正 = 低配，负 = 超配
    """
    all_ids = set(current) | set(target)
    return {
        aid: round(target.get(aid, 0.0) - current.get(aid, 0.0), 8)
        for aid in all_ids
    }


def compute_max_deviation(
    current: dict[str, float],
    target:  dict[str, float],
) -> float:
    """返回最大绝对偏差。"""
    dev = compute_deviation(current, target)
    return max(abs(v) for v in dev.values()) if dev else 0.0


def compute_drift_score(
    current:    dict[str, float],
    target:     dict[str, float],
    method:     str = "l2",
) -> float:
    """
    计算组合漂移评分（越大越需要再平衡）。

    Parameters
    ----------
    method : "l2" = L2 范数；"l1" = 平均绝对偏差

    Returns
    -------
    float  [0, +∞)
    """
    dev = compute_deviation(current, target)
    vals = list(dev.values())
    if not vals:
        return 0.0
    if method == "l2":
        return round(math.sqrt(sum(v ** 2 for v in vals)), 6)
    return round(sum(abs(v) for v in vals) / len(vals), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  触发判断
# ─────────────────────────────────────────────────────────────────────────────

def should_rebalance(
    current:   dict[str, float],
    target:    dict[str, float],
    threshold: float = 0.05,
) -> bool:
    """
    判断是否需要再平衡（任一绝对偏差超过阈值）。

    Parameters
    ----------
    threshold : 触发阈值（默认 5%）

    Returns
    -------
    bool
    """
    return compute_max_deviation(current, target) >= threshold


def check_scheduled_trigger(
    last_rebalance_at: datetime | None,
    interval_days:     int = 7,
    reference_time:    datetime | None = None,
) -> bool:
    """
    检查定时再平衡触发条件。

    Parameters
    ----------
    last_rebalance_at : 上次再平衡时间（None 表示从未执行过）
    interval_days     : 再平衡间隔天数（默认 7 天）
    reference_time    : 当前参考时间（None 则用 datetime.now()）

    Returns
    -------
    bool  是否应触发定时再平衡
    """
    now = reference_time or datetime.now()
    if last_rebalance_at is None:
        return True
    return (now - last_rebalance_at) >= timedelta(days=interval_days)


def check_risk_trigger(
    risk_snap,
    var_threshold:  float = 0.025,
    dd_threshold:   float = 0.12,
    n_breach_limit: int   = 3,
) -> tuple[bool, str]:
    """
    检查风险触发条件。

    Parameters
    ----------
    risk_snap      : RiskSnapshot（可为 None）
    var_threshold  : 组合 VaR 上限
    dd_threshold   : 组合回撤上限
    n_breach_limit : 最大允许违规 Alpha 数

    Returns
    -------
    (triggered, reason)
    """
    if risk_snap is None:
        return False, ""

    if risk_snap.portfolio_var > var_threshold:
        return True, (
            f"Portfolio VaR={risk_snap.portfolio_var:.4f}"
            f" > threshold={var_threshold:.4f}"
        )
    if risk_snap.portfolio_dd > dd_threshold:
        return True, (
            f"Portfolio DD={risk_snap.portfolio_dd:.4f}"
            f" > threshold={dd_threshold:.4f}"
        )
    if risk_snap.n_breached > n_breach_limit:
        return True, (
            f"Breached alphas={risk_snap.n_breached}"
            f" > limit={n_breach_limit}"
        )
    return False, ""


def check_score_trigger(
    prev_scores: dict[str, float],
    curr_scores: dict[str, float],
    change_threshold: float = 0.10,
    n_changed_limit:  int   = 3,
) -> tuple[bool, str]:
    """
    检查评分变化触发条件。

    当超过 n_changed_limit 个 Alpha 的评分变化超过 change_threshold 时触发。

    Returns
    -------
    (triggered, reason)
    """
    if not prev_scores or not curr_scores:
        return False, ""

    changed = [
        aid for aid in curr_scores
        if abs(curr_scores[aid] - prev_scores.get(aid, curr_scores[aid]))
           >= change_threshold
    ]
    if len(changed) >= n_changed_limit:
        return True, (
            f"Score change: {len(changed)} alphas changed"
            f" > limit={n_changed_limit}"
        )
    return False, ""


# ─────────────────────────────────────────────────────────────────────────────
#  交易计算
# ─────────────────────────────────────────────────────────────────────────────

def compute_rebalance_trades(
    current:       dict[str, float],
    target:        dict[str, float],
    total_capital: float,
    min_trade:     float = 1000.0,
) -> dict[str, float]:
    """
    计算再平衡所需调整量（金额）。

    小于 min_trade 的调整量直接忽略（降低交易摩擦）。

    Parameters
    ----------
    current       : 当前分配比例
    target        : 目标分配比例
    total_capital : 总资金
    min_trade     : 最小有效交易金额

    Returns
    -------
    dict  {alpha_id: delta_capital}
      正 = 增配，负 = 减配
    """
    dev = compute_deviation(current, target)
    trades: dict[str, float] = {}
    for aid, delta_ratio in dev.items():
        delta_amt = round(delta_ratio * total_capital, 2)
        if abs(delta_amt) >= min_trade:
            trades[aid] = delta_amt
    return trades


def compute_incremental_trades(
    trades:        dict[str, float],
    max_single:    float = 500_000.0,
) -> list[dict[str, float]]:
    """
    将大额交易拆分为多批次（降低市场冲击）。

    Parameters
    ----------
    trades     : {alpha_id: delta_capital}
    max_single : 单笔最大交易金额

    Returns
    -------
    list of batches，每批 {alpha_id: delta_capital}
    """
    if not trades:
        return []

    batches: list[dict[str, float]] = []
    remaining = dict(trades)

    while any(abs(v) >= max_single * 0.01 for v in remaining.values()):
        batch: dict[str, float] = {}
        for aid, amt in list(remaining.items()):
            if abs(amt) < max_single * 0.01:
                remaining.pop(aid)
                continue
            chunk = math.copysign(min(abs(amt), max_single), amt)
            batch[aid] = round(chunk, 2)
            remaining[aid] = round(amt - chunk, 2)
        if batch:
            batches.append(batch)
        else:
            break
    return batches


# ─────────────────────────────────────────────────────────────────────────────
#  成本估算
# ─────────────────────────────────────────────────────────────────────────────

def estimate_rebalance_cost(
    trades:         dict[str, float],
    commission:     float = 0.0003,   # 单边佣金率
    slippage:       float = 0.0002,   # 滑点估算
    market_impact:  float = 0.0001,   # 市场冲击
) -> dict:
    """
    估算再平衡交易成本明细。

    Parameters
    ----------
    trades        : {alpha_id: delta_capital}
    commission    : 单边佣金率
    slippage      : 滑点率
    market_impact : 市场冲击率

    Returns
    -------
    dict  {
      "commission":     float,
      "slippage":       float,
      "market_impact":  float,
      "total":          float,
      "total_turnover": float,
    }
    """
    total_turnover = sum(abs(v) for v in trades.values())
    cost_rate      = commission + slippage + market_impact
    commission_amt = round(total_turnover * commission,     2)
    slippage_amt   = round(total_turnover * slippage,       2)
    impact_amt     = round(total_turnover * market_impact,  2)
    total_cost     = round(total_turnover * cost_rate,      2)

    return {
        "commission":     commission_amt,
        "slippage":       slippage_amt,
        "market_impact":  impact_amt,
        "total":          total_cost,
        "total_turnover": round(total_turnover, 2),
        "cost_rate":      round(cost_rate, 6),
    }


def is_cost_effective(
    cost_estimate:  dict,
    expected_gain:  float,
    min_gain_ratio: float = 3.0,
) -> bool:
    """
    判断再平衡是否划算（预期收益/成本 >= min_gain_ratio）。

    Parameters
    ----------
    cost_estimate  : estimate_rebalance_cost() 返回值
    expected_gain  : 再平衡预期收益（金额）
    min_gain_ratio : 最小收益/成本比（默认 3x）

    Returns
    -------
    bool
    """
    total_cost = cost_estimate.get("total", 0.0)
    if total_cost < 1e-6:
        return True
    return (expected_gain / total_cost) >= min_gain_ratio
