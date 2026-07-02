"""
alpha_factory_2/utils/scoring_utils.py  (Phase 3)

Alpha 评分工具函数。

实现：
  - compute_ic            Pearson 相关系数
  - compute_rank_ic       Spearman 排名相关系数
  - compute_ic_series     滚动期的 IC 序列
  - compute_stability     IC 信息比率 IR = mean(IC)/std(IC)
  - compute_turnover      截面换手率
  - compute_total_score   综合评分公式

❌ 无 IO，无网络，无线程，纯计算
"""

from __future__ import annotations

import math
from typing import Sequence


# ─────────────────────────────────────────────────────────────────────────────
#  基础统计工具（不依赖 numpy / scipy）
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


def _rank(xs: Sequence[float]) -> list[float]:
    """将序列转为排名（1-based，允许平均秩）。"""
    n      = len(xs)
    pairs  = sorted(enumerate(xs), key=lambda t: t[1])
    ranks  = [0.0] * n
    i      = 0
    while i < n:
        j = i
        while j < n - 1 and pairs[j + 1][1] == pairs[i][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[pairs[k][0]] = avg_rank
        i = j + 1
    return ranks


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float:
    """Pearson 相关系数（返回 0 如输入长度不足或方差为零）。"""
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    xs, ys = xs[:n], ys[:n]
    mx, my = _mean(xs), _mean(ys)
    num    = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx     = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy     = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx < 1e-12 or sy < 1e-12:
        return 0.0
    return num / (sx * sy)


# ─────────────────────────────────────────────────────────────────────────────
#  评分指标
# ─────────────────────────────────────────────────────────────────────────────

def compute_ic(
    alpha_values: Sequence[float],
    returns:      Sequence[float],
) -> float:
    """
    IC — Pearson 相关系数（Alpha 信号与下期收益）。

    Parameters
    ----------
    alpha_values : 截面 Alpha 信号（N 个标的）
    returns      : 对应的下期收益率

    Returns
    -------
    float  [-1, 1]，越高越好，正值代表正向预测力
    """
    return round(_pearson(alpha_values, returns), 6)


def compute_rank_ic(
    alpha_values: Sequence[float],
    returns:      Sequence[float],
) -> float:
    """
    RankIC — Spearman 排名相关系数（更鲁棒，对异常值不敏感）。
    """
    if len(alpha_values) < 2 or len(returns) < 2:
        return 0.0
    n      = min(len(alpha_values), len(returns))
    ra     = _rank(alpha_values[:n])
    rr     = _rank(returns[:n])
    return round(_pearson(ra, rr), 6)


def compute_ic_series(
    alpha_panel:   list[Sequence[float]],
    returns_panel: list[Sequence[float]],
    use_rank:      bool = False,
) -> list[float]:
    """
    计算时序 IC 序列（每期一个 IC 值）。

    Parameters
    ----------
    alpha_panel   : list of 截面 Alpha 信号（每期一个列表）
    returns_panel : 对应的下期截面收益率
    use_rank      : True 则计算 RankIC

    Returns
    -------
    list[float]  与输入等长的 IC 序列
    """
    fn  = compute_rank_ic if use_rank else compute_ic
    n   = min(len(alpha_panel), len(returns_panel))
    return [fn(alpha_panel[i], returns_panel[i]) for i in range(n)]


def compute_stability(ic_series: Sequence[float]) -> float:
    """
    Stability — IC 信息比率 IR = mean(IC) / std(IC)。

    IR > 0.5 视为稳定，IR > 1.0 视为优秀。

    Returns
    -------
    float  IR 值（未截断，可能超出 [0,1]），0 表示无数据或方差为零
    """
    if len(ic_series) < 2:
        return 0.0
    std = _std(ic_series, ddof=1)
    if std < 1e-12:
        return 0.0
    ir = _mean(ic_series) / std
    return round(ir, 6)


def compute_turnover(
    positions_t:  Sequence[float],
    positions_t1: Sequence[float],
) -> float:
    """
    Turnover — 截面换手率。

    定义：sum(|w_t - w_{t-1}|) / 2，值域 [0, 1]。
    0 = 完全不换手，1 = 完全翻转。

    Parameters
    ----------
    positions_t   : t 期权重向量（已归一化）
    positions_t1  : t+1 期权重向量

    Returns
    -------
    float  [0, 1]，越小换手率越低
    """
    n = min(len(positions_t), len(positions_t1))
    if n == 0:
        return 0.0
    diff = sum(abs(positions_t1[i] - positions_t[i]) for i in range(n))
    return round(min(diff / 2.0, 1.0), 6)


def compute_turnover_series(
    positions_series: list[Sequence[float]],
) -> list[float]:
    """
    计算逐期换手率序列。

    Parameters
    ----------
    positions_series : 每期权重向量列表（长度 T）

    Returns
    -------
    list[float]  长度 T-1 的换手率序列
    """
    result = []
    for i in range(1, len(positions_series)):
        result.append(compute_turnover(positions_series[i - 1], positions_series[i]))
    return result


def compute_mean_turnover(
    positions_series: list[Sequence[float]],
) -> float:
    """平均换手率（换手率序列的均值）。"""
    ts = compute_turnover_series(positions_series)
    return round(_mean(ts), 6) if ts else 0.0


def compute_total_score(
    ic:         float,
    stability:  float,
    decay:      float,
    turnover:   float,
    weights:    tuple[float, float, float, float] = (0.3, 0.3, 0.2, 0.2),
) -> float:
    """
    综合评分公式：

        Total = IC * 0.3 + Stability_norm * 0.3
              + Decay_norm * 0.2 + Turnover_norm * 0.2

    各维度先归一化到 [0, 1]：
      IC_norm        = clip((IC + 0.1) / 0.2, 0, 1)   实用 IC 范围 [-0.1, 0.1]
      Stability_norm = clip(IR / 2.0, 0, 1)             IR 0~2 映射
      Decay_norm     = clip(decay / 20.0, 0, 1)         半衰期 0~20 期
      Turnover_norm  = clip(1 - turnover, 0, 1)          低换手 = 高分

    Parameters
    ----------
    ic        : Pearson IC（通常 -0.1 ~ 0.1）
    stability : IR（通常 0 ~ 2）
    decay     : IC 半衰期（交易日数，越大越好）
    turnover  : 平均换手率（0~1，越小越好）
    weights   : (w_ic, w_stability, w_decay, w_turnover)

    Returns
    -------
    float  [0, 1]，越高越好
    """
    w_ic, w_stab, w_decay, w_turn = weights

    ic_norm    = max(0.0, min(1.0, (ic + 0.1) / 0.2))
    stab_norm  = max(0.0, min(1.0, stability / 2.0))
    decay_norm = max(0.0, min(1.0, decay / 20.0))
    turn_norm  = max(0.0, min(1.0, 1.0 - turnover))

    score = (
        ic_norm    * w_ic
        + stab_norm  * w_stab
        + decay_norm * w_decay
        + turn_norm  * w_turn
    )
    return round(score, 6)
