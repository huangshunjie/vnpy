"""
portfolio_engine/engine/attribution_engine.py

AttributionEngine — 回撤归因引擎（Phase 3 实现）。

方法：
  1. 定位最大回撤区间 [peak, trough]（来自 risk_utils.max_drawdown_period）
  2. 在该区间内计算每个槽位的收益贡献
     contribution_i = w_i × cumret_i(peak, trough)
  3. 若有基准，额外估算市场系统性贡献
     market_contrib = β × cumret_mkt(peak, trough)

设计约束：
  - 纯函数风格，无状态存储
  - 不访问数据库，所有数据由 dispatcher 传入
  - 贡献之和 ≈ total_drawdown（因权重为静态且各序列需对齐，可能有小误差）
"""

from __future__ import annotations

import math
from datetime import datetime

import pandas as pd

from ..model.attribution_model import AttributionResult, SlotContribution
from ..model.portfolio_model import Portfolio
from ..model.allocation_model import AllocationResult
from ..utils.risk_utils import max_drawdown_period, drawdown_series
from ..utils.math_utils import returns_from_nav


class AttributionEngine:
    """回撤归因引擎（无状态，纯函数风格）。"""

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def compute(
        self,
        portfolio: Portfolio,
        allocation: AllocationResult,
        nav_series: pd.Series,
        returns_map: dict[str, pd.Series],
        benchmark_returns: pd.Series | None = None,
    ) -> AttributionResult:
        """
        计算最大回撤区间内各槽位的收益贡献。

        Parameters
        ----------
        portfolio         : 组合定义
        allocation        : 权重分配结果
        nav_series        : 组合净值序列
        returns_map       : slot_name -> 日收益率 Series
        benchmark_returns : 基准日收益率（可选）

        Returns
        -------
        AttributionResult（is_valid=True 时可信）
        """
        result = AttributionResult(portfolio_name=portfolio.name)

        nav = nav_series.dropna()
        if len(nav) < 5:
            return result

        # ── 1. 定位最大回撤区间 ─────────────────────────────────────────
        peak_ts, trough_ts = self._find_max_drawdown_period(nav)
        result.drawdown_start = (
            peak_ts.to_pydatetime() if hasattr(peak_ts, "to_pydatetime") else peak_ts
        )
        result.drawdown_end = (
            trough_ts.to_pydatetime() if hasattr(trough_ts, "to_pydatetime") else trough_ts
        )

        # 组合在该区间内的总回撤
        nav_peak   = float(nav.loc[peak_ts])
        nav_trough = float(nav.loc[trough_ts])
        total_dd   = nav_trough / nav_peak - 1.0
        result.total_drawdown = total_dd

        # ── 2. 各槽位贡献 ───────────────────────────────────────────────
        contribs: list[SlotContribution] = []
        for slot in portfolio.slots:
            if not slot.enabled:
                continue
            w = allocation.weights.get(slot.name, 0.0)
            if w < 1e-8:
                continue
            ret = returns_map.get(slot.name)
            if ret is None or ret.empty:
                contribs.append(SlotContribution(
                    slot_name=slot.name, weight=w, contribution=float("nan")
                ))
                continue

            contrib = self._compute_slot_contribution(
                slot_name=slot.name,
                weight=w,
                slot_returns=ret,
                peak_ts=peak_ts,
                trough_ts=trough_ts,
            )
            contribs.append(contrib)

        result.slot_contributions = contribs

        # ── 3. 市场系统性贡献（有基准时计算）────────────────────────────
        if benchmark_returns is not None and not benchmark_returns.empty:
            result.market_contribution = self._compute_market_contribution(
                nav_series=nav,
                benchmark_returns=benchmark_returns,
                peak_ts=peak_ts,
                trough_ts=trough_ts,
                total_dd=total_dd,
            )
        else:
            result.market_contribution = float("nan")

        result.is_valid = True
        result.computed_at = datetime.now()
        return result

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    def _find_max_drawdown_period(
        self,
        nav: pd.Series,
    ) -> tuple[pd.Timestamp, pd.Timestamp]:
        """找出最大回撤的峰值日期和谷值日期。"""
        return max_drawdown_period(nav)

    def _compute_slot_contribution(
        self,
        slot_name: str,
        weight: float,
        slot_returns: pd.Series,
        peak_ts: pd.Timestamp,
        trough_ts: pd.Timestamp,
    ) -> SlotContribution:
        """
        计算单个槽位在 [peak, trough] 区间内的回撤贡献。

        贡献 = w_i × 区间累计收益 = w_i × (∏(1+r_t) - 1)

        若槽位在该区间内无数据，贡献记为 NaN。
        """
        try:
            r = slot_returns.dropna()
            # 取 (peak, trough] 区间（peak 之后到 trough，共同时间轴）
            mask = (r.index > peak_ts) & (r.index <= trough_ts)
            r_period = r.loc[mask]

            if r_period.empty:
                return SlotContribution(
                    slot_name=slot_name, weight=weight, contribution=float("nan")
                )

            cum_ret   = float((1.0 + r_period).prod() - 1.0)
            contrib   = weight * cum_ret

            return SlotContribution(
                slot_name=slot_name,
                weight=weight,
                contribution=contrib,
                cumulative_return=cum_ret,
            )
        except Exception:
            return SlotContribution(
                slot_name=slot_name, weight=weight, contribution=float("nan")
            )

    def _compute_market_contribution(
        self,
        nav_series: pd.Series,
        benchmark_returns: pd.Series,
        peak_ts: pd.Timestamp,
        trough_ts: pd.Timestamp,
        total_dd: float,
    ) -> float:
        """
        市场系统性贡献估算：
          1. 计算 β（全期）
          2. 计算基准在 [peak, trough] 区间累计收益
          3. market_contrib = β × benchmark_cumret

        返回值为负数（若基准也在下跌）。
        """
        try:
            from ..utils.risk_utils import beta as calc_beta
            port_returns = returns_from_nav(nav_series).dropna()
            b = calc_beta(port_returns, benchmark_returns)
            if math.isnan(b):
                return float("nan")

            bm = benchmark_returns.dropna()
            mask = (bm.index > peak_ts) & (bm.index <= trough_ts)
            bm_period = bm.loc[mask]
            if bm_period.empty:
                return float("nan")

            bm_cumret = float((1.0 + bm_period).prod() - 1.0)
            return b * bm_cumret
        except Exception:
            return float("nan")
