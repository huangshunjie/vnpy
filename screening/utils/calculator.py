"""
screening/utils/calculator.py

评分计算工具（Phase 4）。
提供 Z-score 标准化、百分位排名、加权综合评分。
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple


def z_score_normalize(values: List[float]) -> List[float]:
    """Z-score 标准化，去除离群值（winsorize ±3σ）。"""
    n = len(values)
    if n < 2:
        return list(values)
    mu = sum(values) / n
    std = math.sqrt(sum((v - mu) ** 2 for v in values) / n)
    if std < 1e-9:
        return [0.0] * n
    z = [(v - mu) / std for v in values]
    # winsorize at ±3
    return [max(-3.0, min(3.0, zi)) for zi in z]


def percentile_rank(values: List[float]) -> List[float]:
    """
    百分位排名（0~1）。
    相同值取平均百分位。
    """
    n = len(values)
    if n == 0:
        return []
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    result = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and indexed[j + 1][1] == indexed[i][1]:
            j += 1
        pct = (i + j) / 2.0 / (n - 1) if n > 1 else 0.5
        for k in range(i, j + 1):
            result[indexed[k][0]] = pct
        i = j + 1
    return result


def weighted_composite(
    factor_scores: Dict[str, float],
    weights: Dict[str, float],
) -> float:
    """
    加权综合评分。
    factor_scores: {factor_name: z_score}
    weights:       {factor_name: weight}
    权重自动归一化。
    """
    total_w = sum(abs(w) for w in weights.values() if weights.get(w) is not None)
    # 注意 weights 是 {factor_name: weight}
    total_w = sum(abs(v) for v in weights.values())
    if total_w < 1e-9:
        return 0.0
    score = 0.0
    for fname, w in weights.items():
        v = factor_scores.get(fname, 0.0)
        score += (v or 0.0) * w / total_w
    return score


def cross_sectional_rank(
    symbol_values: Dict[str, float],
    ascending: bool = False,
) -> Dict[str, int]:
    """
    横截面排名。
    ascending=False → 值越大排名越靠前（rank=1最好）。
    """
    sorted_items = sorted(
        symbol_values.items(),
        key=lambda x: x[1],
        reverse=not ascending,
    )
    return {sym: rank + 1 for rank, (sym, _) in enumerate(sorted_items)}


def compute_ic(
    factor_values: List[float],
    forward_returns: List[float],
) -> float:
    """
    计算因子 IC（信息系数）= Pearson 相关系数。
    """
    n = len(factor_values)
    if n < 3 or len(forward_returns) != n:
        return 0.0
    mf = sum(factor_values) / n
    mr = sum(forward_returns) / n
    cov = sum((f - mf) * (r - mr) for f, r in zip(factor_values, forward_returns)) / n
    sf = math.sqrt(sum((f - mf) ** 2 for f in factor_values) / n)
    sr = math.sqrt(sum((r - mr) ** 2 for r in forward_returns) / n)
    if sf < 1e-9 or sr < 1e-9:
        return 0.0
    return cov / (sf * sr)


def compute_rank_ic(
    factor_values: List[float],
    forward_returns: List[float],
) -> float:
    """
    计算 RankIC（Spearman 秩相关）。
    """
    n = len(factor_values)
    if n < 3 or len(forward_returns) != n:
        return 0.0

    def _ranks(vals: List[float]) -> List[float]:
        indexed = sorted(enumerate(vals), key=lambda x: x[1])
        r = [0.0] * n
        for rank, (idx, _) in enumerate(indexed):
            r[idx] = float(rank + 1)
        return r

    rf = _ranks(factor_values)
    rr = _ranks(forward_returns)
    return compute_ic(rf, rr)
