"""
research_validation/utils/correlation_utils.py

相关性与稳定性工具函数（Phase 4 实现）。

所有函数为纯函数，无副作用，仅依赖标准库。
❌ 不允许引入机器学习模型。
"""

from __future__ import annotations

import math
from .stats_utils import _mean, _std, _pearson, _rank


# ─────────────────────────────────────────────────────────────────────────────
#  自相关
# ─────────────────────────────────────────────────────────────────────────────

def calc_autocorr(
    series: list[float],
    lag:    int = 1,
) -> float:
    """
    计算时间序列的自相关系数（Pearson）。

    Parameters
    ----------
    series : 时间序列（如 rolling IC）
    lag    : 滞后阶数（默认 1）

    Returns
    -------
    float  自相关系数 ∈ [-1, 1]，序列过短时返回 0.0
    """
    n = len(series)
    if n <= lag + 1:
        return 0.0
    xs = series[:n - lag]
    ys = series[lag:]
    return _pearson(xs, ys)


def calc_autocorr_series(
    series: list[float],
    max_lag: int = 10,
) -> list[float]:
    """
    计算 lag=1..max_lag 的自相关系数序列。

    Returns
    -------
    list[float]  长度为 max_lag，index 0 对应 lag=1
    """
    return [calc_autocorr(series, lag) for lag in range(1, max_lag + 1)]


# ─────────────────────────────────────────────────────────────────────────────
#  因子截面相关性
# ─────────────────────────────────────────────────────────────────────────────

def calc_factor_correlation(
    factor_a: dict[str, float],
    factor_b: dict[str, float],
) -> float:
    """
    计算两个因子截面值的 Pearson 相关系数。

    Parameters
    ----------
    factor_a : {symbol: value}
    factor_b : {symbol: value}

    Returns
    -------
    float  Pearson 相关系数 ∈ [-1, 1]，公共标的 < 2 时返回 0.0
    """
    common = [s for s in factor_a if s in factor_b]
    if len(common) < 2:
        return 0.0
    xs = [factor_a[s] for s in common]
    ys = [factor_b[s] for s in common]
    return _pearson(xs, ys)


def calc_factor_rank_correlation(
    factor_a: dict[str, float],
    factor_b: dict[str, float],
) -> float:
    """
    计算两个因子截面值的 Spearman 秩相关系数。

    Returns
    -------
    float  Spearman ρ ∈ [-1, 1]
    """
    common = [s for s in factor_a if s in factor_b]
    if len(common) < 2:
        return 0.0
    xs = _rank([factor_a[s] for s in common])
    ys = _rank([factor_b[s] for s in common])
    return _pearson(xs, ys)


# ─────────────────────────────────────────────────────────────────────────────
#  IC 衰减
# ─────────────────────────────────────────────────────────────────────────────

def calc_ic_decay(
    factor_cs:  list[dict[str, float]],
    return_cs:  list[dict[str, float]],
    max_lag:    int = 20,
    use_rank:   bool = False,
) -> list[float]:
    """
    计算因子 IC 衰减序列（lag=1 到 max_lag）。

    每个 lag=k 的 IC：因子值 factor_cs[t] 与 k 期后收益 return_cs[t+k] 的截面相关性，
    再对所有可用 t 取均值。

    Parameters
    ----------
    factor_cs : 因子截面序列
    return_cs : 收益截面序列（与 factor_cs 等长）
    max_lag   : 最大滞后期数
    use_rank  : True = RankIC，False = IC

    Returns
    -------
    list[float]  长度为 max_lag，index 0 对应 lag=1
    """
    from .stats_utils import calc_ic, calc_rank_ic
    ic_fn = calc_rank_ic if use_rank else calc_ic

    n = len(factor_cs)
    decay = []
    for lag in range(1, max_lag + 1):
        ics = []
        for t in range(n - lag):
            ic_val = ic_fn(factor_cs[t], return_cs[t + lag])
            ics.append(ic_val)
        decay.append(_mean(ics) if ics else 0.0)
    return decay


def calc_ic_decay_halflife(decay_series: list[float]) -> float:
    """
    估算 IC 衰减半衰期（IC 降至 lag=1 值的一半所需的滞后期数）。

    使用线性插值，若 IC 不单调衰减则返回 max_lag（表示衰减极慢）。

    Returns
    -------
    float  半衰期（期数），最小 1.0，最大 len(decay_series)
    """
    if not decay_series or abs(decay_series[0]) < 1e-9:
        return float(len(decay_series))

    target = decay_series[0] / 2.0
    sign   = 1.0 if decay_series[0] > 0 else -1.0

    for i in range(1, len(decay_series)):
        curr = decay_series[i]
        prev = decay_series[i - 1]
        # IC 绝对值降至 target（或穿越 0）
        if sign * curr <= sign * target:
            # 线性插值
            if abs(prev - curr) < 1e-12:
                return float(i + 1)
            frac = (prev - target) / (prev - curr)
            return float(i) + frac

    return float(len(decay_series))


# ─────────────────────────────────────────────────────────────────────────────
#  滚动相关性
# ─────────────────────────────────────────────────────────────────────────────

def calc_rolling_correlation(
    series_a: list[float],
    series_b: list[float],
    window:   int = 60,
) -> list[float]:
    """
    计算两个时间序列的滚动 Pearson 相关系数。

    Parameters
    ----------
    series_a : 时间序列 A
    series_b : 时间序列 B（等长）
    window   : 滚动窗口长度

    Returns
    -------
    list[float]  长度与输入相同；前 window-1 个元素为 float('nan')
    """
    n = len(series_a)
    if n != len(series_b):
        raise ValueError("series_a 与 series_b 长度必须一致。")

    result = [float('nan')] * n
    for i in range(window - 1, n):
        xa = series_a[i - window + 1 : i + 1]
        xb = series_b[i - window + 1 : i + 1]
        result[i] = _pearson(xa, xb)
    return result


def calc_rolling_ic(
    factor_cs:  list[dict[str, float]],
    return_cs:  list[dict[str, float]],
    window:     int  = 60,
    use_rank:   bool = False,
) -> list[float]:
    """
    计算滚动窗口 IC 均值序列。

    每个输出点 i = window-1..n-1，对应 factor_cs[i-window+1:i+1] 窗口内的 IC 均值。
    前 window-1 个元素为 float('nan')。

    Parameters
    ----------
    factor_cs : 因子截面序列
    return_cs : 收益截面序列
    window    : 滚动窗口长度
    use_rank  : True = RankIC

    Returns
    -------
    list[float]  长度与输入相同
    """
    from .stats_utils import calc_ic, calc_rank_ic
    ic_fn = calc_rank_ic if use_rank else calc_ic

    n = len(factor_cs)
    if n != len(return_cs):
        raise ValueError("factor_cs 与 return_cs 长度必须一致。")

    # 先计算每期点 IC
    spot_ics = [ic_fn(factor_cs[i], return_cs[i]) for i in range(n)]

    result = [float('nan')] * n
    for i in range(window - 1, n):
        window_ics = spot_ics[i - window + 1 : i + 1]
        result[i] = _mean(window_ics)
    return result


# ─────────────────────────────────────────────────────────────────────────────
#  稳定性评级
# ─────────────────────────────────────────────────────────────────────────────

def classify_ic_stability(
    rolling_ic: list[float],
    threshold_strong: float = 0.03,
    threshold_weak:   float = 0.01,
) -> str:
    """
    基于滚动 IC 序列评定因子稳定性等级。

    规则：
      STRONG  : 均值 > threshold_strong 且正向比 > 70%
      MODERATE: 均值 > threshold_weak   且正向比 > 55%
      WEAK    : 均值 > 0               且正向比 > 50%
      UNSTABLE: 其余

    Returns
    -------
    str  "STRONG" | "MODERATE" | "WEAK" | "UNSTABLE"
    """
    valid = [x for x in rolling_ic if not math.isnan(x)]
    if not valid:
        return "UNSTABLE"

    mean_ic  = _mean(valid)
    pos_rate = sum(1 for x in valid if x > 0) / len(valid)

    if mean_ic > threshold_strong and pos_rate > 0.70:
        return "STRONG"
    if mean_ic > threshold_weak and pos_rate > 0.55:
        return "MODERATE"
    if mean_ic > 0 and pos_rate > 0.50:
        return "WEAK"
    return "UNSTABLE"
