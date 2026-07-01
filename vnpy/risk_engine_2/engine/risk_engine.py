"""
risk_engine_2/engine/risk_engine.py

RiskCoreEngine — 风控核心编排引擎（Phase 2 实现）。

职责：
  - 持有 ExposureEngine + LimitEngine
  - 接收成交回报 → 更新暴露 → 校验限制 → 发出风控事件
  - 交易前拦截：check_order() 供 dispatcher 在发单前调用
"""

from __future__ import annotations

from datetime import datetime

from ..model.exposure_model import ExposureReport
from ..model.limit_model import LimitReport, RiskLimit, LimitCheckResult
from ..constant import RiskLevel, RiskAction, LimitType
from .exposure_engine import ExposureEngine
from .limit_engine import LimitEngine
from .drawdown_engine import DrawdownEngine
from .alert_engine import AlertEngine, AlertRule
from ..model.drawdown_model import DrawdownState, AlertRecord
from ..model.risk_model import AttributionResult, AttributionReport
from .attribution_engine import AttributionEngine


class RiskCoreEngine:
    """
    风控核心编排引擎（Phase 2）。

    使用方式：
        core = RiskCoreEngine()
        core.set_nav(1_000_000.0)
        report = core.check_order("rb2501.SHFE", "LONG", 10.0, 3500.0)
        if report.any_blocked:
            # 阻断订单
        core.on_fill(fill_dict)   # 成交后更新暴露
    """

    def __init__(self) -> None:
        self.exposure_engine   = ExposureEngine()
        self.limit_engine      = LimitEngine()
        self.drawdown_engine   = DrawdownEngine()
        self.alert_engine      = AlertEngine()
        self.attribution_engine = AttributionEngine()

        self._last_exposure:  ExposureReport | None = None
        self._last_report:    LimitReport    | None = None
        self._last_drawdown:  DrawdownState  | None = None
        self._alert_history:  list[AlertRecord]     = []

        # 风控状态
        self._is_halted:  bool = False   # True = 已暂停交易

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        pass

    def start(self) -> None:
        self._is_halted = False

    def stop(self) -> None:
        pass

    # ------------------------------------------------------------------ #
    #  外部数据注入
    # ------------------------------------------------------------------ #

    def set_nav(self, nav: float) -> None:
        """注入组合净值（来自 Portfolio Engine）。"""
        self.exposure_engine.set_nav(nav)
        self.drawdown_engine.set_nav(nav)

    def set_symbol_industry(self, mapping: dict[str, str]) -> None:
        self.exposure_engine.set_symbol_industry(mapping)
        self.attribution_engine.set_symbol_industry(mapping)

    def set_symbol_betas(self, mapping: dict[str, float]) -> None:
        self.exposure_engine.set_symbol_betas(mapping)
        self.attribution_engine.set_symbol_betas(mapping)

    # ------------------------------------------------------------------ #
    #  交易前拦截（Pre-Trade Risk）
    # ------------------------------------------------------------------ #

    def check_order(
        self,
        symbol:       str,
        direction:    str,
        volume:       float,
        signal_price: float,
        nav:          float = 0.0,
    ) -> LimitReport:
        """
        交易前风控校验（安全门）。

        1. 计算该笔订单成交后的预期持仓权重
        2. 对全组合限制运行完整校验
        3. 对单票做追加校验
        4. 返回 LimitReport（any_blocked=True 时调用方应拒绝下单）

        Parameters
        ----------
        symbol       : 目标合约
        direction    : "LONG" / "SHORT"
        volume       : 下单数量
        signal_price : 信号价格（用于估算名义价值）
        nav          : 组合净值（0 = 使用已注入的值）
        """
        if self._is_halted:
            from ..model.limit_model import LimitCheckResult
            result = LimitCheckResult(
                limit_id      = "halt",
                limit_type    = LimitType.TOTAL,
                current_value = 0.0,
                risk_level    = RiskLevel.BREACH,
                is_blocked    = True,
                action        = RiskAction.HALT_TRADING,
                message       = "风控已暂停交易，拒绝下单。",
            )
            return LimitReport.from_results([result])

        if nav > 0:
            self.exposure_engine.set_nav(nav)

        # 当前暴露报告
        exposure = self.exposure_engine.compute_report()
        self._last_exposure = exposure

        # 全组合限制校验
        full_report = self.limit_engine.check_all(exposure)

        # 单票追加校验：估算交易后权重
        if signal_price > 0 and exposure.nav > 0:
            order_notional = volume * signal_price
            signed = 1.0 if direction == "LONG" else -1.0
            current_mv = (exposure.symbol_weights.get(symbol, 0.0)
                          * exposure.nav)
            projected_mv  = current_mv + signed * order_notional
            projected_w   = projected_mv / exposure.nav
            single_report = self.limit_engine.check_single_symbol(
                symbol        = symbol,
                target_weight = abs(projected_w),
                report        = exposure,
            )
            all_results = full_report.results + single_report.results
            full_report  = LimitReport.from_results(all_results)

        self._last_report = full_report
        return full_report

    # ------------------------------------------------------------------ #
    #  成交回报处理（In-Trade 持仓更新）
    # ------------------------------------------------------------------ #

    def on_fill(self, fill: dict) -> ExposureReport:
        """
        处理成交回报，更新持仓暴露，返回最新 ExposureReport。

        fill 格式与 ExposureEngine.on_fill() 相同。
        """
        self.exposure_engine.on_fill(fill)
        self.drawdown_engine.on_fill(fill)
        exposure = self.exposure_engine.compute_report()
        self._last_exposure = exposure

        # 更新浮动 PnL（用所有持仓浮动 PnL 之和）
        unrealized = sum(
            p.unrealized_pnl
            for p in self.exposure_engine.get_snapshot().positions.values()
        )
        self.drawdown_engine.on_price_update(unrealized)
        self._last_drawdown = self.drawdown_engine.get_state()

        # Phase 3：预警检查
        alerts = self.alert_engine.check_drawdown(self._last_drawdown)
        alerts += self.alert_engine.check_exposure(exposure)
        self._alert_history.extend(alerts)

        # 自动风控动作（回撤 / 日亏损硬限制）
        from ..constant import RiskAction
        for alert in alerts:
            if alert.action == RiskAction.HALT_TRADING and not self._is_halted:
                self._is_halted = True

        return exposure

    def on_price_update(self, symbol: str, last_price: float) -> None:
        """更新最新价格（来自行情）。"""
        self.exposure_engine.on_price_update(symbol, last_price)

    # ------------------------------------------------------------------ #
    #  风控动作
    # ------------------------------------------------------------------ #

    def halt_trading(self) -> None:
        """暂停所有交易（重大风险触发）。"""
        self._is_halted = True

    def resume_trading(self) -> None:
        """恢复交易。"""
        self._is_halted = False

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_last_exposure(self) -> ExposureReport | None:
        return self._last_exposure

    def get_last_report(self) -> LimitReport | None:
        return self._last_report

    def get_limits(self) -> list[RiskLimit]:
        return self.limit_engine.get_all_limits()

    def add_limit(self, limit: RiskLimit) -> None:
        self.limit_engine.add_limit(limit)

    def remove_limit(self, limit_id: str) -> None:
        self.limit_engine.remove_limit(limit_id)

    def update(self) -> ExposureReport:
        """主动刷新暴露报告（定时器调用）。"""
        exposure = self.exposure_engine.compute_report()
        self._last_exposure = exposure
        # 同步回撤状态
        unrealized = sum(
            p.unrealized_pnl
            for p in self.exposure_engine.get_snapshot().positions.values()
        )
        self.drawdown_engine.on_price_update(unrealized)
        self._last_drawdown = self.drawdown_engine.get_state()
        return exposure

    def clear(self) -> None:
        """清空持仓和历史记录（新一轮回测前调用）。"""
        self.exposure_engine.clear()
        self.drawdown_engine.clear()
        self.alert_engine.clear_history()
        self.attribution_engine.clear()
        self._last_exposure = None
        self._last_report   = None
        self._last_drawdown = None
        self._alert_history = []
        self._is_halted     = False

    def get_drawdown_state(self) -> DrawdownState | None:
        """返回最新回撤状态。"""
        return self._last_drawdown

    def get_alert_history(self) -> list[AlertRecord]:
        """返回所有预警记录。"""
        return list(self._alert_history)

    def get_unacknowledged_alerts(self) -> list[AlertRecord]:
        return self.alert_engine.get_unacknowledged()

    def acknowledge_alert(self, alert_id: str) -> None:
        self.alert_engine.acknowledge(alert_id)

    def set_drawdown_thresholds(
        self,
        drawdown_warning: float = 0.05,
        drawdown_limit:   float = 0.10,
        daily_loss_warn:  float = 0.03,
        daily_loss_limit: float = 0.05,
    ) -> None:
        """更新回撤 / 日亏损阈值（UI 调用）。"""
        self.drawdown_engine.set_thresholds(
            drawdown_warning  = drawdown_warning,
            drawdown_limit    = drawdown_limit,
            daily_loss_warn   = daily_loss_warn,
            daily_loss_limit  = daily_loss_limit,
        )

    # ------------------------------------------------------------------ #
    #  Phase 4: 归因接口
    # ------------------------------------------------------------------ #

    def set_symbol_strategy(self, mapping: dict[str, str]) -> None:
        """注入策略映射 {symbol: strategy_name}。"""
        self.attribution_engine.set_symbol_strategy(mapping)

    def set_factor_exposures(
        self,
        exposures: dict[str, dict[str, float]],
    ) -> None:
        """注入因子暴露矩阵 {factor_name: {symbol: loading}}。"""
        self.attribution_engine.set_factor_exposures(exposures)

    def compute_attribution(
        self,
        symbol_pnl: dict[str, float] | None = None,
    ) -> AttributionResult | None:
        """触发一次归因计算，返回 AttributionResult。"""
        exposure = self._last_exposure
        if exposure is None:
            exposure = self.exposure_engine.compute_report()
        return self.attribution_engine.compute(
            exposure   = exposure,
            drawdown   = self._last_drawdown,
            symbol_pnl = symbol_pnl,
        )

    def get_attribution_report(self) -> AttributionReport:
        return self.attribution_engine.get_report()

    def get_latest_attribution(self) -> AttributionResult | None:
        return self.attribution_engine.get_latest()

    def get_attribution_text(self) -> str:
        return self.attribution_engine.get_text_summary()

    # ------------------------------------------------------------------ #
    #  Phase 5: Portfolio Engine 联动
    # ------------------------------------------------------------------ #

    def on_portfolio_update(self, payload: dict) -> None:
        """
        接收 Portfolio Engine 实时推送的组合状态。

        payload 格式：
        {
          "nav":       float,
          "weights":   {symbol: float},
          "positions": list[dict],
          "industry":  {symbol: str},    # 可选
          "betas":     {symbol: float},  # 可选
        }
        """
        nav     = float(payload.get("nav", 0.0))
        weights = payload.get("weights", {})
        industry= payload.get("industry", {})
        betas   = payload.get("betas", {})

        if nav > 0:
            self.set_nav(nav)

        # 行业 / Beta 映射更新
        if industry:
            self.exposure_engine.set_symbol_industry(industry)
            self.attribution_engine.set_symbol_industry(industry)
        if betas:
            self.exposure_engine.set_symbol_betas(betas)
            self.attribution_engine.set_symbol_betas(betas)

        # 用 Portfolio 权重校准 ExposureEngine 快照
        for sym, w in weights.items():
            mv = w * nav
            pos = self.exposure_engine.get_snapshot().positions.get(sym)
            if pos is not None:
                pos.market_value = mv

    # ------------------------------------------------------------------ #
    #  Phase 5: Execution Engine 联动 — 下单前风控门
    # ------------------------------------------------------------------ #

    def gate_order(
        self,
        symbol:       str,
        direction:    str,
        volume:       float,
        signal_price: float,
        nav:          float = 0.0,
    ) -> tuple[bool, str]:
        """
        交易安全门：封装 check_order()，返回 (allowed, reason)。

        allowed=True  → 放行
        allowed=False → 拒绝，reason 说明原因

        与 check_order() 的区别：
          - 返回 bool 而非 LimitReport，适合 Execution Engine 直接调用
          - 自动记录拦截日志
        """
        report = self.check_order(symbol, direction, volume, signal_price, nav)
        if report.any_blocked:
            reasons = [r.message for r in report.results if r.is_blocked]
            return False, "; ".join(reasons)
        return True, ""

    # ------------------------------------------------------------------ #
    #  Phase 5: Factor Research 联动 — 因子暴露 + 风格漂移检测
    # ------------------------------------------------------------------ #

    def on_factor_exposure_update(
        self,
        factor_name: str,
        exposures:   dict[str, float],
        ic:          float = 0.0,
    ) -> dict | None:
        """
        接收 Factor Research Engine 推送的因子截面暴露数据。

        1. 更新归因引擎的因子暴露矩阵
        2. 检测风格漂移（当前组合暴露 vs 基准暴露）
        3. 若漂移超阈值，返回漂移警报 dict；否则返回 None

        Parameters
        ----------
        factor_name : 因子名称（如 "momentum_20"）
        exposures   : {symbol: loading}  当前截面因子暴露
        ic          : 本期 IC 值（可选，用于因子有效性过滤）
        """
        # 更新归因引擎
        self.attribution_engine.set_factor_exposure(factor_name, exposures)

        # 当前组合对该因子的暴露 = Σ (w_i × loading_i)
        snap    = self.exposure_engine.get_snapshot()
        nav     = self._last_exposure.nav if self._last_exposure else 0.0
        current_exposure = 0.0
        for sym, loading in exposures.items():
            pos = snap.positions.get(sym)
            if pos is not None and nav > 0:
                w = pos.market_value / nav
                current_exposure += w * loading

        # 风格漂移：与上次记录的暴露比较
        if not hasattr(self, "_factor_exposure_history"):
            self._factor_exposure_history: dict[str, float] = {}

        prev = self._factor_exposure_history.get(factor_name, 0.0)
        drift = abs(current_exposure - prev)
        self._factor_exposure_history[factor_name] = current_exposure

        # 漂移阈值（可通过 set_drift_threshold 调整）
        threshold = getattr(self, "_drift_threshold", 0.15)
        if drift >= threshold:
            return {
                "factor":    factor_name,
                "drift":     drift,
                "current":   current_exposure,
                "previous":  prev,
                "threshold": threshold,
                "message": (
                    f"风格漂移检测：{factor_name}  "
                    f"Δ={drift:.4f} >= 阈值={threshold:.4f}  "
                    f"当前暴露={current_exposure:.4f}"
                ),
            }
        return None

    def set_drift_threshold(self, threshold: float) -> None:
        """设置风格漂移检测阈值（默认 0.15）。"""
        self._drift_threshold = max(0.01, threshold)

    def get_factor_exposures(self) -> dict[str, float]:
        """返回当前各因子的组合暴露水平。"""
        return dict(getattr(self, "_factor_exposure_history", {}))
