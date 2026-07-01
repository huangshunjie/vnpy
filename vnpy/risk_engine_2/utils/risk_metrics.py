"""
risk_engine_2/utils/risk_metrics.py

风险指标计算工具（Phase 2）。

所有函数为纯函数（无状态），直接基于持仓快照数据计算。
"""

from __future__ import annotations

from .math_utils import safe_div, calc_portfolio_beta, calc_industry_weights


def compute_leverage(
    gross_notional: float,
    nav: float,
) -> float:
    """
    杠杆率 = 总名义价值 / 净值。

    gross_notional = Σ |position_i × price_i × multiplier_i|
    """
    return safe_div(gross_notional, nav, 0.0)


def compute_beta(
    symbol_weights:  dict[str, float],
    symbol_betas:    dict[str, float],
) -> float:
    """
    组合加权 Beta = Σ (w_i × β_i)。

    未提供 beta 的标的默认 beta=1.0。
    """
    return calc_portfolio_beta(symbol_weights, symbol_betas)


def compute_single_concentration(
    symbol_weights: dict[str, float],
) -> tuple[float, str]:
    """
    单票最大权重集中度。

    Returns
    -------
    (max_weight, symbol)
    """
    if not symbol_weights:
        return 0.0, ""
    symbol = max(symbol_weights, key=lambda k: abs(symbol_weights[k]))
    return abs(symbol_weights[symbol]), symbol


def compute_industry_concentration(
    symbol_weights:  dict[str, float],
    symbol_industry: dict[str, str],
) -> tuple[float, str, dict[str, float]]:
    """
    行业最大集中度。

    Returns
    -------
    (max_weight, industry_name, industry_weights_dict)
    """
    ind_weights = calc_industry_weights(symbol_weights, symbol_industry)
    if not ind_weights:
        return 0.0, "", {}
    industry = max(ind_weights, key=lambda k: ind_weights[k])
    return ind_weights[industry], industry, ind_weights


def check_position_limit(
    symbol:        str,
    current_weight: float,
    hard_limit:    float,
    warning_threshold: float = 0.0,
) -> tuple[bool, str]:
    """
    校验单票仓位限制。

    Returns
    -------
    (passed, message)
      passed=False 表示超过硬限制，需要阻断。
    """
    if hard_limit > 0 and current_weight >= hard_limit:
        return False, (
            f"单票仓位超限：{symbol} weight={current_weight:.2%}"
            f" >= hard_limit={hard_limit:.2%}"
        )
    if warning_threshold > 0 and current_weight >= warning_threshold:
        return True, (
            f"单票仓位预警：{symbol} weight={current_weight:.2%}"
            f" >= warning={warning_threshold:.2%}"
        )
    return True, ""


def check_leverage_limit(
    leverage:          float,
    hard_limit:        float,
    warning_threshold: float = 0.0,
) -> tuple[bool, str]:
    """
    校验杠杆限制。

    Returns
    -------
    (passed, message)
    """
    if hard_limit > 0 and leverage >= hard_limit:
        return False, (
            f"杠杆超限：leverage={leverage:.2f} >= hard_limit={hard_limit:.2f}"
        )
    if warning_threshold > 0 and leverage >= warning_threshold:
        return True, (
            f"杠杆预警：leverage={leverage:.2f} >= warning={warning_threshold:.2f}"
        )
    return True, ""


def check_beta_limit(
    portfolio_beta:    float,
    hard_limit:        float,
    warning_threshold: float = 0.0,
) -> tuple[bool, str]:
    """
    校验 Beta 暴露限制。

    Returns
    -------
    (passed, message)
    """
    abs_beta = abs(portfolio_beta)
    if hard_limit > 0 and abs_beta >= hard_limit:
        return False, (
            f"Beta 暴露超限：beta={portfolio_beta:.3f}"
            f" >= hard_limit={hard_limit:.3f}"
        )
    if warning_threshold > 0 and abs_beta >= warning_threshold:
        return True, (
            f"Beta 暴露预警：beta={portfolio_beta:.3f}"
            f" >= warning={warning_threshold:.3f}"
        )
    return True, ""


def check_industry_limit(
    industry:          str,
    industry_weight:   float,
    hard_limit:        float,
    warning_threshold: float = 0.0,
) -> tuple[bool, str]:
    """
    校验行业集中度限制。

    Returns
    -------
    (passed, message)
    """
    if hard_limit > 0 and industry_weight >= hard_limit:
        return False, (
            f"行业集中度超限：{industry} weight={industry_weight:.2%}"
            f" >= hard_limit={hard_limit:.2%}"
        )
    if warning_threshold > 0 and industry_weight >= warning_threshold:
        return True, (
            f"行业集中度预警：{industry} weight={industry_weight:.2%}"
            f" >= warning={warning_threshold:.2%}"
        )
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3：实时 PnL / 回撤计算工具
# ─────────────────────────────────────────────────────────────────────────────

def compute_drawdown(
    peak_pnl:    float,
    current_pnl: float,
    nav:         float = 0.0,
) -> tuple[float, float]:
    """
    计算当前回撤。

    Returns
    -------
    (abs_drawdown, drawdown_pct)
      abs_drawdown  : 绝对回撤额（peak - current，>= 0）
      drawdown_pct  : 回撤率（abs_drawdown / nav，>= 0）
    """
    abs_dd = max(peak_pnl - current_pnl, 0.0)
    ref    = nav if nav > 0 else 1.0
    return abs_dd, abs_dd / ref


def check_drawdown_limit(
    drawdown_pct:      float,
    hard_limit:        float,
    warning_threshold: float = 0.0,
) -> tuple[bool, str]:
    """
    校验回撤是否超限。

    Returns
    -------
    (passed, message)
      passed=False 表示超过硬限制，需要触发减仓 / 暂停。
    """
    if hard_limit > 0 and drawdown_pct >= hard_limit:
        return False, (
            f"回撤超限：drawdown={drawdown_pct:.2%}"
            f" >= hard_limit={hard_limit:.2%}"
        )
    if warning_threshold > 0 and drawdown_pct >= warning_threshold:
        return True, (
            f"回撤预警：drawdown={drawdown_pct:.2%}"
            f" >= warning={warning_threshold:.2%}"
        )
    return True, ""


def check_daily_loss_limit(
    daily_loss_pct:    float,
    hard_limit:        float,
    warning_threshold: float = 0.0,
) -> tuple[bool, str]:
    """
    校验当日亏损是否超限。

    Parameters
    ----------
    daily_loss_pct : 当日亏损率（正值，= |daily_pnl| / nav）
    """
    if hard_limit > 0 and daily_loss_pct >= hard_limit:
        return False, (
            f"当日亏损超限：daily_loss={daily_loss_pct:.2%}"
            f" >= hard_limit={hard_limit:.2%}"
        )
    if warning_threshold > 0 and daily_loss_pct >= warning_threshold:
        return True, (
            f"当日亏损预警：daily_loss={daily_loss_pct:.2%}"
            f" >= warning={warning_threshold:.2%}"
        )
    return True, ""


def calc_max_drawdown_from_series(pnl_values: list[float]) -> tuple[float, int, int]:
    """
    从 PnL 时间序列计算历史最大回撤。

    Returns
    -------
    (max_drawdown, peak_idx, trough_idx)
    """
    if len(pnl_values) < 2:
        return 0.0, 0, 0

    max_dd    = 0.0
    peak_idx  = 0
    trough_idx = 0
    peak_val  = pnl_values[0]
    peak_i    = 0

    for i, val in enumerate(pnl_values[1:], 1):
        if val > peak_val:
            peak_val = val
            peak_i   = i
        dd = peak_val - val
        if dd > max_dd:
            max_dd     = dd
            peak_idx   = peak_i
            trough_idx = i

    return max_dd, peak_idx, trough_idx
