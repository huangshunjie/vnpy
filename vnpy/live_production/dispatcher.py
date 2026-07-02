"""
live_production/dispatcher.py

LiveProductionEngine — 顶层引擎（Phase 2）。

Phase 2 新增：
  - 代理 mark_degraded / start_recovery / recovery_success /
    recovery_fail / clear_degraded / reset
  - 暴露 state_history / state_summary
"""

from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME, TradingState, SystemHealthState
from .event import EVENT_PROD_START, EVENT_PROD_STOP, EVENT_STATE_CHANGE
from .engine.production_engine import ProductionEngine
from .engine.recovery_engine import RecoveryTrigger, RecoveryRecord, RecoveryPhase
from .engine.failover_engine import FailoverEngine, FailoverReason, FailoverRecord
from .engine.order_sync_engine import OrderSyncEngine, OrderSnapshot
from .engine.health_monitor import HealthMonitor, HealthThresholds, HealthSnapshot
from .engine.state_manager import (
    TRIGGER_EXECUTION_ERROR,
    TRIGGER_RISK_ALERT,
    TRIGGER_MODULE_ERROR,
)


class LiveProductionEngine(BaseEngine):
    """Live Production System 顶层引擎（Phase 2）。"""

    def __init__(
        self,
        main_engine:  MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._engine: ProductionEngine | None = None

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        if self._engine is None:
            self._engine = ProductionEngine(
                event_put_fn=self.event_engine.put
            )
        self._engine.init()

    def start(self) -> None:
        if self._engine is None:
            self.init()
        self._engine.start()

    def stop(self, reason: str = "") -> None:
        if self._engine is None:
            return
        self._engine.stop(reason)

    # ------------------------------------------------------------------ #
    #  状态更新（通用）
    # ------------------------------------------------------------------ #

    def update_state(
        self,
        new_state: TradingState | str,
        reason:    str = "",
    ) -> None:
        if self._engine is None:
            return
        if isinstance(new_state, str):
            new_state = TradingState(new_state)
        self._engine.update_state(new_state, reason)

    # ------------------------------------------------------------------ #
    #  状态转换快捷接口（Phase 2）
    # ------------------------------------------------------------------ #

    def mark_degraded(
        self,
        reason:  str = "",
        trigger: str = TRIGGER_MODULE_ERROR,
    ) -> bool:
        """RUNNING → DEGRADED（外部模块异常时调用）。"""
        if self._engine is None:
            return False
        return self._engine.mark_degraded(reason, trigger)

    def start_recovery(self, reason: str = "") -> bool:
        """DEGRADED → RECOVERY。"""
        if self._engine is None:
            return False
        return self._engine.start_recovery(reason)

    def recovery_success(self, reason: str = "") -> bool:
        """RECOVERY → RUNNING。"""
        if self._engine is None:
            return False
        return self._engine.recovery_success(reason)

    def recovery_fail(self, reason: str = "") -> bool:
        """RECOVERY → STOPPED。"""
        if self._engine is None:
            return False
        return self._engine.recovery_fail(reason)

    def clear_degraded(self, reason: str = "") -> bool:
        """DEGRADED → RUNNING（降级原因消除）。"""
        if self._engine is None:
            return False
        return self._engine.clear_degraded(reason)

    def reset(self, reason: str = "") -> bool:
        """STOPPED → INIT（准备重启）。"""
        if self._engine is None:
            return False
        return self._engine.reset(reason)

    # ------------------------------------------------------------------ #
    #  事件分发
    # ------------------------------------------------------------------ #

    def dispatch_event(
        self,
        event_type: str,
        data:       dict | None = None,
    ) -> None:
        if self._engine is None:
            self.init()
        self._engine.dispatch_event(event_type, data or {})

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    @property
    def production_engine(self) -> ProductionEngine | None:
        return self._engine

    @property
    def state(self) -> TradingState:
        if self._engine is None:
            return TradingState.INIT
        return self._engine.state

    @property
    def health(self) -> SystemHealthState:
        if self._engine is None:
            return SystemHealthState.UNKNOWN
        return self._engine.health

    def get_state_history(self, limit: int = 100) -> list[str]:
        """返回状态转换历史（字符串列表，供 UI 显示）。"""
        if self._engine is None:
            return []
        return self._engine.state_manager.get_history_lines(limit)

    # ------------------------------------------------------------------ #
    #  Recovery 代理（Phase 3）
    # ------------------------------------------------------------------ #

    def save_checkpoint(self) -> str:
        """保存当前系统快照到 Checkpoint 文件。"""
        if self._engine is None:
            return ""
        return self._engine.save_checkpoint()

    def trigger_recovery(
        self,
        trigger: RecoveryTrigger = RecoveryTrigger.MANUAL,
        reason:  str = "",
    ) -> "RecoveryRecord | None":
        """触发一次完整恢复流程（DEGRADED → RECOVERY → RUNNING/STOPPED）。"""
        if self._engine is None:
            return None
        return self._engine.trigger_recovery(trigger, reason)

    def load_latest_checkpoint(self) -> "dict | None":
        """加载最新 Checkpoint 数据字典。"""
        if self._engine is None:
            return None
        return self._engine.load_latest_checkpoint()

    def list_checkpoints(self) -> list:
        """列出所有 Checkpoint 文件元信息。"""
        if self._engine is None:
            return []
        return self._engine.list_checkpoints()

    def get_recovery_records(self, limit: int = 50) -> list:
        """返回历次恢复记录列表。"""
        if self._engine is None:
            return []
        return self._engine.recovery_engine.get_records(limit)

    @property
    def recovery_phase(self) -> "RecoveryPhase":
        """当前恢复阶段。"""
        if self._engine is None:
            return RecoveryPhase.IDLE
        return self._engine.recovery_engine.phase

    def get_recovery_summary(self) -> dict:
        """返回 RecoveryEngine 摘要。"""
        if self._engine is None:
            return {}
        return self._engine.recovery_engine.summary()

    # ------------------------------------------------------------------ #
    #  Failover 代理（Phase 4）
    # ------------------------------------------------------------------ #

    def downgrade(
        self,
        reason:     "FailoverReason" = FailoverReason.MANUAL,
        detail:     str = "",
        force_safe: bool = False,
    ) -> bool:
        """降级一步（FULL→PARTIAL 或 PARTIAL→SAFE_MODE）。"""
        if self._engine is None:
            return False
        return self._engine.downgrade(reason, detail, force_safe)

    def upgrade(
        self,
        reason: "FailoverReason" = FailoverReason.AUTO_RECOVERY,
        detail: str = "",
    ) -> bool:
        """恢复一步（SAFE_MODE→PARTIAL 或 PARTIAL→FULL）。"""
        if self._engine is None:
            return False
        return self._engine.upgrade(reason, detail)

    def upgrade_full(
        self,
        reason: "FailoverReason" = FailoverReason.AUTO_RECOVERY,
        detail: str = "",
    ) -> bool:
        """直接恢复到 FULL 模式。"""
        if self._engine is None:
            return False
        return self._engine.upgrade_full(reason, detail)

    def trigger_risk_takeover(self, detail: str = "") -> bool:
        """触发风控接管（强制 SAFE_MODE + 广播事件）。"""
        if self._engine is None:
            return False
        return self._engine.trigger_risk_takeover(detail)

    def release_risk_takeover(self, detail: str = "") -> bool:
        """解除风控接管，逐步恢复至 FULL。"""
        if self._engine is None:
            return False
        return self._engine.release_risk_takeover(detail)

    def get_failover_records(self, limit: int = 100) -> list:
        if self._engine is None:
            return []
        return self._engine.failover_engine.get_records(limit)

    def get_failover_summary(self) -> dict:
        if self._engine is None:
            return {}
        return self._engine.failover_engine.summary()

    @property
    def failover_mode(self):
        if self._engine is None:
            from .constant import FailoverMode
            return FailoverMode.FULL
        return self._engine.failover_engine.mode

    # ------------------------------------------------------------------ #
    #  OrderSync 代理（Phase 4）
    # ------------------------------------------------------------------ #

    def register_order(self, order_id: str, **kwargs) -> None:
        """注册订单到 OrderSyncEngine。"""
        if self._engine:
            self._engine.register_order(order_id, **kwargs)

    def reconcile_orders(self, exchange_statuses: dict) -> list:
        """执行订单对账，返回不一致记录列表。"""
        if self._engine is None:
            return []
        return self._engine.reconcile_orders(exchange_statuses)

    def batch_reconcile(self, orders: list) -> list:
        """批量对账。"""
        if self._engine is None:
            return []
        return self._engine.batch_reconcile(orders)

    def mark_order_resolved(self, order_id: str) -> bool:
        """标记订单不一致已修复。"""
        if self._engine is None:
            return False
        return self._engine.mark_order_resolved(order_id)

    def get_order_sync_summary(self) -> dict:
        """返回 OrderSyncEngine 摘要。"""
        if self._engine is None:
            return {}
        return self._engine.order_sync_engine.summary()

    def get_mismatches(self, limit: int = 100, unresolved_only: bool = False) -> list:
        """返回订单不一致记录列表。"""
        if self._engine is None:
            return []
        return self._engine.order_sync_engine.get_mismatches(limit, unresolved_only)

    # ------------------------------------------------------------------ #
    #  HealthMonitor 代理（Phase 5）
    # ------------------------------------------------------------------ #

    def record_latency(self, latency_ms: float) -> None:
        """上报网关往返延迟（ms）。"""
        if self._engine:
            self._engine.record_latency(latency_ms)

    def record_order_result(self, success: bool) -> None:
        """上报订单执行结果（True=成功）。"""
        if self._engine:
            self._engine.record_order_result(success)

    def record_data_delay(self, delay_s: float) -> None:
        """上报行情数据延迟（秒）。"""
        if self._engine:
            self._engine.record_data_delay(delay_s)

    def record_heartbeat(self, ok: bool = True) -> None:
        """上报心跳状态。"""
        if self._engine:
            self._engine.record_heartbeat(ok)

    def evaluate_health(self) -> "HealthSnapshot | None":
        """触发一次健康评估，广播 EVENT_HEALTH_UPDATE。"""
        if self._engine is None:
            return None
        return self._engine.evaluate_health()

    def get_health_summary(self) -> dict:
        """返回当前健康指标摘要。"""
        if self._engine is None:
            return {}
        return self._engine.health_monitor.summary()

    def get_health_history(self, limit: int = 120) -> list:
        """返回最近 N 条健康快照列表。"""
        if self._engine is None:
            return []
        return self._engine.health_monitor.get_history(limit)

    def update_health_thresholds(self, **kwargs) -> None:
        """动态更新告警阈值，如 update_health_thresholds(latency_warn_ms=150)。"""
        if self._engine:
            self._engine.health_monitor.update_thresholds(**kwargs)

    def get_summary(self) -> dict:
        if self._engine is None:
            return {"state": "init", "health": "unknown", "uptime": 0}
        return self._engine.get_summary()
