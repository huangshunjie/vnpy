"""
portfolio_engine/utils/factor_utils.py

因子信号 → 组合权重映射工具（Phase 4 实现）。

设计原则：
  - 纯函数，无状态，不依赖 VeighNa 核心
  - 与 FactorResearch 模型的耦合仅在 factor_bridge.py 中，
    本模块只接受基本 Python/pandas 类型
  - 所有权重输出保证：非负、求和 = 1.0（long_only 模式下）

权重映射方法概述：
  ic_to_weights       : 用 IC 时序的滚动均值作为信号强度，按信号绝对值分配权重
  factor_score_to_weights : 分位数截断后对 score 做 softmax 或线性归一化
  rank_ic_weights     : 截面 RankIC → 直接正规化为权重（做多正 IC 品种）
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
#  1. IC 时序 → 权重
# ──────────────────────────────────────────────────────────────────────────────

def ic_to_weights(
    ic_series: pd.Series,
    symbols: list[str],
    method: str = "rank",
) -> dict[str, float]:
    """
    把 IC 序列（时序）映射为各合约目标权重。

    本函数适用于**单因子 × 多合约**场景：
      ic_series.index = 合约代码（截面），ic_series.values = IC 值

    或**单合约**场景（仅有一个合约时直接返回 {symbol: 1.0}）。

    Parameters
    ----------
    ic_series : pd.Series
        index = symbol（合约代码），values = IC 值（浮点，典型范围 [-1, 1]）
    symbols   : list[str]
        参与组合的合约代码子集（ic_series 的子集过滤）
    method    : str
        "rank"  — RankIC 加权：对截面 IC 排名后归一化
        "score" — 分数加权：用 IC 绝对值经 softmax 归一化

    Returns
    -------
    dict[str, float]
        symbol -> weight，权重之和 = 1.0（long_only，仅做多正 IC 品种）
        若无有效信号返回等权
    """
    if not symbols:
        return {}

    # 只取 symbols 交集
    available = {s: ic_series.get(s, float("nan")) for s in symbols}
    valid     = {s: v for s, v in available.items() if not math.isnan(v)}

    if not valid:
        n = len(symbols)
        return {s: 1.0 / n for s in symbols}

    if method == "rank":
        return _rank_normalise(valid, long_only=True)
    elif method == "score":
        return _softmax_weights(valid, long_only=True)
    else:
        raise ValueError(f"Unknown method: {method!r}. Choose 'rank' or 'score'.")


# ──────────────────────────────────────────────────────────────────────────────
#  2. 因子综合评分 → 权重
# ──────────────────────────────────────────────────────────────────────────────

def factor_score_to_weights(
    scores: dict[str, float],
    long_quantile: float = 0.8,
    short_quantile: float = 0.2,
    long_only: bool = True,
) -> dict[str, float]:
    """
    把因子综合评分（0~100）映射为持仓权重（分位数截断）。

    规则：
      - 评分 >= long_quantile 分位数 → 做多（正权重）
      - 评分 <= short_quantile 分位数 → 做空（负权重，long_only=False 时）
      - 其余合约权重为 0
      - 多头权重之和 = 1.0；空头权重之和 = -1.0（long_only=False 时）

    Parameters
    ----------
    scores         : {symbol: score(0~100)}
    long_quantile  : 做多阈值分位数（默认 0.8 = 前 20% 高分做多）
    short_quantile : 做空阈值分位数（默认 0.2 = 后 20% 低分做空）
    long_only      : True 时忽略空头信号

    Returns
    -------
    dict[str, float]  symbol -> weight
    """
    if not scores:
        return {}

    valid  = {s: v for s, v in scores.items()
              if not math.isnan(v) and v is not None}
    if not valid:
        return {}

    vals   = np.array(list(valid.values()))
    syms   = list(valid.keys())

    lo_thr = float(np.quantile(vals, long_quantile))
    sh_thr = float(np.quantile(vals, short_quantile))

    long_scores  = {s: v for s, v in valid.items() if v >= lo_thr}
    short_scores = {} if long_only else {s: v for s, v in valid.items() if v <= sh_thr}

    result: dict[str, float] = {}

    # 多头：按得分线性分配权重
    if long_scores:
        total_l = sum(long_scores.values())
        if total_l > 1e-10:
            for s, v in long_scores.items():
                result[s] = v / total_l
        else:
            n = len(long_scores)
            for s in long_scores:
                result[s] = 1.0 / n

    # 空头：按得分（倒序）线性分配权重（和为 -1）
    if short_scores:
        total_s = sum(short_scores.values())
        if total_s > 1e-10:
            for s, v in short_scores.items():
                result[s] = result.get(s, 0.0) - v / total_s
        else:
            n = len(short_scores)
            for s in short_scores:
                result[s] = result.get(s, 0.0) - 1.0 / n

    return result


# ──────────────────────────────────────────────────────────────────────────────
#  3. 截面 RankIC → 权重
# ──────────────────────────────────────────────────────────────────────────────

def rank_ic_weights(
    cross_section_ic: dict[str, float],
    normalize: bool = True,
) -> dict[str, float]:
    """
    截面 RankIC 值直接作为做多权重（正规化可选）。

    适用场景：某期截面中，每个合约都有一个 RankIC 值，
    直接用正 IC 值比例分配多头权重（忽略负 IC 合约）。

    Parameters
    ----------
    cross_section_ic : {symbol: rank_ic_value}
    normalize        : True → 权重之和 = 1.0

    Returns
    -------
    dict[str, float]  仅包含正 IC 合约，负 IC 合约权重为 0（不包含在输出中）
    """
    if not cross_section_ic:
        return {}

    positive = {s: v for s, v in cross_section_ic.items()
                if not math.isnan(v) and v > 0}

    if not positive:
        # 全部 IC 为负：等权返回全部合约（防御性）
        n = len(cross_section_ic)
        return {s: 1.0 / n for s in cross_section_ic}

    if not normalize:
        return dict(positive)

    total = sum(positive.values())
    if total < 1e-12:
        n = len(positive)
        return {s: 1.0 / n for s in positive}

    return {s: v / total for s, v in positive.items()}


# ──────────────────────────────────────────────────────────────────────────────
#  4. 辅助函数
# ──────────────────────────────────────────────────────────────────────────────

def blend_factor_weights(
    ic_weights: dict[str, float],
    score_weights: dict[str, float],
    ic_blend: float = 0.5,
) -> dict[str, float]:
    """
    混合 IC 权重与评分权重。

    Parameters
    ----------
    ic_weights    : IC 映射的权重字典
    score_weights : 评分映射的权重字典
    ic_blend      : IC 权重的混合比例（0~1），score 权重占 1-ic_blend

    Returns
    -------
    dict[str, float]  归一化混合权重
    """
    if not 0 <= ic_blend <= 1:
        raise ValueError(f"ic_blend must be in [0,1], got {ic_blend}")

    all_syms = set(ic_weights) | set(score_weights)
    if not all_syms:
        return {}

    raw: dict[str, float] = {}
    for s in all_syms:
        w = ic_blend * ic_weights.get(s, 0.0) + (1 - ic_blend) * score_weights.get(s, 0.0)
        raw[s] = w

    # 归一化（仅正权重）
    pos = {s: v for s, v in raw.items() if v > 0}
    if not pos:
        n = len(all_syms)
        return {s: 1.0 / n for s in all_syms}

    total = sum(pos.values())
    return {s: v / total for s, v in pos.items()}


def _rank_normalise(values: dict[str, float], long_only: bool = True) -> dict[str, float]:
    """按值的排名归一化：排名越高（值越大）权重越大（线性）。"""
    syms  = list(values.keys())
    vals  = np.array([values[s] for s in syms], dtype=float)

    if long_only:
        # 只保留正值；排名从 1 开始
        ranks = np.where(vals > 0, vals, 0.0)
    else:
        ranks = vals - vals.min() + 1.0   # shift to positive

    total = float(ranks.sum())
    if total < 1e-12:
        n = len(syms)
        return {s: 1.0 / n for s in syms}

    return {s: float(ranks[i]) / total for i, s in enumerate(syms)}


def _softmax_weights(values: dict[str, float], long_only: bool = True) -> dict[str, float]:
    """Softmax 归一化权重：对正 IC 使用 softmax，负 IC 权重置零（long_only 时）。"""
    syms = list(values.keys())
    vals = np.array([values[s] for s in syms], dtype=float)

    if long_only:
        vals = np.where(vals > 0, vals, -np.inf)

    # 数值稳定 softmax
    shifted = vals - np.max(vals[np.isfinite(vals)] if np.any(np.isfinite(vals)) else vals)
    exp_vals = np.where(np.isfinite(shifted), np.exp(shifted), 0.0)
    total    = float(exp_vals.sum())

    if total < 1e-12:
        n = len(syms)
        return {s: 1.0 / n for s in syms}

    return {s: float(exp_vals[i]) / total for i, s in enumerate(syms)}
