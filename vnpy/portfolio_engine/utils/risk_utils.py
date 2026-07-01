"""
portfolio_engine/utils/risk_utils.py

风险计算工具函数（纯函数，无状态）。
Phase 3：全部实现，供 RiskEngine / AttributionEngine 调用。
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .math_utils import TRADING_DAYS_PER_YEAR


def beta(
    port_returns: pd.Series,
    mkt_returns: pd.Series,
) -> float:
    """
    市场 Beta：β = Cov(r_port, r_mkt) / Var(r_mkt)

    序列自动 inner-join 对齐；数据不足 5 条时返回 NaN。
    """
    aligned = pd.concat([port_returns, mkt_returns], axis=1, join="inner").dropna()
    if len(aligned) < 5:
        return float("nan")
    p = aligned.iloc[:, 0].values
    m = aligned.iloc[:, 1].values
    var_m = float(np.var(m, ddof=1))
    if var_m < 1e-14:
        return float("nan")
    cov_pm = float(np.cov(p, m, ddof=1)[0, 1])
    return cov_pm / var_m


def alpha(
    port_returns: pd.Series,
    mkt_returns: pd.Series,
    risk_free: float = 0.0,
) -> float:
    """
    Jensen Alpha（年化）：α = E[r_p] - β × E[r_m]，乘以 252 年化。

    risk_free : 日无风险利率（默认 0）
    """
    b = beta(port_returns, mkt_returns)
    if math.isnan(b):
        return float("nan")
    aligned = pd.concat([port_returns, mkt_returns], axis=1, join="inner").dropna()
    if len(aligned) < 5:
        return float("nan")
    mu_p = float(aligned.iloc[:, 0].mean()) - risk_free
    mu_m = float(aligned.iloc[:, 1].mean()) - risk_free
    return (mu_p - b * mu_m) * TRADING_DAYS_PER_YEAR


def tracking_error(
    port_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """
    年化跟踪误差 = std(active_return) × √252

    active_return = port_returns - benchmark_returns（inner-join 对齐）
    """
    aligned = pd.concat([port_returns, benchmark_returns],
                        axis=1, join="inner").dropna()
    if len(aligned) < 2:
        return float("nan")
    active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    return float(active.std(ddof=1)) * math.sqrt(TRADING_DAYS_PER_YEAR)


def information_ratio(
    port_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float:
    """
    信息比率 = mean(active_return) / std(active_return) × √252
    """
    aligned = pd.concat([port_returns, benchmark_returns],
                        axis=1, join="inner").dropna()
    if len(aligned) < 2:
        return float("nan")
    active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    std_a  = float(active.std(ddof=1))
    if std_a < 1e-12:
        return float("nan")
    return float(active.mean()) / std_a * math.sqrt(TRADING_DAYS_PER_YEAR)


def correlation_matrix(returns_map: dict[str, pd.Series]) -> pd.DataFrame:
    """
    Pearson 相关矩阵（inner-join 对齐后计算）。

    Returns
    -------
    pd.DataFrame  shape (N, N)，index = columns = slot_names
                  若数据不足返回空 DataFrame
    """
    if len(returns_map) < 2:
        names = list(returns_map.keys())
        return pd.DataFrame([[1.0]], index=names, columns=names) if names else pd.DataFrame()

    df = pd.DataFrame(returns_map).dropna()
    if len(df) < 2:
        return pd.DataFrame()
    return df.corr(method="pearson")


def rolling_volatility(
    returns: pd.Series,
    window: int = 21,
) -> pd.Series:
    """
    滚动年化波动率 = rolling_std(returns, window) × √252。

    前 window-1 项为 NaN。
    """
    if returns.empty:
        return pd.Series(dtype=float)
    return returns.rolling(window=window, min_periods=window).std(ddof=1) * math.sqrt(
        TRADING_DAYS_PER_YEAR
    )


def drawdown_series(nav: pd.Series) -> pd.Series:
    """
    回撤序列：dd(t) = nav(t) / cummax(nav)[t] - 1  （负数）

    供 AttributionEngine 和 RiskEngine 共用。
    """
    nav = nav.dropna()
    if nav.empty:
        return pd.Series(dtype=float)
    rolling_peak = nav.cummax()
    return nav / rolling_peak - 1.0


def max_drawdown_period(
    nav: pd.Series,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """
    找出最大回撤的峰值日期（peak）和谷值日期（trough）。

    Returns
    -------
    (peak_dt, trough_dt)
    若数据不足返回 (nav.index[0], nav.index[-1])
    """
    nav = nav.dropna()
    if len(nav) < 2:
        return nav.index[0], nav.index[-1]

    dd = drawdown_series(nav)
    trough_idx = int(dd.argmin())
    peak_idx   = int(nav.iloc[: trough_idx + 1].argmax())

    return nav.index[peak_idx], nav.index[trough_idx]
