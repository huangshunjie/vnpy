"""
risk_engine_2/engine/limit_engine.py

LimitEngine — 交易前风控限制校验（Phase 2）。

校验顺序：
  1. 单票仓位限制
  2. 总仓位 / 杠杆限制
  3. Beta 暴露限制
  4. 行业集中度限制

所有校验为纯函数风格，不修改外部状态。
返回 LimitReport，由 RiskCoreEngine 决定是否阻断订单。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from ..constant import LimitType, RiskLevel, RiskAction
from ..model.limit_model import RiskLimit, LimitCheckResult, LimitReport
from ..model.exposure_model import ExposureReport
from ..utils.risk_metrics import (
    check_position_limit,
    check_leverage_limit,
    check_beta_limit,
    check_industry_limit,
)


class LimitEngine:
    """
    交易前风控限制引擎。

    使用方式：
        engine = LimitEngine()
        engine.add_limit(RiskLimit(...))
        report = engine.check_all(exposure_report)
        if report.any_blocked:
            # 阻断订单
    """

    def __init__(self) -> None:
        self._limits: dict[str, RiskLimit] = {}

        # 默认限制（可通过 UI 覆盖）
        self._load_defaults()

    # ------------------------------------------------------------------ #
    #  限制规则管理
    # ------------------------------------------------------------------ #

    def _load_defaults(self) -> None:
        """加载默认风控规则（保守参数，Phase 2）。"""
        defaults = [
            RiskLimit(
                limit_id="position_single_default",
                limit_type=LimitType.POSITION,
                warning_threshold=0.15,
                hard_limit=0.25,
                action=RiskAction.BLOCK,
                description="单票最大仓位 25%",
            ),
            RiskLimit(
                limit_id="leverage_default",
                limit_type=LimitType.LEVERAGE,
                warning_threshold=1.5,
                hard_limit=2.0,
                action=RiskAction.BLOCK,
                description="最大杠杆 2.0x",
            ),
            RiskLimit(
                limit_id="beta_default",
                limit_type=LimitType.BETA,
                warning_threshold=0.8,
                hard_limit=1.2,
                action=RiskAction.ALERT,
                description="组合 Beta ≤ 1.2",
            ),
            RiskLimit(
                limit_id="industry_default",
                limit_type=LimitType.INDUSTRY,
                warning_threshold=0.3,
                hard_limit=0.4,
                action=RiskAction.ALERT,
                description="单行业集中度 ≤ 40%",
            ),
        ]
        for lim in defaults:
            self._limits[lim.limit_id] = lim

    def add_limit(self, limit: RiskLimit) -> None:
        """添加或覆盖限制规则。"""
        self._limits[limit.limit_id] = limit

    def remove_limit(self, limit_id: str) -> None:
        """移除限制规则。"""
        self._limits.pop(limit_id, None)

    def get_limit(self, limit_id: str) -> RiskLimit | None:
        return self._limits.get(limit_id)

    def get_all_limits(self) -> list[RiskLimit]:
        return list(self._limits.values())

    def set_enabled(self, limit_id: str, enabled: bool) -> None:
        lim = self._limits.get(limit_id)
        if lim:
            lim.enabled = enabled

    # ------------------------------------------------------------------ #
    #  校验（核心）
    # ------------------------------------------------------------------ #

    def check_all(self, report: ExposureReport) -> LimitReport:
        """
        对当前 ExposureReport 运行所有启用的限制校验。

        Returns
        -------
        LimitReport  包含所有校验结果的汇总报告
        """
        results: list[LimitCheckResult] = []

        for lim in self._limits.values():
            if not lim.enabled:
                continue
            result = self._check_one(lim, report)
            if result is not None:
                results.append(result)

        return LimitReport.from_results(results)

    def check_single_symbol(
        self,
        symbol:        str,
        target_weight: float,
        report:        ExposureReport,
    ) -> LimitReport:
        """
        检查新增一笔订单后，单票是否超限（交易前拦截）。

        Parameters
        ----------
        symbol        : 目标合约
        target_weight : 交易后的预期权重
        report        : 当前组合暴露报告
        """
        results: list[LimitCheckResult] = []

        for lim in self._limits.values():
            if not lim.enabled:
                continue
            if lim.limit_type != LimitType.POSITION:
                continue
            if lim.symbol and lim.symbol != symbol:
                continue

            passed, msg = check_position_limit(
                symbol            = symbol,
                current_weight    = target_weight,
                hard_limit        = lim.hard_limit,
                warning_threshold = lim.warning_threshold,
            )
            level     = RiskLevel.NORMAL if passed and not msg else (
                        RiskLevel.BREACH  if not passed else RiskLevel.WARNING)
            results.append(LimitCheckResult(
                limit_id          = lim.limit_id,
                limit_type        = lim.limit_type,
                symbol            = symbol,
                current_value     = target_weight,
                warning_threshold = lim.warning_threshold,
                hard_limit        = lim.hard_limit,
                risk_level        = level,
                is_blocked        = not passed,
                action            = lim.action,
                message           = msg,
            ))

        return LimitReport.from_results(results)

    # ------------------------------------------------------------------ #
    #  内部校验
    # ------------------------------------------------------------------ #

    def _check_one(
        self,
        lim:    RiskLimit,
        report: ExposureReport,
    ) -> LimitCheckResult | None:
        """对单条规则运行校验，返回 LimitCheckResult 或 None（不适用时）。"""

        if lim.limit_type == LimitType.POSITION:
            # 单票仓位：取最大单票权重
            if lim.symbol:
                value = report.symbol_weights.get(lim.symbol, 0.0)
                symbol = lim.symbol
            else:
                value  = report.max_single_weight
                symbol = report.max_single_symbol
            passed, msg = check_position_limit(
                symbol            = symbol,
                current_weight    = value,
                hard_limit        = lim.hard_limit,
                warning_threshold = lim.warning_threshold,
            )

        elif lim.limit_type == LimitType.LEVERAGE:
            value = report.leverage
            passed, msg = check_leverage_limit(
                leverage          = value,
                hard_limit        = lim.hard_limit,
                warning_threshold = lim.warning_threshold,
            )
            symbol = ""

        elif lim.limit_type == LimitType.BETA:
            value = report.portfolio_beta
            passed, msg = check_beta_limit(
                portfolio_beta    = value,
                hard_limit        = lim.hard_limit,
                warning_threshold = lim.warning_threshold,
            )
            symbol = ""

        elif lim.limit_type == LimitType.INDUSTRY:
            if lim.industry:
                value = report.industry_weights.get(lim.industry, 0.0)
                ind   = lim.industry
            else:
                value = report.max_industry_weight
                ind   = report.max_industry_name
            passed, msg = check_industry_limit(
                industry          = ind,
                industry_weight   = value,
                hard_limit        = lim.hard_limit,
                warning_threshold = lim.warning_threshold,
            )
            symbol = ""

        else:
            return None

        level = RiskLevel.NORMAL
        if not passed:
            level = RiskLevel.BREACH
        elif msg:
            level = RiskLevel.WARNING

        return LimitCheckResult(
            limit_id          = lim.limit_id,
            limit_type        = lim.limit_type,
            symbol            = symbol if lim.limit_type == LimitType.POSITION else "",
            current_value     = value,
            warning_threshold = lim.warning_threshold,
            hard_limit        = lim.hard_limit,
            risk_level        = level,
            is_blocked        = not passed and lim.action == RiskAction.BLOCK,
            action            = lim.action,
            message           = msg or f"{lim.label} = {value:.4f}  正常",
        )
