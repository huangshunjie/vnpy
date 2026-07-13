"""
research_validation/utils/stats_utils.py

统计工具函数（Phase 2 实现）。

所有函数为纯函数，无副作用，无外部依赖（仅标准库）。
❌ 不允许引入机器学习模型。
❌ 不允许连接任何交易接口。
"""

from __future__ import annotations

import math


# ─────────────────────────────────────────────────────────────────────────────
#  基础统计工具
# ─────────────────────────────────────────────────────────────────────────────

def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: list[float], ddof: int = 1) -> float:
    if len(xs) < ddof + 1:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - ddof)
    return math.sqrt(var)


def _pearson(xs: list[float], ys: list[float]) -> float:
    """Pearson 相关系数（纯 Python）。"""
    n = len(xs)
    if n < 2:
        return 0.0
    mx, my = _mean(xs), _mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx  = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy  = math.sqrt(sum((y - my) ** 2 for y in ys))
    denom = dx * dy
    if denom < 1e-12:
        return 0.0
    return num / denom


def _rank(xs: list[float]) -> list[float]:
    """升序秩次（平均秩法处理并列）。"""
    indexed = sorted(enumerate(xs), key=lambda t: t[1])
    ranks   = [0.0] * len(xs)
    i = 0
    while i < len(indexed):
        j = i
        while j < len(indexed) - 1 and indexed[j + 1][1] == indexed[j][1]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k][0]] = avg_rank
        i = j + 1
    return ranks


# ─────────────────────────────────────────────────────────────────────────────
#  公开接口
# ─────────────────────────────────────────────────────────────────────────────

def calc_ic(
    factor_values:   dict[str, float],
    forward_returns: dict[str, float],
) -> float:
    """
    截面 IC（Pearson 相关系数）。

    Parameters
    ----------
    factor_values    : {symbol: factor_value}
    forward_returns  : {symbol: forward_return}

    Returns
    -------
    float  IC ∈ [-1, 1]，公共股票 < 2 时返回 0.0
    """
    common = [s for s in factor_values if s in forward_returns]
    if len(common) < 2:
        return 0.0
    xs = [factor_values[s]   for s in common]
    ys = [forward_returns[s] for s in common]
    return _pearson(xs, ys)


def calc_rank_ic(
    factor_values:   dict[str, float],
    forward_returns: dict[str, float],
) -> float:
    """
    截面 RankIC（Spearman 秩相关系数）。

    Returns
    -------
    float  RankIC ∈ [-1, 1]
    """
    common = [s for s in factor_values if s in forward_returns]
    if len(common) < 2:
        return 0.0
    xs = _rank([factor_values[s]   for s in common])
    ys = _rank([forward_returns[s] for s in common])
    return _pearson(xs, ys)


def calc_sharpe(
    returns:          list[float],
    risk_free:        float = 0.0,
    periods_per_year: int   = 252,
) -> float:
    """
    年化 Sharpe Ratio。

    Parameters
    ----------
    returns          : 期度超额收益序列
    risk_free        : 每期无风险利率（默认 0）
    periods_per_year : 252 = 日频，52 = 周频

    Returns
    -------
    float  Sharpe Ratio（序列长度 < 2 时返回 0.0）
    """
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free for r in returns]
    mean   = _mean(excess)
    std    = _std(excess, ddof=1)
    if std < 1e-12:
        return 0.0
    return (mean / std) * math.sqrt(periods_per_year)


def calc_ir(ic_series: list[float]) -> float:
    """
    IC Information Ratio = IC_mean / IC_std。

    Returns
    -------
    float  IR（序列长度 < 2 或 std = 0 时返回 0.0）
    """
    if len(ic_series) < 2:
        return 0.0
    std = _std(ic_series, ddof=1)
    if std < 1e-12:
        return 0.0
    return _mean(ic_series) / std


def calc_t_stat(ic_series: list[float]) -> float:
    """
    对 IC 序列做单样本 t 检验（H₀: IC_mean = 0）。

    t = IC_mean / (IC_std / √n)

    Returns
    -------
    float  t 统计量（|t| > 1.96 → 5% 显著水平）
    """
    n = len(ic_series)
    if n < 2:
        return 0.0
    std = _std(ic_series, ddof=1)
    if std < 1e-12:
        return 0.0
    return _mean(ic_series) / (std / math.sqrt(n))


def calc_max_drawdown(nav_series: list[float]) -> tuple[float, int, int]:
    """
    最大回撤（基于净值序列）。

    Returns
    -------
    (max_drawdown_pct, peak_idx, trough_idx)
      max_drawdown_pct ≥ 0，peak_idx < trough_idx
    """
    if len(nav_series) < 2:
        return 0.0, 0, 0
    max_dd   = 0.0
    peak_idx = 0
    trough_idx = 0
    peak_val = nav_series[0]
    peak_i   = 0
    for i, val in enumerate(nav_series):
        if val > peak_val:
            peak_val = val
            peak_i   = i
        dd = (peak_val - val) / peak_val if peak_val > 0 else 0.0
        if dd > max_dd:
            max_dd     = dd
            peak_idx   = peak_i
            trough_idx = i
    return max_dd, peak_idx, trough_idx


def calc_ic_series(
    factor_cross_section: list[dict[str, float]],
    return_cross_section: list[dict[str, float]],
    use_rank: bool = False,
) -> list[float]:
    """
    批量计算每期 IC 序列。

    Parameters
    ----------
    factor_cross_section : 每期因子截面 [{symbol: value}, ...]
    return_cross_section : 每期收益截面 [{symbol: return}, ...]  长度须相同
    use_rank             : True = RankIC，False = IC

    Returns
    -------
    list[float]  长度与输入相同的 IC 时间序列
    """
    if len(factor_cross_section) != len(return_cross_section):
        raise ValueError("factor 与 return 截面序列长度不一致。")
    fn = calc_rank_ic if use_rank else calc_ic
    return [fn(f, r) for f, r in zip(factor_cross_section, return_cross_section)]


def summarize_ic_series(ic_series: list[float]) -> dict:
    """
    汇总 IC 序列的统计指标。

    Returns
    -------
    dict  包含 mean / std / ir / t_stat / win_rate / count
    """
    if not ic_series:
        return {"mean": 0.0, "std": 0.0, "ir": 0.0,
                "t_stat": 0.0, "win_rate": 0.0, "count": 0}
    positive = sum(1 for ic in ic_series if ic > 0)
    return {
        "mean":     _mean(ic_series),
        "std":      _std(ic_series, ddof=1) if len(ic_series) > 1 else 0.0,
        "ir":       calc_ir(ic_series),
        "t_stat":   calc_t_stat(ic_series),
        "win_rate": positive / len(ic_series),
        "count":    len(ic_series),
    }
