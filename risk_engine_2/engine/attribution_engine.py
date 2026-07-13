"""
risk_engine_2/engine/attribution_engine.py

AttributionEngine — 策略 / 因子 / 行业归因分解（Phase 4）。

职责：
  - 接收 ExposureReport + DrawdownState + 持仓 PnL 快照
  - 按策略 / 因子 / 行业三维度分解 PnL 和风险贡献
  - 生成 AttributionResult，追加到 AttributionReport 历史

设计原则：无 AI / 无优化 / 纯线性分解。
"""

from __future__ import annotations

from datetime import datetime

from ..model.risk_model import (
    RiskContribution, AttributionResult, AttributionReport
)
from ..model.exposure_model import ExposureReport
from ..model.drawdown_model import DrawdownState
from ..utils.report_utils import (
    calc_pnl_contributions,
    calc_factor_contributions,
    calc_industry_contributions,
    calc_market_residual,
    calc_realized_volatility,
    format_contribution_bar,
)
from ..utils.math_utils import safe_div


class AttributionEngine:
    """
    归因分析引擎（Phase 4）。

    使用方式：
        engine = AttributionEngine()
        engine.set_symbol_strategy({"rb2501.SHFE": "CTA_A"})
        result = engine.compute(exposure_report, drawdown_state, symbol_pnl)
        print(result.to_text())
    """

    def __init__(self) -> None:
        self._report = AttributionReport()

        # 归因映射（外部注入）
        self._symbol_strategy: dict[str, str]  = {}   # symbol → strategy
        self._symbol_industry: dict[str, str]  = {}   # symbol → industry
        self._symbol_betas:    dict[str, float] = {}  # symbol → beta

        # 因子暴露矩阵（由 Factor Research Engine 注入）
        # {factor_name: {symbol: loading}}
        self._factor_exposure: dict[str, dict[str, float]] = {}

        # PnL 时间序列（用于波动率计算）
        self._pnl_history: list[float] = []

    # ------------------------------------------------------------------ #
    #  外部注入
    # ------------------------------------------------------------------ #

    def set_symbol_strategy(self, mapping: dict[str, str]) -> None:
        """注入策略映射 {symbol: strategy_name}。"""
        self._symbol_strategy.update(mapping)

    def set_symbol_industry(self, mapping: dict[str, str]) -> None:
        self._symbol_industry.update(mapping)

    def set_symbol_betas(self, mapping: dict[str, float]) -> None:
        self._symbol_betas.update(mapping)

    def set_factor_exposure(
        self,
        factor_name: str,
        loadings: dict[str, float],
    ) -> None:
        """注入单个因子的截面暴露 {symbol: loading}。"""
        self._factor_exposure[factor_name] = loadings

    def set_factor_exposures(
        self,
        exposures: dict[str, dict[str, float]],
    ) -> None:
        """批量注入因子暴露矩阵。"""
        self._factor_exposure.update(exposures)

    # ------------------------------------------------------------------ #
    #  归因计算（核心）
    # ------------------------------------------------------------------ #

    def compute(
        self,
        exposure:      ExposureReport,
        drawdown:      DrawdownState | None = None,
        symbol_pnl:    dict[str, float] | None = None,
        period_start:  datetime | None = None,
        period_end:    datetime | None = None,
    ) -> AttributionResult:
        """
        执行一次完整归因计算。

        Parameters
        ----------
        exposure     : 当前组合暴露报告（ExposureReport）
        drawdown     : 当前回撤状态（可选）
        symbol_pnl   : {symbol: total_pnl}，若为 None 则从 exposure 估算
        period_start : 归因起始时间
        period_end   : 归因结束时间

        Returns
        -------
        AttributionResult
        """
        now = datetime.now()
        period_start = period_start or now
        period_end   = period_end   or now

        # ── 构建 symbol_pnl（若未传入则用浮动 PnL 估算）──────────────────
        if symbol_pnl is None:
            symbol_pnl = {
                sym: exposure.symbol_weights.get(sym, 0.0) * exposure.nav
                     * 0.01    # 粗估 1% 浮动，实际由 ExposureEngine 填充
                for sym in exposure.symbol_weights
            }

        total_pnl = sum(symbol_pnl.values())

        # ── 总风险（已实现波动率 × NAV）────────────────────────────────────
        self._pnl_history.append(total_pnl)
        if len(self._pnl_history) > 252:
            self._pnl_history = self._pnl_history[-252:]
        vol        = calc_realized_volatility(self._pnl_history)
        total_risk = vol if vol > 0 else max(abs(total_pnl), 1.0)

        # ── 策略贡献 ────────────────────────────────────────────────────────
        strategy_contribs = calc_pnl_contributions(
            symbol_pnl      = symbol_pnl,
            symbol_strategy = self._symbol_strategy,
            total_pnl       = total_pnl,
        )

        # ── 因子贡献 ────────────────────────────────────────────────────────
        if self._factor_exposure:
            factor_contribs = calc_factor_contributions(
                symbol_weights  = exposure.symbol_weights,
                symbol_betas    = self._symbol_betas,
                symbol_pnl      = symbol_pnl,
                factor_exposure = self._factor_exposure,
                total_risk      = total_risk,
            )
        else:
            # 无因子数据时：用 Beta 作为单因子代理
            beta_loadings = {
                sym: self._symbol_betas.get(sym, 1.0)
                for sym in exposure.symbol_weights
            }
            factor_contribs = calc_factor_contributions(
                symbol_weights  = exposure.symbol_weights,
                symbol_betas    = self._symbol_betas,
                symbol_pnl      = symbol_pnl,
                factor_exposure = {"Market Beta": beta_loadings},
                total_risk      = total_risk,
            )

        # ── 行业贡献 ────────────────────────────────────────────────────────
        # 按行业聚合 PnL
        industry_pnl: dict[str, float] = {}
        for sym, pnl in symbol_pnl.items():
            ind = self._symbol_industry.get(sym, "其他")
            industry_pnl[ind] = industry_pnl.get(ind, 0.0) + pnl

        industry_contribs = calc_industry_contributions(
            industry_weights = exposure.industry_weights,
            industry_pnl     = industry_pnl,
            total_pnl        = total_pnl,
            total_risk       = total_risk,
        )

        # ── 市场残差 ────────────────────────────────────────────────────────
        market_contrib = calc_market_residual(
            strategy_contribs = strategy_contribs,
            factor_contribs   = factor_contribs,
            total_pnl         = total_pnl,
            total_risk        = total_risk,
        )

        # ── 组装结果 ────────────────────────────────────────────────────────
        result = AttributionResult(
            period_start       = period_start,
            period_end         = period_end,
            total_pnl          = total_pnl,
            total_risk         = total_risk,
            portfolio_beta     = exposure.portfolio_beta,
            max_drawdown       = drawdown.max_drawdown     if drawdown else 0.0,
            max_drawdown_pct   = drawdown.max_drawdown_pct if drawdown else 0.0,
            strategy_contribs  = strategy_contribs,
            factor_contribs    = factor_contribs,
            industry_contribs  = industry_contribs,
            market_contrib     = market_contrib,
            computed_at        = now,
        )
        self._report.append(result)
        return result

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_report(self) -> AttributionReport:
        return self._report

    def get_latest(self) -> AttributionResult | None:
        return self._report.latest

    def get_text_summary(self) -> str:
        """返回最新归因结果的文本摘要。"""
        latest = self._report.latest
        if latest is None:
            return "暂无归因数据。"
        return latest.to_text()

    def get_strategy_bar(self) -> str:
        """策略贡献文本 bar chart。"""
        latest = self._report.latest
        if not latest:
            return "—"
        return format_contribution_bar(latest.strategy_contribs, key="pnl")

    def get_factor_bar(self) -> str:
        """因子贡献文本 bar chart。"""
        latest = self._report.latest
        if not latest:
            return "—"
        return format_contribution_bar(latest.factor_contribs, key="risk")

    def get_industry_bar(self) -> str:
        """行业贡献文本 bar chart。"""
        latest = self._report.latest
        if not latest:
            return "—"
        return format_contribution_bar(latest.industry_contribs, key="pnl")

    def clear(self) -> None:
        self._report.clear()
        self._pnl_history.clear()
