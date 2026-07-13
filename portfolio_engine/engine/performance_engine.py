"""
portfolio_engine/engine/performance_engine.py

PerformanceEngine — 组合绩效计算引擎。

Phase 2 实现：
  1. _blend_returns  : 加权合成组合日收益率
  2. _build_nav      : 净值曲线（起始=1.0）
  3. _compute_stats  : Sharpe / MDD / 年化收益 / Calmar / 波动率 / 胜率
  4. compute         : 串联以上三步，返回 PerformanceStats
"""

from __future__ import annotations

import math
from datetime import datetime

import pandas as pd

from ..model.allocation_model import AllocationResult
from ..model.performance_model import PerformanceStats
from ..model.portfolio_model import Portfolio
from ..utils.math_utils import (
    annual_return,
    annualised_volatility,
    calmar_ratio,
    max_drawdown,
    nav_from_returns,
    returns_from_nav,
    sharpe_ratio,
    win_rate,
)


class PerformanceEngine:
    """组合绩效计算引擎（无状态，纯函数风格）。"""

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def compute(
        self,
        portfolio: Portfolio,
        allocation: AllocationResult,
        returns_map: dict[str, pd.Series],
    ) -> PerformanceStats:
        """
        计算组合净值与绩效统计。

        Steps：
          1. 对齐所有策略收益率到公共时间轴（inner join）
          2. 加权合成组合日收益率
          3. 构建净值曲线
          4. 计算标量绩效指标
        """
        if not allocation.is_valid or not allocation.weights:
            return PerformanceStats(
                portfolio_name=portfolio.name,
                is_valid=False,
            )

        port_returns = self._blend_returns(allocation.weights, returns_map)

        if port_returns is None or port_returns.dropna().empty:
            return PerformanceStats(
                portfolio_name=portfolio.name,
                is_valid=False,
            )

        nav = self._build_nav(port_returns)
        return self._compute_stats(nav, port_returns, portfolio.name)

    # ------------------------------------------------------------------ #
    #  Step 1: 加权合成
    # ------------------------------------------------------------------ #

    def _blend_returns(
        self,
        weights: dict[str, float],
        returns_map: dict[str, pd.Series],
    ) -> pd.Series | None:
        """
        加权合成组合日收益率。

        R_port(t) = Σ w_i × r_i(t)

        只取 weights 中有对应 returns_map 条目的槽位；
        所有序列 inner join 对齐（dropna 行），保证无偏。
        """
        available = {
            name: returns_map[name]
            for name in weights
            if name in returns_map
        }
        if not available:
            return None

        # 对齐到公共日期轴
        df = pd.DataFrame(available).dropna()
        if df.empty:
            return None

        port_ret = pd.Series(0.0, index=df.index)
        for name, series in df.items():
            w = weights.get(str(name), 0.0)
            port_ret += w * series

        port_ret.name = "portfolio"
        return port_ret

    # ------------------------------------------------------------------ #
    #  Step 2: 净值曲线
    # ------------------------------------------------------------------ #

    def _build_nav(self, returns: pd.Series) -> pd.Series:
        """
        从日收益率序列构建净值曲线（起始=1.0）。
        NAV(t) = NAV(t-1) × (1 + r(t))
        """
        return nav_from_returns(returns, start_nav=1.0)

    # ------------------------------------------------------------------ #
    #  Step 3: 标量绩效指标
    # ------------------------------------------------------------------ #

    def _compute_stats(
        self,
        nav: pd.Series,
        returns: pd.Series,
        portfolio_name: str,
    ) -> PerformanceStats:
        """计算全部标量绩效指标并封装为 PerformanceStats。"""
        clean_ret = returns.dropna()
        clean_nav = nav.dropna()

        ar   = annual_return(clean_nav)
        mdd  = max_drawdown(clean_nav)
        sr   = sharpe_ratio(clean_ret)
        cal  = calmar_ratio(clean_nav)
        vol  = annualised_volatility(clean_ret)
        wr   = win_rate(clean_ret)
        tr   = float(clean_nav.iloc[-1] / clean_nav.iloc[0] - 1.0) if len(clean_nav) >= 2 else float("nan")

        return PerformanceStats(
            portfolio_name=portfolio_name,
            computed_at=datetime.now(),
            nav_series=nav,
            total_return=tr,
            annual_return=ar,
            sharpe_ratio=sr,
            max_drawdown=mdd,
            calmar_ratio=cal,
            volatility=vol,
            win_rate=wr,
            is_valid=True,
        )
