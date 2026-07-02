"""
capital_allocation_ai/utils/scoring_utils.py  (Phase 2)

Alpha 资本评分工具函数。

资本评分公式：
    Capital Score = IC * 0.3 + Stability * 0.25 + Capacity * 0.25 + Decay * 0.2

所有函数均为纯计算，无 IO、无网络、无线程。
"""

from __future__ import annotations

import math
from typing import Sequence


# ─────────────────────────────────────────────────────────────────────────────
#  基础统计工具
# ─────────────────────────────────────────────────────────────────────────────

def _mean(xs: Sequence[float]) -> float:
    n = len(xs)
    return sum(xs) / n if n else 0.0


def _std(xs: Sequence[float], ddof: int = 1) -> float:
    n = len(xs)
    if n <= ddof:
        return 0.0
    m   = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (n - ddof)
    return math.sqrt(var)


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


# ─────────────────────────────────────────────────────────────────────────────
#  评分维度计算
# ─────────────────────────────────────────────────────────────────────────────

def compute_ic_mean(ic_series: Sequence[float]) -> float:
    """
    计算 IC 均值（典型范围 -0.1 ~ 0.1）。

    Parameters
    ----------
    ic_series : 时序 IC 列表

    Returns
    -------
    float  IC 均值
    """
    if not ic_series:
        return 0.0
    return round(_mean(list(ic_series)), 6)


def compute_stability(ic_series: Sequence[float]) -> float:
    """
    计算 IC 稳定性 = IR = mean(IC) / std(IC)。

    典型范围 0 ~ 2，越高越稳定。

    Returns
    -------
    float  IR 值（未截断）
    """
    if len(ic_series) < 2:
        return 0.0
    std = _std(list(ic_series), ddof=1)
    if std < 1e-12:
        return 0.0
    return round(_mean(list(ic_series)) / std, 6)


def estimate_capacity(
    ic_mean:      float,
    volatility:   float,
    n_symbols:    int   = 100,
    capital_base: float = 1_000_000.0,
) -> float:
    """
    估算 Alpha 容量评分（0~1）。

    简化模型：
        capacity_raw = |IC| * sqrt(N) * (1 / (1 + vol))
        capacity_norm = clip(capacity_raw / 1.0, 0, 1)

    高 IC、多标的、低波动 → 高容量评分。

    Parameters
    ----------
    ic_mean     : IC 均值（绝对值衡量方向无关的信号强度）
    volatility  : 年化波动率（0 ~ 1）
    n_symbols   : 截面标的数量
    capital_base: 参考资金规模（未来 Phase 3 可用于实际容量计算）

    Returns
    -------
    float  [0, 1]
    """
    if n_symbols <= 0:
        return 0.0
    ic_abs = abs(ic_mean)
    vol_factor = 1.0 / (1.0 + max(volatility, 0.0))
    raw = ic_abs * math.sqrt(n_symbols) * vol_factor
    return round(_clip(raw / 1.0, 0.0, 1.0), 6)


def compute_decay_score(
    ic_decay_curve: Sequence[float],
    max_lag:        float = 20.0,
) -> float:
    """
    计算 IC 衰减评分（0~1）。

    算法：
      1. 找到 IC 衰减至初始值 50% 的半衰期
      2. half_life / max_lag → 归一化到 [0, 1]

    较大的半衰期 → 信号持久 → 高衰减评分。

    Parameters
    ----------
    ic_decay_curve : IC Decay 曲线（lag=1, 2, ...）
    max_lag        : 归一化参考最大滞后期（默认 20 个交易日）

    Returns
    -------
    float  [0, 1]
    """
    if not ic_decay_curve or abs(ic_decay_curve[0]) < 1e-12:
        return 0.0

    base   = abs(ic_decay_curve[0])
    target = base * 0.5
    n      = len(ic_decay_curve)

    half_life = float(n)   # 若未找到衰减点，返回 max_lag
    for lag in range(1, n):
        if abs(ic_decay_curve[lag]) <= target:
            prev = abs(ic_decay_curve[lag - 1])
            curr = abs(ic_decay_curve[lag])
            if prev > curr:
                frac = (prev - target) / (prev - curr)
                half_life = lag - 1 + frac
            else:
                half_life = float(lag)
            break

    return round(_clip(half_life / max_lag, 0.0, 1.0), 6)


def compute_sharpe(
    returns:   Sequence[float],
    risk_free: float = 0.0,
    periods:   int   = 252,
) -> float:
    """
    计算年化 Sharpe 比率。

    Sharpe = mean(excess_returns) / std(excess_returns) * sqrt(periods)

    Parameters
    ----------
    returns   : 日度收益率序列
    risk_free : 无风险收益率（日度，默认 0）
    periods   : 年化系数（默认 252 个交易日）

    Returns
    -------
    float  年化 Sharpe（未截断，可能为负）
    """
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free for r in returns]
    std    = _std(excess, ddof=1)
    if std < 1e-12:
        return 0.0
    return round(_mean(excess) / std * math.sqrt(periods), 6)


# ─────────────────────────────────────────────────────────────────────────────
#  综合资本评分
# ─────────────────────────────────────────────────────────────────────────────

def compute_capital_score(
    ic_mean:   float,
    stability: float,
    capacity:  float,
    decay:     float,
    weights:   tuple[float, float, float, float] = (0.3, 0.25, 0.25, 0.2),
) -> float:
    """
    综合资本评分公式：

        Capital Score = IC_norm * 0.30
                      + Stability_norm * 0.25
                      + Capacity_norm  * 0.25
                      + Decay_norm     * 0.20

    各维度归一化至 [0, 1]：
      IC_norm        = clip((ic_mean + 0.1) / 0.2, 0, 1)   实用 IC 范围 [-0.1, 0.1]
      Stability_norm = clip(stability / 2.0, 0, 1)           IR 0~2 映射
      Capacity_norm  = capacity（已 [0,1]）
      Decay_norm     = decay（已 [0,1]）

    Parameters
    ----------
    ic_mean   : IC 均值
    stability : IR
    capacity  : 容量评分 [0, 1]
    decay     : 衰减评分 [0, 1]
    weights   : (w_ic, w_stability, w_capacity, w_decay)

    Returns
    -------
    float  [0, 1]，越高越好
    """
    w_ic, w_stab, w_cap, w_decay = weights

    ic_norm   = _clip((ic_mean + 0.1) / 0.2, 0.0, 1.0)
    stab_norm = _clip(stability / 2.0,        0.0, 1.0)
    cap_norm  = _clip(capacity,               0.0, 1.0)
    dec_norm  = _clip(decay,                  0.0, 1.0)

    score = (
        ic_norm   * w_ic
        + stab_norm * w_stab
        + cap_norm  * w_cap
        + dec_norm  * w_decay
    )
    return round(score, 6)


def normalize_capital_scores(
    scores: dict[str, float],
) -> dict[str, float]:
    """
    将资本评分字典归一化（绝对值总和为 1），用于资金比例分配。

    Parameters
    ----------
    scores : {alpha_id: capital_score}

    Returns
    -------
    dict  {alpha_id: ratio}  各 Alpha 应分配的资金比例
    """
    if not scores:
        return {}
    total = sum(max(v, 0.0) for v in scores.values())
    if total < 1e-12:
        n = len(scores)
        return {k: round(1.0 / n, 8) for k in scores}
    return {k: round(max(v, 0.0) / total, 8) for k, v in scores.items()}


def rank_alphas_by_score(
    scores: dict[str, float],
) -> list[tuple[str, float]]:
    """
    按资本评分降序排列 Alpha。

    Returns
    -------
    list of (alpha_id, score) 有序列表
    """
    return sorted(scores.items(), key=lambda t: t[1], reverse=True)
