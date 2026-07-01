"""
risk_engine_2/utils/math_utils.py

数学工具函数（Phase 2）。
"""

from __future__ import annotations


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法，分母为 0 时返回 default。"""
    if denominator == 0.0:
        return default
    return numerator / denominator


def clamp(value: float, lo: float, hi: float) -> float:
    """将 value 限定在 [lo, hi] 区间。"""
    return max(lo, min(hi, value))


def calc_weight(market_value: float, nav: float) -> float:
    """计算单标的权重 = market_value / nav。"""
    return safe_div(market_value, nav, 0.0)


def calc_leverage(gross_notional: float, nav: float) -> float:
    """计算杠杆率 = gross_notional / nav。"""
    return safe_div(gross_notional, nav, 0.0)


def calc_portfolio_beta(
    weights: dict[str, float],
    betas:   dict[str, float],
) -> float:
    """
    计算组合加权 Beta。

    portfolio_beta = Σ (w_i × β_i)

    Parameters
    ----------
    weights : {symbol: weight}，权重之和不要求为 1
    betas   : {symbol: beta}，缺失标的默认 beta=1.0
    """
    total = 0.0
    for symbol, w in weights.items():
        beta = betas.get(symbol, 1.0)
        total += w * beta
    return total


def calc_concentration(
    weights: dict[str, float],
) -> tuple[float, str]:
    """
    计算最大单一权重及对应标的。

    Returns
    -------
    (max_weight, symbol)
    """
    if not weights:
        return 0.0, ""
    symbol = max(weights, key=lambda k: abs(weights[k]))
    return abs(weights[symbol]), symbol


def calc_industry_weights(
    symbol_weights:   dict[str, float],
    symbol_industry:  dict[str, str],
) -> dict[str, float]:
    """
    按行业聚合权重。

    Parameters
    ----------
    symbol_weights  : {symbol: weight}
    symbol_industry : {symbol: industry}

    Returns
    -------
    {industry: total_weight}
    """
    result: dict[str, float] = {}
    for symbol, w in symbol_weights.items():
        ind = symbol_industry.get(symbol, "其他")
        result[ind] = result.get(ind, 0.0) + abs(w)
    return result
