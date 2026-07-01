"""
risk_engine_2/utils/report_utils.py

归因报告工具函数（Phase 4）。

所有函数为纯函数，基于持仓快照 + PnL 序列计算。
"""

from __future__ import annotations

from ..model.risk_model import RiskContribution
from .math_utils import safe_div


def calc_pnl_contributions(
    symbol_pnl:     dict[str, float],
    symbol_strategy: dict[str, str],
    total_pnl:      float,
) -> list[RiskContribution]:
    """
    按策略聚合 PnL 贡献。

    Parameters
    ----------
    symbol_pnl      : {symbol: realized_pnl + unrealized_pnl}
    symbol_strategy : {symbol: strategy_name}
    total_pnl       : 组合总 PnL（用于计算贡献比例）

    Returns
    -------
    list[RiskContribution]  每个策略一条记录
    """
    strategy_pnl: dict[str, float] = {}
    for sym, pnl in symbol_pnl.items():
        strat = symbol_strategy.get(sym, "未分类")
        strategy_pnl[strat] = strategy_pnl.get(strat, 0.0) + pnl

    results = []
    for strat, pnl in strategy_pnl.items():
        results.append(RiskContribution(
            source_type     = "strategy",
            source_name     = strat,
            pnl_contrib     = pnl,
            pnl_contrib_pct = safe_div(pnl, total_pnl, 0.0),
        ))
    return sorted(results, key=lambda c: c.pnl_contrib, reverse=True)


def calc_factor_contributions(
    symbol_weights:  dict[str, float],
    symbol_betas:    dict[str, float],
    symbol_pnl:      dict[str, float],
    factor_exposure: dict[str, dict[str, float]],
    total_risk:      float,
) -> list[RiskContribution]:
    """
    按因子聚合风险贡献。

    Parameters
    ----------
    symbol_weights  : {symbol: weight}
    symbol_betas    : {symbol: beta}
    symbol_pnl      : {symbol: pnl}
    factor_exposure : {factor_name: {symbol: loading}}
    total_risk      : 组合总风险（用于归一化）

    Returns
    -------
    list[RiskContribution]  每个因子一条记录
    """
    results = []
    total_pnl = sum(symbol_pnl.values())

    for factor, loadings in factor_exposure.items():
        # 因子 PnL 贡献 = Σ (loading_i × pnl_i)
        f_pnl  = sum(loadings.get(sym, 0.0) * symbol_pnl.get(sym, 0.0)
                     for sym in loadings)
        # 因子风险贡献 = Σ (w_i × loading_i × beta_i) / Σ weights
        f_risk = sum(
            symbol_weights.get(sym, 0.0) * loadings.get(sym, 0.0)
            * symbol_betas.get(sym, 1.0)
            for sym in loadings
        )
        # Beta 贡献（组合层面）
        f_beta = sum(
            symbol_weights.get(sym, 0.0) * loadings.get(sym, 0.0)
            for sym in loadings
        )
        results.append(RiskContribution(
            source_type      = "factor",
            source_name      = factor,
            pnl_contrib      = f_pnl,
            pnl_contrib_pct  = safe_div(f_pnl, total_pnl, 0.0),
            risk_contrib     = f_risk,
            risk_contrib_pct = safe_div(f_risk, total_risk, 0.0),
            beta_contrib     = f_beta,
        ))
    return sorted(results, key=lambda c: abs(c.risk_contrib_pct), reverse=True)


def calc_industry_contributions(
    industry_weights: dict[str, float],
    industry_pnl:     dict[str, float],
    total_pnl:        float,
    total_risk:       float,
) -> list[RiskContribution]:
    """
    按行业聚合 PnL + 风险贡献。

    Parameters
    ----------
    industry_weights : {industry: weight}
    industry_pnl     : {industry: pnl}  （由 ExposureEngine 按行业汇总）
    total_pnl        : 组合总 PnL
    total_risk       : 组合总风险

    Returns
    -------
    list[RiskContribution]  每个行业一条记录
    """
    results = []
    all_inds = set(industry_weights) | set(industry_pnl)
    for ind in all_inds:
        w   = industry_weights.get(ind, 0.0)
        pnl = industry_pnl.get(ind, 0.0)
        results.append(RiskContribution(
            source_type      = "industry",
            source_name      = ind,
            pnl_contrib      = pnl,
            pnl_contrib_pct  = safe_div(pnl, total_pnl, 0.0),
            risk_contrib     = w,
            risk_contrib_pct = safe_div(w, total_risk if total_risk > 0 else 1.0, 0.0),
            weight           = w,
        ))
    return sorted(results, key=lambda c: c.pnl_contrib, reverse=True)


def calc_market_residual(
    strategy_contribs: list[RiskContribution],
    factor_contribs:   list[RiskContribution],
    total_pnl:         float,
    total_risk:        float,
) -> RiskContribution:
    """
    计算市场残差（无法被策略 / 因子解释的部分）。
    """
    explained_pnl  = sum(c.pnl_contrib for c in strategy_contribs)
    explained_risk = sum(c.risk_contrib for c in factor_contribs)
    residual_pnl   = total_pnl  - explained_pnl
    residual_risk  = total_risk - explained_risk
    return RiskContribution(
        source_type      = "market",
        source_name      = "市场残差",
        pnl_contrib      = residual_pnl,
        pnl_contrib_pct  = safe_div(residual_pnl, total_pnl, 0.0),
        risk_contrib     = residual_risk,
        risk_contrib_pct = safe_div(residual_risk, total_risk if total_risk > 0 else 1.0, 0.0),
    )


def calc_realized_volatility(
    pnl_series: list[float],
    periods_per_year: int = 252,
) -> float:
    """
    计算已实现波动率（年化标准差）。

    Parameters
    ----------
    pnl_series        : 按期 PnL 列表
    periods_per_year  : 252 = 日频，52 = 周频

    Returns
    -------
    annualized_vol : float  (0 if < 2 observations)
    """
    if len(pnl_series) < 2:
        return 0.0
    n    = len(pnl_series)
    mean = sum(pnl_series) / n
    var  = sum((x - mean) ** 2 for x in pnl_series) / (n - 1)
    return (var ** 0.5) * (periods_per_year ** 0.5)


def format_contribution_bar(
    contributions: list[RiskContribution],
    width: int = 30,
    key: str = "pnl",
) -> str:
    """
    生成文本横向 bar chart，用于 UI 文本区展示。

    Parameters
    ----------
    contributions : 贡献列表
    width         : bar 最大宽度（字符数）
    key           : "pnl" | "risk"
    """
    if not contributions:
        return "—"

    if key == "pnl":
        values = [(c.source_name, c.pnl_contrib, c.pnl_contrib_pct)
                  for c in contributions]
    else:
        values = [(c.source_name, c.risk_contrib, c.risk_contrib_pct)
                  for c in contributions]

    max_abs = max(abs(v) for _, v, _ in values) or 1.0
    lines   = []
    for name, val, pct in values:
        bar_len = int(abs(val) / max_abs * width)
        bar     = ("█" if val >= 0 else "░") * bar_len
        sign    = "+" if val >= 0 else ""
        lines.append(f"  {name[:10]:10s} │{bar:<{width}} {sign}{pct:.1%}")
    return "\n".join(lines)
