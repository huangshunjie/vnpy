"""
risk_engine_2/dispatcher.py

RiskEngine2 — Risk Engine 2.0 主引擎（Phase 2 实现）。

职责：
  - 持有 RiskCoreEngine（编排 ExposureEngine + LimitEngine）
  - 订阅 Execution Engine 成交回报 → 更新持仓暴露
  - 订阅 Portfolio Engine 净值更新 → 注入 NAV
  - 暴露 check_order() 供交易前拦截调用
  - 发布风控事件（EVENT_RISK_UPDATE / ALERT / LIMIT / LOG）
"""

from __future__ import annotations

import threading
import traceback

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME, RiskLevel, RiskAction
from .event import (
    EVENT_RISK_UPDATE,
    EVENT_RISK_ALERT,
    EVENT_RISK_LIMIT,
    EVENT_RISK_DRAWDOWN,
    EVENT_RISK_LOG,
    EVENT_RISK_PORTFOLIO_UPDATE,
    EVENT_RISK_FACTOR_EXPOSURE,
    EVENT_RISK_ORDER_GATE,
    EVENT_RISK_STYLE_DRIFT,
    EVENT_RISK_STATUS,
)
from .engine.risk_engine import RiskCoreEngine
from .model.limit_model import RiskLimit, LimitReport
from .model.exposure_model import ExposureReport
from .model.drawdown_model import DrawdownState, AlertRecord
from .model.risk_model import AttributionResult, AttributionReport

# 监听的上游事件（来自 Execution Engine）
_EVENT_FILL_UPDATE  = "eFillUpdate"
_EVENT_ORDER_UPDATE = "eOrderUpdate"
# 监听的上游事件（来自 Portfolio Engine）
_EVENT_PORTFOLIO_SIGNAL = "ePortfolioSignal"
_EVENT_EXECUTION_DONE   = "eExecutionDone"
# 行情事件（VeighNa 标准）
_EVENT_TICK = "eTick"

# Phase 5：三方联动上游事件
_EVENT_PORTFOLIO_UPDATE  = "ePortfolio.update"   # Portfolio Engine 组合状态
_EVENT_PORTFOLIO_RISK    = "ePortfolio.risk"     # Portfolio Engine 风险指标
_EVENT_FACTOR_FINISHED   = "eFactorFinished"     # Factor Research 计算完成
_EVENT_FACTOR_PLOT_READY = "eFactorPlotReady"    # Factor Research 图表数据
_EVENT_BATCH_ORDER_REQ   = "eBatchOrderReq"      # Execution 批量下单请求（拦截点）


class RiskEngine2(BaseEngine):
    """
    Risk Engine 2.0 主引擎（Phase 2）。

    Pre-Trade Risk：
      check_order() → LimitEngine 校验 → 返回 LimitReport
      any_blocked=True 时调用方应拒绝下单

    In-Trade（Phase 2 基础）：
      on_fill() → ExposureEngine 更新持仓 → 发布 EVENT_RISK_UPDATE
    """

    def __init__(
        self,
        main_engine:  MainEngine,
        event_engine: EventEngine,
        engine_name:  str = APP_NAME,
    ) -> None:
        super().__init__(main_engine, event_engine, engine_name)

        # 核心风控引擎
        self.core = RiskCoreEngine()

        self._running: bool         = False
        self._lock:    threading.Lock = threading.Lock()

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        """初始化：加载默认限制规则。"""
        self.core.init()
        self.write_log("Risk Engine 2.0 初始化完成。默认风控规则已加载。")

    def start(self) -> None:
        """启动引擎，订阅上游事件。"""
        if self._running:
            self.write_log("Risk Engine 2.0 已在运行中。")
            return

        reg = self.event_engine.register
        reg(_EVENT_FILL_UPDATE,      self._on_fill_update)
        reg(_EVENT_ORDER_UPDATE,     self._on_order_update)
        reg(_EVENT_PORTFOLIO_SIGNAL, self._on_portfolio_signal)
        reg(_EVENT_EXECUTION_DONE,   self._on_execution_done)

        reg(_EVENT_TICK,             self._on_tick)
        # Phase 5：三方联动
        reg(_EVENT_PORTFOLIO_UPDATE,  self._on_portfolio_update)
        reg(_EVENT_PORTFOLIO_RISK,    self._on_portfolio_risk)
        reg(_EVENT_FACTOR_FINISHED,   self._on_factor_finished)
        reg(_EVENT_FACTOR_PLOT_READY, self._on_factor_plot_ready)
        reg(_EVENT_BATCH_ORDER_REQ,   self._on_batch_order_req)

        self.core.start()
        self._running = True
        self._publish_status("running", "Risk Engine 2.0 已启动（Phase 5 全联动）。")
        self.write_log(
            "Risk Engine 2.0 已启动（Phase 5）。"
            "  仓位=25%  杠杆=2.0x  Beta=1.2  行业=40%"
            "  回撤预警=5%  回撤限制=10%  日亏损=5%"
            "  联动：Portfolio / Execution / Factor"
        )

    def stop(self) -> None:
        """停止引擎，注销上游事件。"""
        if not self._running:
            return

        unreg = self.event_engine.unregister
        unreg(_EVENT_FILL_UPDATE,      self._on_fill_update)
        unreg(_EVENT_ORDER_UPDATE,     self._on_order_update)
        unreg(_EVENT_PORTFOLIO_SIGNAL, self._on_portfolio_signal)
        unreg(_EVENT_EXECUTION_DONE,   self._on_execution_done)
        unreg(_EVENT_TICK,             self._on_tick)
        unreg(_EVENT_PORTFOLIO_UPDATE,  self._on_portfolio_update)
        unreg(_EVENT_PORTFOLIO_RISK,    self._on_portfolio_risk)
        unreg(_EVENT_FACTOR_FINISHED,   self._on_factor_finished)
        unreg(_EVENT_FACTOR_PLOT_READY, self._on_factor_plot_ready)
        unreg(_EVENT_BATCH_ORDER_REQ,   self._on_batch_order_req)

        self.core.stop()
        self._running = False
        self.write_log("Risk Engine 2.0 已停止。")

    def update(self, data=None) -> None:
        """主动刷新风险指标（定时器或外部触发）。"""
        if not self._running:
            return
        try:
            exposure = self.core.update()
            self._publish_update(exposure)
        except Exception as exc:
            self.write_log(f"[ERROR] update: {exc}")

    def process_event(self, event: Event) -> None:
        """通用事件入口（按类型路由）。"""
        if not self._running:
            return
        t = event.type
        if t == _EVENT_FILL_UPDATE:
            self._on_fill_update(event)
        elif t == _EVENT_PORTFOLIO_SIGNAL:
            self._on_portfolio_signal(event)

    def close(self) -> None:
        self.stop()

    # ------------------------------------------------------------------ #
    #  Pre-Trade Risk：交易前拦截接口（供外部调用）
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

        Returns
        -------
        LimitReport
          report.any_blocked=True  → 应拒绝下单，发布 EVENT_RISK_LIMIT
          report.warning_count > 0 → 发布 EVENT_RISK_ALERT

        示例：
            report = risk_engine.check_order("rb2501.SHFE","LONG",10,3500)
            if report.any_blocked:
                return  # 拒绝
        """
        if not self._running:
            return LimitReport()

        try:
            with self._lock:
                report = self.core.check_order(
                    symbol       = symbol,
                    direction    = direction,
                    volume       = volume,
                    signal_price = signal_price,
                    nav          = nav,
                )

            # 发布风控事件
            if report.any_blocked:
                msgs = [r.message for r in report.results if r.is_blocked]
                self._publish_limit("; ".join(msgs))
                self.write_log(f"[BLOCK] {symbol} {direction} 被风控阻断：{msgs[0]}")
            elif report.warning_count > 0:
                msgs = [r.message for r in report.results if r.risk_level == RiskLevel.WARNING]
                self._publish_alert("; ".join(msgs))

            return report

        except Exception as exc:
            self.write_log(f"[ERROR] check_order: {exc}\n{traceback.format_exc()}")
            return LimitReport()

    def is_trading_halted(self) -> bool:
        """查询交易是否已被暂停。"""
        return self.core._is_halted

    def halt_trading(self) -> None:
        """手动暂停交易。"""
        self.core.halt_trading()
        self.write_log("[HALT] 交易已暂停。")
        self._publish_limit("手动暂停交易。")

    def resume_trading(self) -> None:
        """恢复交易。"""
        self.core.resume_trading()
        self.write_log("[RESUME] 交易已恢复。")

    # ------------------------------------------------------------------ #
    #  配置接口（供 UI 调用）
    # ------------------------------------------------------------------ #

    def add_limit(self, limit: RiskLimit) -> None:
        """添加或覆盖限制规则。"""
        self.core.add_limit(limit)
        self.write_log(f"风控规则已更新：{limit.label}  hard={limit.hard_limit}")

    def remove_limit(self, limit_id: str) -> None:
        self.core.remove_limit(limit_id)
        self.write_log(f"风控规则已移除：{limit_id}")

    def get_limits(self) -> list[RiskLimit]:
        return self.core.get_limits()

    def set_nav(self, nav: float) -> None:
        """注入组合净值（来自 Portfolio Engine 或 UI 手动设置）。"""
        self.core.set_nav(nav)

    def set_symbol_betas(self, mapping: dict[str, float]) -> None:
        """注入 Beta 映射 {symbol: beta}。"""
        self.core.set_symbol_betas(mapping)

    def set_symbol_industry(self, mapping: dict[str, str]) -> None:
        """注入行业分类映射 {symbol: industry}。"""
        self.core.set_symbol_industry(mapping)

    def get_exposure(self) -> ExposureReport | None:
        """返回最新暴露报告（供 UI 展示）。"""
        return self.core.get_last_exposure()

    def get_last_limit_report(self) -> LimitReport | None:
        return self.core.get_last_report()

    def get_drawdown_state(self) -> DrawdownState | None:
        """返回最新回撤状态（供 UI 展示）。"""
        return self.core.get_drawdown_state()

    def get_alert_history(self) -> list[AlertRecord]:
        """返回所有预警历史记录。"""
        return self.core.get_alert_history()

    def acknowledge_alert(self, alert_id: str) -> None:
        self.core.acknowledge_alert(alert_id)

    def set_drawdown_thresholds(
        self,
        drawdown_warning: float = 0.05,
        drawdown_limit:   float = 0.10,
        daily_loss_warn:  float = 0.03,
        daily_loss_limit: float = 0.05,
    ) -> None:
        """更新回撤阈值（UI 调用）。"""
        self.core.set_drawdown_thresholds(
            drawdown_warning  = drawdown_warning,
            drawdown_limit    = drawdown_limit,
            daily_loss_warn   = daily_loss_warn,
            daily_loss_limit  = daily_loss_limit,
        )
        self.write_log(
            f'回撤阈值更新：warning={drawdown_warning:.1%}  '
            f'limit={drawdown_limit:.1%}  '
            f'daily_warn={daily_loss_warn:.1%}  '
            f'daily_limit={daily_loss_limit:.1%}'
        )

    # ------------------------------------------------------------------ #
    #  Phase 5: 三方联动事件处理器
    # ------------------------------------------------------------------ #

    def _on_portfolio_update(self, event: Event) -> None:
        """
        Portfolio Engine 组合状态更新。

        payload: {nav, weights, positions, industry, betas}
        """
        if not self._running:
            return
        try:
            payload = event.data
            if not isinstance(payload, dict):
                return
            with self._lock:
                self.core.on_portfolio_update(payload)

            nav = float(payload.get("nav", 0.0))
            n_positions = len(payload.get("weights", {}))
            self.write_log(
                f"[Portfolio] NAV={nav:,.0f}  持仓数={n_positions}"
            )
            # 通知 UI 刷新暴露
            exposure = self.core.update()
            self._publish_update(exposure)
            self.event_engine.put(
                Event(EVENT_RISK_PORTFOLIO_UPDATE, payload)
            )
        except Exception as exc:
            self.write_log(f"[ERROR] _on_portfolio_update: {exc}")

    def _on_portfolio_risk(self, event: Event) -> None:
        """Portfolio Engine 风险指标更新（接收 beta / vol 等，注入 ExposureEngine）。"""
        if not self._running:
            return
        try:
            data = event.data
            if isinstance(data, dict):
                betas = data.get("betas", {})
                if betas:
                    self.core.set_symbol_betas(betas)
        except Exception as exc:
            self.write_log(f"[ERROR] _on_portfolio_risk: {exc}")

    def _on_factor_finished(self, event: Event) -> None:
        """
        Factor Research 计算完成 → 触发归因更新。

        在整批因子计算完成后触发一次完整归因。
        """
        if not self._running:
            return
        try:
            result = self.core.compute_attribution()
            if result is not None:
                self.event_engine.put(Event("eAttributionResult", result))
                self.write_log(
                    f"[Factor→归因] PnL={result.total_pnl:+.2f}  "
                    f"Beta={result.portfolio_beta:.3f}"
                )
        except Exception as exc:
            self.write_log(f"[ERROR] _on_factor_finished: {exc}")

    def _on_factor_plot_ready(self, event: Event) -> None:
        """
        Factor Research 图表数据就绪 → 更新因子暴露 + 风格漂移检测。

        event.data: {"tab": str, "payload": {factor: str, ic_series: list, ...}}
        """
        if not self._running:
            return
        try:
            outer = event.data
            if not isinstance(outer, dict):
                return
            payload = outer.get("payload", {})
            if not isinstance(payload, dict):
                return

            factor_name = payload.get("factor", outer.get("tab", "unknown"))
            # 截面暴露：{symbol: loading}（Factor Research 输出格式）
            exposures: dict[str, float] = payload.get("exposures", {})
            if not exposures:
                return
            ic = float(payload.get("ic", 0.0))

            with self._lock:
                drift_info = self.core.on_factor_exposure_update(
                    factor_name, exposures, ic
                )

            self.event_engine.put(
                Event(EVENT_RISK_FACTOR_EXPOSURE, {
                    "factor": factor_name,
                    "exposures": exposures,
                    "ic": ic,
                })
            )

            if drift_info is not None:
                self.event_engine.put(
                    Event(EVENT_RISK_STYLE_DRIFT, drift_info)
                )
                self._publish_alert(drift_info["message"])
                self.write_log(f"[风格漂移] {drift_info['message']}")
        except Exception as exc:
            self.write_log(f"[ERROR] _on_factor_plot_ready: {exc}")

    def _on_batch_order_req(self, event: Event) -> None:
        """
        Execution Engine 批量下单请求拦截点（Phase 5 安全门）。

        event.data: dict 或 list[dict]
        每笔订单必须通过 gate_order() 校验，失败则发布 EVENT_RISK_ORDER_GATE 阻断。
        """
        if not self._running:
            return
        try:
            data = event.data
            orders = data if isinstance(data, list) else [data]
            blocked = []
            for order in orders:
                if not isinstance(order, dict):
                    continue
                sym   = str(order.get("symbol", ""))
                direc = str(order.get("direction", "LONG"))
                vol   = float(order.get("volume", 0.0))
                price = float(order.get("price", 0.0))
                if not sym or vol <= 0 or price <= 0:
                    continue
                with self._lock:
                    allowed, reason = self.core.gate_order(
                        sym, direc, vol, price
                    )
                if not allowed:
                    blocked.append({"order": order, "reason": reason})
                    self.write_log(f"[GATE BLOCK] {sym} {direc} {vol:.0f}: {reason}")

            if blocked:
                self.event_engine.put(
                    Event(EVENT_RISK_ORDER_GATE, {"blocked": blocked})
                )
                self._publish_limit(
                    f"批量下单拦截：{len(blocked)} 笔被风控阻断"
                )
        except Exception as exc:
            self.write_log(f"[ERROR] _on_batch_order_req: {exc}")

    # ------------------------------------------------------------------ #
    #  Phase 4: 归因接口
    # ------------------------------------------------------------------ #

    def set_symbol_strategy(self, mapping: dict[str, str]) -> None:
        """注入策略映射 {symbol: strategy_name}（供 UI / 外部调用）。"""
        self.core.set_symbol_strategy(mapping)
        self.write_log(f'策略映射已更新：{len(mapping)} 条')

    def set_factor_exposures(
        self,
        exposures: dict[str, dict[str, float]],
    ) -> None:
        """注入因子暴露矩阵（来自 Factor Research Engine）。"""
        self.core.set_factor_exposures(exposures)
        self.write_log(f'因子暴露已更新：{len(exposures)} 个因子')

    def compute_attribution(
        self,
        symbol_pnl: dict[str, float] | None = None,
    ) -> AttributionResult | None:
        """手动触发归因计算（UI 按钮或定时器调用）。"""
        if not self._running:
            return None
        try:
            result = self.core.compute_attribution(symbol_pnl)
            if result is not None:
                self.event_engine.put(Event("eAttributionResult", result))
            return result
        except Exception as exc:
            self.write_log(f'[ERROR] compute_attribution: {exc}')
            return None

    def get_attribution_report(self) -> AttributionReport:
        """返回完整归因报告历史。"""
        return self.core.get_attribution_report()

    def get_latest_attribution(self) -> AttributionResult | None:
        return self.core.get_latest_attribution()

    def get_attribution_text(self) -> str:
        """返回最新归因文本摘要（供 UI 日志区展示）。"""
        return self.core.get_attribution_text()

    # ------------------------------------------------------------------ #
    #  上游事件处理器
    # ------------------------------------------------------------------ #

    def _on_fill_update(self, event: Event) -> None:
        """
        Execution Engine 成交回报 → 更新持仓暴露。

        event.data 可以是 FillRecord 对象或字典。
        """
        if not self._running:
            return
        try:
            data = event.data
            # 兼容 FillRecord 对象和字典
            if hasattr(data, "symbol"):
                fill = {
                    "symbol":    data.symbol,
                    "direction": data.direction,
                    "volume":    data.fill_volume,
                    "price":     data.fill_price,
                }
            elif isinstance(data, dict):
                fill = data
            else:
                return

            with self._lock:
                exposure = self.core.on_fill(fill)

            self._publish_update(exposure)

            # Phase 3：发布回撤 + 预警事件
            dd = self.core.get_drawdown_state()
            if dd is not None:
                self._publish_drawdown(dd)
            for alert in self.core.get_alert_history()[-5:]:
                if not alert.acknowledged:
                    self._publish_alert(alert.message)
                    if alert.action.value == 'halt_trading':
                        self.write_log('[AUTO-HALT] 日亏损超限，交易已自动暂停。')

        except Exception as exc:
            self.write_log(f"[ERROR] _on_fill_update: {exc}")

    def _on_order_update(self, event: Event) -> None:
        """Order 状态变更（Phase 2：仅记录，Phase 3 扩展）。"""
        pass

    def _on_portfolio_signal(self, event: Event) -> None:
        """
        Portfolio Engine 信号：提取 nav 注入 ExposureEngine。
        """
        if not self._running:
            return
        data = event.data
        if isinstance(data, dict):
            nav = float(data.get("nav", 0.0))
            if nav > 0:
                self.core.set_nav(nav)

    def _on_execution_done(self, event: Event) -> None:
        """批量执行完成后触发完整风险刷新 + 归因计算。"""
        if not self._running:
            return
        self.update()
        # Phase 4：每次批量执行完成后自动触发归因
        try:
            result = self.core.compute_attribution()
            if result is not None:
                self.event_engine.put(Event("eAttributionResult", result))
                self.write_log(
                    f"[归因] PnL={result.total_pnl:+.2f}  "
                    f"Beta={result.portfolio_beta:.3f}  "
                    f"MaxDD={result.max_drawdown_pct:.2%}"
                )
        except Exception as exc:
            self.write_log(f"[WARN] 归因计算失败：{exc}")

    # ------------------------------------------------------------------ #
    #  风控事件发布
    # ------------------------------------------------------------------ #

    def _publish_update(self, exposure: ExposureReport) -> None:
        self.event_engine.put(Event(EVENT_RISK_UPDATE, exposure))

    def _publish_alert(self, msg: str) -> None:
        self.event_engine.put(Event(EVENT_RISK_ALERT, msg))

    def _publish_limit(self, msg: str) -> None:
        self.event_engine.put(Event(EVENT_RISK_LIMIT, msg))

    def _publish_drawdown(self, state: DrawdownState) -> None:
        self.event_engine.put(Event(EVENT_RISK_DRAWDOWN, state))

    def _on_tick(self, event) -> None:
        """行情 Tick → 更新持仓最新价 + 刷新浮动 PnL。"""
        if not self._running:
            return
        try:
            tick = event.data
            if hasattr(tick, 'symbol') and hasattr(tick, 'last_price'):
                sym   = tick.symbol
                price = float(tick.last_price)
                if price > 0:
                    with self._lock:
                        self.core.exposure_engine.on_price_update(sym, price)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    #  日志工具
    # ------------------------------------------------------------------ #

    def write_log(self, msg: str) -> None:
        self.event_engine.put(Event(EVENT_RISK_LOG, msg))

    # ------------------------------------------------------------------ #
    #  Phase 5: 联动查询接口
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
        交易安全门（供 Execution Engine 直接调用）。

        Returns
        -------
        (allowed: bool, reason: str)
          allowed=False → 调用方应拒绝下单
        """
        if not self._running:
            return True, ""   # 引擎未启动时不拦截
        return self.core.gate_order(symbol, direction, volume, signal_price, nav)

    def get_factor_exposures(self) -> dict[str, float]:
        """返回当前各因子的组合暴露水平 {factor_name: exposure}。"""
        return self.core.get_factor_exposures()

    def set_drift_threshold(self, threshold: float) -> None:
        """设置风格漂移检测阈值（默认 0.15）。"""
        self.core.set_drift_threshold(threshold)
        self.write_log(f"[Factor] 风格漂移阈值已更新：{threshold:.4f}")

    def _publish_status(self, status: str, message: str) -> None:
        """发布全局状态变更事件（Phase 5）。"""
        from .event import EVENT_RISK_STATUS
        self.event_engine.put(
            Event(EVENT_RISK_STATUS, {"status": status, "message": message})
        )
