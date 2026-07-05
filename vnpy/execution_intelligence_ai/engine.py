"""
execution_intelligence_ai/engine.py  (Phase 1)

ExecutionIntelligenceEngine — 顶层引擎骨架。

Phase 1: 仅骨架，init/start/stop/process_order/dispatch_event。
Phase 2+: 逐步接入拆单/冲击/路由/反馈子引擎。
"""

from __future__ import annotations
from datetime import datetime

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME
from .event import (
    EVENT_EXECUTION_START,
    EVENT_ORDER_SLICED,
    EVENT_IMPACT_ESTIMATED,
    EVENT_ROUTE_SELECTED,
    EVENT_EXECUTION_COMPLETED,
    EVENT_FEEDBACK_UPDATED,
    EVENT_EXECUTION_ABORTED,
)
from .engine.execution_engine import ExecutionEngine
from .engine.strategy_engine  import StrategyEngine
from .engine.slicing_engine   import SlicingEngine
from .engine.impact_engine    import ImpactEngine
from .engine.routing_engine   import RoutingEngine
from .engine.feedback_engine  import FeedbackEngine
from .datasource.market_loader    import MarketLoader
from .datasource.order_loader     import OrderLoader
from .datasource.execution_loader import ExecutionLoader


class ExecutionIntelligenceEngine(BaseEngine):
    """
    Execution Intelligence 2.0 — 顶层引擎（Phase 1 骨架）。

    职责（Phase 1）：
      - 集成所有子引擎实例
      - 提供 process_order() 执行入口（空实现）
      - 提供 dispatch_event() 事件广播
      - 维护日志记录

    Phase 2+ 逐步实现各子引擎的真实逻辑。
    """

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)

        self._started_at:  datetime | None = None
        self._log_records: list[str]       = []

        # 子引擎实例
        self._exec_engine     = ExecutionEngine(log_fn=self._log)
        self._strategy_engine = StrategyEngine(log_fn=self._log)
        self._slicing_engine  = SlicingEngine(log_fn=self._log)
        self._impact_engine   = ImpactEngine(log_fn=self._log)
        self._routing_engine  = RoutingEngine(log_fn=self._log)
        self._feedback_engine = FeedbackEngine(log_fn=self._log)

        # 数据源
        self._market_loader    = MarketLoader(main_engine=main_engine)
        self._order_loader     = OrderLoader(main_engine=main_engine)
        self._execution_loader = ExecutionLoader(main_engine=main_engine)

        self._log(f"[{APP_NAME}] Engine created (Phase 1)")

    # ------------------------------------------------------------------ #
    #  BaseEngine 生命周期
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        self._log(f"[{APP_NAME}] init()")
        for eng in [self._exec_engine, self._strategy_engine,
                    self._slicing_engine, self._impact_engine,
                    self._routing_engine, self._feedback_engine]:
            eng.init()

    def start(self) -> None:
        self._started_at = datetime.now()
        self._log(f"[{APP_NAME}] start()")
        for eng in [self._exec_engine, self._strategy_engine,
                    self._slicing_engine, self._impact_engine,
                    self._routing_engine, self._feedback_engine]:
            eng.start()
        self.dispatch_event(EVENT_EXECUTION_START, {
            "status": "started", "phase": 1})

    def stop(self) -> None:
        self._log(f"[{APP_NAME}] stop()")
        for eng in [self._exec_engine, self._strategy_engine,
                    self._slicing_engine, self._impact_engine,
                    self._routing_engine, self._feedback_engine]:
            eng.stop()

    def close(self) -> None:
        self.stop()

    # ------------------------------------------------------------------ #
    #  执行入口（Phase 2+ 实现）
    # ------------------------------------------------------------------ #

    def process_order(self, order_data: dict) -> None:
        """
        接收来自上层（Portfolio / Risk）的父订单，启动执行流水线。

        Phase 1: 空实现，仅记录日志 + 广播事件。
        Phase 2+: 拆单 → 冲击估算 → 路由选择 → 执行 → 反馈。
        """
        oid = order_data.get("order_id", "unknown")
        self._log(f"[{APP_NAME}] process_order received: {oid}")
        self.dispatch_event(EVENT_EXECUTION_START, order_data)

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_summary(self) -> dict:
        uptime = 0.0
        if self._started_at:
            uptime = round(
                (datetime.now() - self._started_at).total_seconds(), 1)
        return {
            "app":     APP_NAME,
            "phase":   1,
            "uptime":  uptime,
            "market_loader":    self._market_loader.is_available(),
            "order_loader":     self._order_loader.is_available(),
            "execution_loader": self._execution_loader.is_available(),
        }

    def get_logs(self, limit: int = 200) -> list[str]:
        return self._log_records[-limit:]

    # ------------------------------------------------------------------ #
    #  事件广播
    # ------------------------------------------------------------------ #

    def dispatch_event(self, event_type: str, data: dict | None = None) -> None:
        self.event_engine.put(Event(event_type, data or {}))

    # ------------------------------------------------------------------ #
    #  内部日志
    # ------------------------------------------------------------------ #

    def _log(self, msg: str) -> None:
        ts = str(datetime.now())[:19]
        entry = f"{ts}  {msg}"
        self._log_records.append(entry)
        try:
            self.write_log(msg)
        except Exception:
            pass
