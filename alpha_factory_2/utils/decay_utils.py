"""
alpha_factory_2/utils/decay_utils.py  (Phase 3)

Alpha IC Decay 分析工具。

实现：
  - compute_ic_decay      不同持有期的 IC 序列（Decay 曲线）
  - decay_half_life       IC 半衰期（IC 衰减到初始值 50% 所需期数）
  - is_decayed            Alpha 是否已充分衰减
  - decay_score           将半衰期转换为评分维度

❌ 无 IO，无网络，无线程，纯计算
"""

from __future__ import annotations

import math
from typing import Sequence

from .scoring_utils import compute_ic, compute_rank_ic, _mean


# ─────────────────────────────────────────────────────────────────────────────
#  IC Decay 曲线
# ─────────────────────────────────────────────────────────────────────────────

def compute_ic_decay(
    alpha_values:   Sequence[float],
    returns_series: list[Sequence[float]],
    max_lag:        int  = 20,
    use_rank:       bool = False,
) -> list[float]:
    """
    计算 IC Decay 曲线（不同持有期的 IC）。

    Parameters
    ----------
    alpha_values   : 截面 Alpha 信号（N 个标的）
    returns_series : list of 持有期收益率序列，
                     returns_series[k] 对应 lag=k+1 的收益率向量
    max_lag        : 最大滞后期（若 returns_series 长度不足则补零）
    use_rank       : True 则计算 RankIC

    Returns
    -------
    list[float]  长度 max_lag 的 IC 序列，ic_decay[0] = lag-1 IC
    """
    fn     = compute_rank_ic if use_rank else compute_ic
    result = []
    for lag in range(max_lag):
        if lag < len(returns_series) and len(returns_series[lag]) > 1:
            ic = fn(alpha_values, returns_series[lag])
        else:
            ic = 0.0
        result.append(ic)
    return result


def compute_ic_decay_from_panel(
    alpha_panel:   list[Sequence[float]],
    returns_panel: list[Sequence[float]],
    max_lag:       int  = 20,
    use_rank:      bool = False,
) -> list[float]:
    """
    从面板数据计算平均 IC Decay 曲线。

    Parameters
    ----------
    alpha_panel   : 每期截面 Alpha 信号列表（T 期）
    returns_panel : 每期截面收益率列表（T 期）
    max_lag       : 最大滞后期

    Returns
    -------
    list[float]  长度 max_lag 的平均 IC Decay 曲线
    """
    fn = compute_rank_ic if use_rank else compute_ic
    T  = min(len(alpha_panel), len(returns_panel))
    decay_matrix: list[list[float]] = [[] for _ in range(max_lag)]

    for t in range(T):
        for lag in range(1, max_lag + 1):
            future = t + lag
            if future < len(returns_panel):
                ic = fn(alpha_panel[t], returns_panel[future])
                decay_matrix[lag - 1].append(ic)

    return [
        round(_mean(col), 6) if col else 0.0
        for col in decay_matrix
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  半衰期
# ─────────────────────────────────────────────────────────────────────────────

def decay_half_life(ic_decay: Sequence[float]) -> float:
    """
    计算 IC 半衰期（IC 衰减至初始值 50% 所需的滞后期数）。

    算法：
      1. 取 ic_decay[0] 为基准 IC
      2. 从 lag=1 开始，找第一个 |IC[lag]| <= |IC[0]| * 0.5 的位置
      3. 若序列中未找到，则返回 max_lag（信号持续有效）

    Parameters
    ----------
    ic_decay : IC Decay 曲线（lag=1, 2, ...）

    Returns
    -------
    float  半衰期（交易日数），值越大 Alpha 越持久
    """
    if not ic_decay or abs(ic_decay[0]) < 1e-12:
        return 0.0

    base    = abs(ic_decay[0])
    target  = base * 0.5
    max_lag = len(ic_decay)

    for lag in range(1, max_lag):
        if abs(ic_decay[lag]) <= target:
            # 线性插值使结果更精确
            prev = abs(ic_decay[lag - 1])
            curr = abs(ic_decay[lag])
            if prev > curr:
                frac = (prev - target) / (prev - curr)
                return round(lag - 1 + frac, 2)
            return float(lag)

    return float(max_lag)


def is_decayed(ic_decay: Sequence[float], threshold: float = 0.02) -> bool:
    """
    判断 Alpha 是否已充分衰减。

    若 ic_decay 序列中超过一半的值的绝对值低于 threshold，
    则认为 Alpha 已衰减。

    Parameters
    ----------
    ic_decay  : IC Decay 曲线
    threshold : IC 有效阈值（默认 0.02）

    Returns
    -------
    bool  True = 已衰减（Alpha 预测力已丧失）
    """
    if not ic_decay:
        return True
    significant = sum(1 for v in ic_decay if abs(v) >= threshold)
    return significant < len(ic_decay) / 2


def decay_score(half_life: float, max_lag: float = 20.0) -> float:
    """
    将半衰期转换为 [0, 1] 评分（供综合评分使用）。

    half_life = 0      -> 0.0
    half_life = max_lag -> 1.0

    Parameters
    ----------
    half_life : IC 半衰期（交易日数）
    max_lag   : 归一化参考值（默认 20 个交易日）

    Returns
    -------
    float  [0, 1]
    """
    if half_life <= 0:
        return 0.0
    return round(min(half_life / max_lag, 1.0), 6)
