"""
capital_allocation_ai/utils/capital_utils.py  (Phase 3)

资本分配工具函数。

实现：
  - normalize_scores          评分归一化为分配比例
  - apply_capital_constraints 上下限约束
  - compute_flow_direction    资金流向判断
  - compute_concentration     HHI 集中度
  - compute_allocation_delta  本期与上期分配差异
  - build_allocation_summary  汇总统计

❌ 无 IO，无网络，无线程，纯计算
"""

from __future__ import annotations

import math
from typing import Sequence


# ─────────────────────────────────────────────────────────────────────────────
#  比例归一化
# ─────────────────────────────────────────────────────────────────────────────

def normalize_scores(
    scores:   dict[str, float],
    min_clip: float = 0.0,
) -> dict[str, float]:
    """
    将评分字典归一化为分配比例（和严格为 1）。

    负分或低于 min_clip 的 Alpha 直接截为 0（不参与分配）。

    Parameters
    ----------
    scores   : {alpha_id: score}
    min_clip : 低于此分数的 Alpha 不参与分配

    Returns
    -------
    dict  {alpha_id: ratio}  ratio ∈ [0, 1]，和为 1
    """
    if not scores:
        return {}
    clipped = {k: max(v, min_clip) for k, v in scores.items()}
    total   = sum(clipped.values())
    if total < 1e-12:
        n = len(scores)
        return {k: round(1.0 / n, 8) for k in scores}
    return {k: round(v / total, 8) for k, v in clipped.items()}


# ─────────────────────────────────────────────────────────────────────────────
#  资金约束
# ─────────────────────────────────────────────────────────────────────────────

def apply_capital_constraints(
    allocations:  dict[str, float],
    max_ratio:    float = 0.30,
    min_ratio:    float = 0.005,
    n_iterations: int   = 50,
    tol:          float = 1e-9,
) -> dict[str, float]:
    """
    对资金分配比例施加上下限约束（水位线迭代重归一化）。

    算法：
      1. 先将低于 min_ratio 的 Alpha 永久移除（置 0，不再参与分配）
      2. 重归一化到剩余 Active Alpha
      3. 对超过 max_ratio 的 Alpha 固定为 max_ratio，
         将溢出比例按原权重重分配给仍未超限的 Active Alpha
      4. 重复 3 直到无超限为止

    Returns
    -------
    dict  {alpha_id: ratio}，满足约束，和为 1
    """
    if not allocations:
        return {}

    # 初始化：归一化输入，保留非负值
    result = {k: max(v, 0.0) for k, v in allocations.items()}
    total = sum(result.values())
    if total < 1e-12:
        return {k: 0.0 for k in allocations}
    result = {k: v / total for k, v in result.items()}

    # Step 1: 永久移除低于 min_ratio 的 Alpha（只做一次）
    excluded: set = set()
    for k, v in result.items():
        if 0.0 < v < min_ratio:
            excluded.add(k)
    for k in excluded:
        result[k] = 0.0

    # 重归一化（仅 active Alpha）
    total = sum(result.values())
    if total < 1e-12:
        return result
    result = {k: (v / total if k not in excluded else 0.0)
              for k, v in result.items()}

    # Step 2: 水位线迭代（只对 active Alpha 进行）
    for _ in range(n_iterations):
        active  = {k: v for k, v in result.items() if k not in excluded and v > 0}
        capped  = {k for k, v in active.items() if v >= max_ratio - tol}
        free    = {k: v for k, v in active.items() if k not in capped}

        if not capped:
            break   # 已收敛

        fixed_sum = len(capped) * max_ratio
        remainder = 1.0 - fixed_sum
        free_sum  = sum(free.values())

        if remainder < 0.0:
            # 超限项占满，free Alpha 全部清零
            for k in capped:
                result[k] = max_ratio
            for k in free:
                result[k] = 0.0
                excluded.add(k)
            break

        if free_sum < 1e-12:
            for k in capped:
                result[k] = max_ratio
            break

        scale = remainder / free_sum
        for k in capped:
            result[k] = max_ratio
        for k in free:
            result[k] = free[k] * scale

        # 检查移除新产生的低于 min_ratio 项
        new_excluded = {k for k in free if result[k] > 0 and result[k] < min_ratio}
        for k in new_excluded:
            result[k] = 0.0
            excluded.add(k)
        if new_excluded:
            # 需要重归一化再继续
            total = sum(v for k, v in result.items() if k not in excluded)
            if total > 1e-12:
                for k in result:
                    if k not in excluded:
                        result[k] = result[k] / total

        if all(v <= max_ratio + tol for v in result.values()):
            break

    # 最终归一化消除浮点误差
    total = sum(result.values())
    if total > 1e-12:
        result = {k: round(v / total, 8) for k, v in result.items()}

    return result


def compute_flow_direction(
    prev:      float,
    curr:      float,
    threshold: float = 0.005,
) -> str:
    """
    计算资金流向。

    Parameters
    ----------
    prev      : 上期分配比例
    curr      : 本期分配比例
    threshold : 变动阈值（小于此变动视为 hold）

    Returns
    -------
    str  "increase" | "decrease" | "transfer" | "hold"
    """
    delta = curr - prev
    if abs(delta) < threshold:
        return "hold"
    if prev < 1e-9 and curr > 1e-9:
        return "transfer"    # 新进入
    if curr < 1e-9 and prev > 1e-9:
        return "transfer"    # 完全退出
    return "increase" if delta > 0 else "decrease"


def compute_flow_directions(
    prev_ratios: dict[str, float],
    curr_ratios: dict[str, float],
    threshold:   float = 0.005,
) -> dict[str, str]:
    """
    批量计算资金流向。

    Returns
    -------
    dict  {alpha_id: flow_direction_str}
    """
    all_ids = set(prev_ratios) | set(curr_ratios)
    return {
        aid: compute_flow_direction(
            prev_ratios.get(aid, 0.0),
            curr_ratios.get(aid, 0.0),
            threshold,
        )
        for aid in all_ids
    }


# ─────────────────────────────────────────────────────────────────────────────
#  集中度
# ─────────────────────────────────────────────────────────────────────────────

def compute_concentration(
    allocations: dict[str, float],
) -> float:
    """
    计算资金集中度（Herfindahl-Hirschman Index，HHI）。

    HHI = sum(ratio_i ^ 2)
    HHI = 1.0 → 完全集中（单一 Alpha）
    HHI = 1/N → 完全分散（均匀分配）

    Returns
    -------
    float  [1/N, 1.0]
    """
    if not allocations:
        return 0.0
    return round(sum(v ** 2 for v in allocations.values()), 6)


def compute_effective_n(allocations: dict[str, float]) -> float:
    """
    有效 Alpha 数量 = 1 / HHI。

    完全均匀分配时等于实际 Alpha 数量。

    Returns
    -------
    float  有效 Alpha 数量
    """
    hhi = compute_concentration(allocations)
    return round(1.0 / hhi, 2) if hhi > 1e-12 else 0.0


# ─────────────────────────────────────────────────────────────────────────────
#  分配差异
# ─────────────────────────────────────────────────────────────────────────────

def compute_allocation_delta(
    prev_ratios: dict[str, float],
    curr_ratios: dict[str, float],
) -> dict[str, float]:
    """
    计算本期与上期分配比例的差异（delta）。

    Returns
    -------
    dict  {alpha_id: delta_ratio}（正=增配，负=减配）
    """
    all_ids = set(prev_ratios) | set(curr_ratios)
    return {
        aid: round(
            curr_ratios.get(aid, 0.0) - prev_ratios.get(aid, 0.0), 8
        )
        for aid in all_ids
    }


def compute_total_turnover(
    prev_ratios: dict[str, float],
    curr_ratios: dict[str, float],
) -> float:
    """
    计算分配换手率（= 调整总量 / 2，值域 [0, 1]）。

    Returns
    -------
    float  [0, 1]，0 = 无变化，1 = 完全翻转
    """
    delta = compute_allocation_delta(prev_ratios, curr_ratios)
    return round(sum(abs(v) for v in delta.values()) / 2.0, 6)


# ─────────────────────────────────────────────────────────────────────────────
#  汇总
# ─────────────────────────────────────────────────────────────────────────────

def build_allocation_summary(
    ratios:        dict[str, float],
    total_capital: float,
    prev_ratios:   dict[str, float] | None = None,
) -> dict:
    """
    构建资金分配汇总统计。

    Parameters
    ----------
    ratios        : 当前分配比例
    total_capital : 总资金
    prev_ratios   : 上期分配比例（用于计算换手率）

    Returns
    -------
    dict  包含 n_active, concentration, effective_n, turnover, ...
    """
    active      = {k: v for k, v in ratios.items() if v > 1e-8}
    concentration = compute_concentration(active)
    effective_n   = compute_effective_n(active)
    turnover = compute_total_turnover(
        prev_ratios or {}, ratios
    ) if prev_ratios is not None else None

    top1 = max(active.values()) if active else 0.0
    avg  = sum(active.values()) / len(active) if active else 0.0

    return {
        "n_active":      len(active),
        "n_total":       len(ratios),
        "total_capital": round(total_capital, 2),
        "concentration": round(concentration, 6),
        "effective_n":   round(effective_n,   2),
        "top1_ratio":    round(top1,           6),
        "avg_ratio":     round(avg,            6),
        "turnover":      round(turnover, 6) if turnover is not None else None,
    }
