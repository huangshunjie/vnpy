"""
portfolio_engine/utils/math_utils.py

纯数学工具函数（无状态，无副作用）。
Phase 2：全部实现，供 PerformanceEngine / AllocationEngine 调用。
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR: int = 252


def annual_return(nav: pd.Series) -> float:
    """
    年化收益率。
    公式：(NAV_end / NAV_start) ^ (252 / n_days) - 1
    """
    nav = nav.dropna()
    if len(nav) < 2:
        return float("nan")
    n_days = len(nav)
    ratio  = float(nav.iloc[-1]) / float(nav.iloc[0])
    if ratio <= 0:
        return float("nan")
    return ratio ** (TRADING_DAYS_PER_YEAR / n_days) - 1.0


def max_drawdown(nav: pd.Series) -> float:
    """
    最大回撤（负数）。
    公式：min( NAV(t) / cummax(NAV)[t] ) - 1
    """
    nav = nav.dropna()
    if len(nav) < 2:
        return float("nan")
    rolling_peak = nav.cummax()
    drawdowns    = nav / rolling_peak - 1.0
    mdd = float(drawdowns.min())
    return mdd if not math.isnan(mdd) else float("nan")


def sharpe_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    """
    年化 Sharpe ratio。
    公式：(mean(r) - rf) / std(r) * sqrt(252)
    """
    r = returns.dropna()
    if len(r) < 2:
        return float("nan")
    excess = r - risk_free
    std    = float(excess.std(ddof=1))
    if std < 1e-12:
        return float("nan")
    return float(excess.mean()) / std * math.sqrt(TRADING_DAYS_PER_YEAR)


def calmar_ratio(nav: pd.Series) -> float:
    """
    Calmar ratio = annual_return / |max_drawdown|。
    max_drawdown == 0 时返回 nan。
    """
    ar  = annual_return(nav)
    mdd = max_drawdown(nav)
    if math.isnan(ar) or math.isnan(mdd) or abs(mdd) < 1e-12:
        return float("nan")
    return ar / abs(mdd)


def annualised_volatility(returns: pd.Series) -> float:
    """
    年化波动率 = std(daily_returns) * sqrt(252)。
    """
    r = returns.dropna()
    if len(r) < 2:
        return float("nan")
    return float(r.std(ddof=1)) * math.sqrt(TRADING_DAYS_PER_YEAR)


def win_rate(returns: pd.Series) -> float:
    """
    日胜率 = count(r > 0) / count(r != 0)。
    """
    r = returns.dropna()
    nonzero = (r != 0).sum()
    if nonzero == 0:
        return float("nan")
    return float((r > 0).sum()) / float(nonzero)


def nav_from_returns(returns: pd.Series, start_nav: float = 1.0) -> pd.Series:
    """
    从日收益率序列构建净值曲线。
    NAV(t) = NAV(t-1) * (1 + r(t))，NAV(0) = start_nav
    """
    r = returns.fillna(0.0)
    nav = (1.0 + r).cumprod() * start_nav
    return nav


def returns_from_nav(nav: pd.Series) -> pd.Series:
    """
    从净值序列计算日收益率：r(t) = NAV(t)/NAV(t-1) - 1。
    第一项为 NaN。
    """
    return nav.pct_change()
