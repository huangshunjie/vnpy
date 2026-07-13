"""
global_portfolio_intelligence/engine.py

GlobalPortfolioEngine — 顶层引擎（Phase 1 骨架）。

职责：
  - 作为 VeighNa BaseEngine 子类，被 MainEngine 管理
  - 持有所有子引擎的引用（Phase 2+ 逐步激活）
  - 提供 compute_global_state() 统一入口
  - 通过 dispatch_event() 向全系统广播状态变更

Phase 1：仅骨架，无任何优化逻辑。
"""
from __future__ import annotations
from datetime import datetime

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME, SystemStatus
from .event import (
    EVENT_GLOBAL_STATE_UPDATED,
    EVENT_OBJECTIVE_UPDATED,
    EVENT_ALLOCATION_UPDATED,
    EVENT_REBALANCE_TRIGGERED,
    EVENT_SYSTEM_OPTIMIZED,
)


class GlobalPortfolioEngine(BaseEngine):
    """
    全局组合智能系统 — 顶层引擎（Phase 1）。

    方法说明：
      init()                — 初始化所有子引擎
      start()               — 启动系统，开始监听事件
      stop()                — 停止系统
      compute_global_state()— 计算全局状态快照（Phase 2+ 实现）
      dispatch_event()      — 向事件总线广播系统事件
    """

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)

        self._status:      SystemStatus    = SystemStatus.IDLE
        self._started_at:  datetime | None = None
        self._log_records: list[str]       = []

        self._log(f"[{APP_NAME}] Engine created (Phase 1)")

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        """初始化引擎及所有子模块（Phase 2+ 在此激活子引擎）。"""
        self._log(f"[{APP_NAME}] init()")
        self._status = SystemStatus.IDLE

    def start(self) -> None:
        """启动引擎，开始监听全系统事件。"""
        self._started_at = datetime.now()
        self._status     = SystemStatus.RUNNING
        self._log(f"[{APP_NAME}] start()")
        self.dispatch_event(EVENT_GLOBAL_STATE_UPDATED, {
            "status": self._status.value,
            "phase":  1,
        })

    def stop(self) -> None:
        """停止引擎。"""
        self._status = SystemStatus.STOPPED
        self._log(f"[{APP_NAME}] stop()")

    def close(self) -> None:
        self.stop()

    # ------------------------------------------------------------------ #
    #  核心接口（Phase 1 为空实现，Phase 2+ 填充逻辑）
    # ------------------------------------------------------------------ #

    def compute_global_state(self) -> dict:
        """
        计算全局状态快照。

        Phase 1：返回空骨架。
        Phase 2+：聚合 Alpha / Portfolio / Risk / Execution 状态，
                  驱动统一目标函数计算。
        """
        state = {
            "status":     self._status.value,
            "phase":      1,
            "uptime":     self._uptime(),
            "timestamp":  str(datetime.now())[:19],
            # Phase 2+ 填充：
            "objective":  {},
            "allocation": {},
            "performance":{},
            "rebalance":  {},
        }
        self.dispatch_event(EVENT_GLOBAL_STATE_UPDATED, state)
        return state

    # ------------------------------------------------------------------ #
    #  事件
    # ------------------------------------------------------------------ #

    def dispatch_event(self, event_type: str, data: dict | None = None) -> None:
        """向 VeighNa 事件总线广播系统事件。"""
        self.event_engine.put(Event(event_type, data or {}))

    # ------------------------------------------------------------------ #
    #  辅助
    # ------------------------------------------------------------------ #

    def get_logs(self, limit: int = 200) -> list[str]:
        return self._log_records[-limit:]

    def get_status(self) -> SystemStatus:
        return self._status

    def _uptime(self) -> float:
        if self._started_at is None:
            return 0.0
        return round((datetime.now() - self._started_at).total_seconds(), 1)

    def _log(self, msg: str) -> None:
        ts    = str(datetime.now())[:19]
        entry = f"{ts}  {msg}"
        self._log_records.append(entry)
        try:
            self.write_log(msg)
        except Exception:
            pass
