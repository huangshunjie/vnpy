"""
portfolio_engine/engine/risk_engine.py

RiskEngine — 风险暴露分析引擎（Phase 3 实现）。

职责：
  1. Beta 暴露         : β = Cov(port, mkt) / Var(mkt)
  2. Alpha (Jensen)    : α = E[r_p] - β × E[r_m]（年化）
  3. 跟踪误差 / IR     : TE / IR vs 基准
  4. 相关矩阵          : 各槽位间 Pearson 相关
  5. 滚动波动率        : 21 日滚动年化波动率序列
  6. 因子暴露代理      : Momentum / Volatility / 分散度（无外部数据依赖）
  7. 最大回撤区间      : peak / trough 日期
  8. 行业暴露          : 依赖 StrategySlot.sector 字段（Phase 3 基础实现）

行业暴露说明：
  VeighNa 社区版本地数据库无行业分类表，此处用 slot.name 前缀做简单分组。
  如需真实行业映射，在 StrategySlot.sector 字段填入行业名即可自动生效。
"""

from __future__ import annotations

import math
from datetime import datetime
from collections import defaultdict

import pandas as pd

from ..model.portfolio_model import Portfolio
from ..model.risk_model import RiskExposure
from ..utils.math_utils import returns_from_nav, annualised_volatility
from ..utils.risk_utils import (
    beta as calc_beta,
    alpha as calc_alpha,
    tracking_error as calc_te,
    information_ratio as calc_ir,
    correlation_matrix,
    rolling_volatility,
    max_drawdown_period,
    drawdown_series,
)


class RiskEngine:
    """风险暴露分析引擎（无状态，纯函数风格）。"""

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def compute(
        self,
        portfolio: Portfolio,
        nav_series: pd.Series,
        returns_map: dict[str, pd.Series],
        weights: "dict[str, float] | None" = None,
        benchmark_returns: pd.Series | None = None,
    ) -> RiskExposure:
        """
        计算组合风险暴露完整快照。

        Parameters
        ----------
        portfolio          : 组合定义（包含槽位和权重）
        nav_series         : 组合净值序列（datetime index）
        returns_map        : slot_name -> 日收益率 Series
        benchmark_returns  : 基准日收益率序列（可选；无时 Beta/Alpha/IR 为 NaN）

        Returns
        -------
        RiskExposure（is_valid=True 时可信）
        """
        port_returns = returns_from_nav(nav_series).dropna()
        exposure = RiskExposure(portfolio_name=portfolio.name)

        # ── Beta / Alpha / TE / IR ──────────────────────────────────────
        if benchmark_returns is not None and not benchmark_returns.empty:
            exposure.portfolio_beta  = self.compute_beta(port_returns, benchmark_returns)
            exposure.portfolio_alpha = calc_alpha(port_returns, benchmark_returns)
            exposure.tracking_error  = calc_te(port_returns, benchmark_returns)
            exposure.information_ratio = calc_ir(port_returns, benchmark_returns)
        else:
            # 无基准时 Beta 用 1.0 标记（相对自身）
            exposure.portfolio_beta    = float("nan")
            exposure.portfolio_alpha   = float("nan")
            exposure.tracking_error    = float("nan")
            exposure.information_ratio = float("nan")

        # ── 相关矩阵 ────────────────────────────────────────────────────
        exposure.correlation_matrix = correlation_matrix(returns_map)

        # ── 各槽位滚动波动率（最新值）──────────────────────────────────
        slot_vols: dict[str, float] = {}
        for name, ret in returns_map.items():
            rv = rolling_volatility(ret.dropna(), window=21)
            last_val = rv.dropna().iloc[-1] if not rv.dropna().empty else float("nan")
            slot_vols[name] = float(last_val)
        exposure.slot_volatilities = slot_vols

        # ── 滚动波动率序列（组合整体）──────────────────────────────────
        exposure.rolling_vol_series = rolling_volatility(port_returns, window=21)

        # ── 最大回撤区间 ────────────────────────────────────────────────
        from ..utils.math_utils import max_drawdown
        exposure.max_drawdown = max_drawdown(nav_series)
        try:
            peak_dt, trough_dt = max_drawdown_period(nav_series)
            exposure.drawdown_start = peak_dt.to_pydatetime() \
                if hasattr(peak_dt, "to_pydatetime") else peak_dt
            exposure.drawdown_end   = trough_dt.to_pydatetime() \
                if hasattr(trough_dt, "to_pydatetime") else trough_dt
        except Exception:
            pass

        # ── 因子暴露（代理指标，无外部数据依赖）───────────────────────
        effective_weights = weights if weights is not None else {s.name: s.target_weight for s in portfolio.slots}
        exposure.factor_exposures = self.compute_factor_exposures(
            returns_map, effective_weights
        )

        # ── 行业暴露 ────────────────────────────────────────────────────
        exposure.sector_weights = self.compute_sector_weights(
            portfolio, effective_weights
        )

        exposure.is_valid = True
        exposure.computed_at = datetime.now()
        return exposure

    # ------------------------------------------------------------------ #
    #  Beta
    # ------------------------------------------------------------------ #

    def compute_beta(
        self,
        port_returns: pd.Series,
        mkt_returns: pd.Series,
    ) -> float:
        return calc_beta(port_returns, mkt_returns)

    # ------------------------------------------------------------------ #
    #  行业暴露
    # ------------------------------------------------------------------ #

    def compute_sector_weights(
        self,
        portfolio: Portfolio,
        weights: dict[str, float],
    ) -> dict[str, float]:
        """
        行业暴露分布 (sector -> weighted_exposure)。

        映射规则（优先级从高到低）：
          1. slot.sector 字段有值时直接用
          2. slot.name 以 "CTA_" / "FACTOR_" / "CUSTOM_" 等前缀归类
          3. 默认归入 "其他"
        """
        sector_map: dict[str, float] = defaultdict(float)
        for slot in portfolio.slots:
            if not slot.enabled:
                continue
            w = weights.get(slot.name, 0.0)

            # 优先使用 slot.sector（Phase 4 用户可填写）
            sector = getattr(slot, "sector", None) or ""
            if not sector:
                name_upper = slot.name.upper()
                if name_upper.startswith("CTA"):
                    sector = "CTA 策略"
                elif name_upper.startswith("FACTOR") or name_upper.startswith("FC"):
                    sector = "因子策略"
                elif name_upper.startswith("ARB") or name_upper.startswith("STAT"):
                    sector = "套利策略"
                elif name_upper.startswith("TREND"):
                    sector = "趋势策略"
                else:
                    sector = "其他策略"

            sector_map[sector] += w

        return dict(sector_map)

    # ------------------------------------------------------------------ #
    #  因子暴露（代理指标）
    # ------------------------------------------------------------------ #

    def compute_factor_exposures(
        self,
        returns_map: dict[str, pd.Series],
        weights: dict[str, float],
    ) -> dict[str, float]:
        """
        用可观测的统计量代理四类因子暴露（无需外部数据）：

        Momentum  : 加权平均过去 12 个月累计收益
        Volatility: 加权平均年化波动率（低波 = 低暴露）
        Sharpe    : 加权平均 Sharpe（代理 Quality 因子）
        Diversification: 1 - mean(abs(correlation))（分散度）
        """
        from ..utils.math_utils import sharpe_ratio

        exposures: dict[str, float] = {}

        # ── Momentum ────────────────────────────────────────────────────
        mom_vals: list[float] = []
        for name, ret in returns_map.items():
            w = weights.get(name, 0.0)
            if w < 1e-8:
                continue
            last252 = ret.dropna().iloc[-252:] if len(ret.dropna()) >= 20 else ret.dropna()
            cum_ret = float((1 + last252).prod() - 1)
            mom_vals.append(w * cum_ret)
        exposures["Momentum"] = sum(mom_vals) if mom_vals else float("nan")

        # ── Volatility (加权平均年化波动率) ─────────────────────────────
        vol_vals: list[float] = []
        for name, ret in returns_map.items():
            w = weights.get(name, 0.0)
            if w < 1e-8:
                continue
            v = annualised_volatility(ret.dropna())
            if not math.isnan(v):
                vol_vals.append(w * v)
        exposures["Volatility"] = sum(vol_vals) if vol_vals else float("nan")

        # ── Quality (加权平均 Sharpe) ────────────────────────────────────
        sr_vals: list[float] = []
        for name, ret in returns_map.items():
            w = weights.get(name, 0.0)
            if w < 1e-8:
                continue
            sr = sharpe_ratio(ret.dropna())
            if not math.isnan(sr):
                sr_vals.append(w * sr)
        exposures["Quality(Sharpe)"] = sum(sr_vals) if sr_vals else float("nan")

        # ── Diversification (分散度) ─────────────────────────────────────
        if len(returns_map) >= 2:
            corr_df = correlation_matrix(returns_map)
            if not corr_df.empty:
                n = len(corr_df)
                off_diag = [
                    abs(corr_df.iloc[i, j])
                    for i in range(n)
                    for j in range(n)
                    if i != j
                ]
                mean_abs_corr = sum(off_diag) / len(off_diag) if off_diag else 0.0
                exposures["Diversification"] = round(1.0 - mean_abs_corr, 4)
            else:
                exposures["Diversification"] = float("nan")
        else:
            exposures["Diversification"] = float("nan")

        return exposures
