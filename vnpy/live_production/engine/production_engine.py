"""
live_production/engine/production_engine.py

ProductionEngine — Live Production System 内核（Phase 2）。

Phase 2 新增：
  - 持有 TradingStateManager 实例
  - 代理 start / stop / mark_degraded / start_recovery / recovery_success 等
  - update_state 经由 StateManager 校验合法性后广播

❌ 禁止任何交易 / 下单逻辑
"""

from __future__ import annotations

from datetime import datetime

from ..constant import TradingState, SystemHealthState, APP_NAME
from ..event import (
    EVENT_PROD_START,
    EVENT_PROD_STOP,
    EVENT_STATE_CHANGE,
    EVENT_HEALTH_UPDATE,
)
from ..model.system_state_model import TradingStateRecord
from ..model.health_model import HealthSnapshot
from .recovery_engine import RecoveryEngine, RecoveryTrigger
from .failover_engine import FailoverEngine, FailoverReason
from .health_monitor import HealthMonitor, HealthThresholds
from .order_sync_engine import OrderSyncEngine
from .state_manager import (
    TradingStateManager,
    TRIGGER_MANUAL,
    TRIGGER_EXECUTION_ERROR,
    TRIGGER_RISK_ALERT,
    TRIGGER_RECOVERY_SUCCESS,
    TRIGGER_RECOVERY_FAIL,
    TRIGGER_DEGRADED_CLEAR,
    TRIGGER_MODULE_ERROR,
)


class ProductionEngine:
    """
    Live Production System 内核（Phase 2）。

    子引擎：
      - state_manager    : TradingStateManager   ✅ Phase 2
      - failover_engine  : FailoverEngine         ⬜ Phase 4
      - recovery_engine  : RecoveryEngine         ⬜ Phase 3
      - order_sync_engine: OrderSyncEngine        ⬜ Phase 4
      - health_monitor   : HealthMonitor          ⬜ Phase 5
    """

    def __init__(self, event_put_fn) -> None:
        self._put        = event_put_fn
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None

        self._state_record    = TradingStateRecord()
        self._health_snapshot = HealthSnapshot()

        # Phase 2: StateManager
        self.state_manager = TradingStateManager(
            event_publish_fn = self._publish_bus,
            log_fn           = self._log,
        )

        # Phase 3: RecoveryEngine
        self.recovery_engine = RecoveryEngine(
            event_publish_fn = self._publish_bus,
            log_fn           = self._log,
            state_manager    = self.state_manager,
        )

        # Phase 4: FailoverEngine + OrderSyncEngine
        self.failover_engine = FailoverEngine(
            event_publish_fn = self._publish_bus,
            log_fn           = self._log,
            state_manager    = self.state_manager,
        )
        self.order_sync_engine = OrderSyncEngine(
            event_publish_fn = self._publish_bus,
            log_fn           = self._log,
        )

        # Phase 5: HealthMonitor
        self.health_monitor = HealthMonitor(
            event_publish_fn = self._publish_bus,
            log_fn           = self._log,
        )

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        """初始化内核。"""
        self._log("ProductionEngine 初始化完成。")

    def start(self) -> None:
        """启动系统：INIT → RUNNING。"""
        if self.state_manager.is_running:
            self._log("[WARN] ProductionEngine 已在运行中。")
            return
        self._started_at = datetime.now()
        ok = self.state_manager.start()
        if ok:
            self._state_record.update(TradingState.RUNNING)
            self._publish_raw(EVENT_PROD_START, {"state": TradingState.RUNNING.value})
            self._log("Live Production System 已启动。")

    def stop(self, reason: str = "") -> None:
        """停止系统（强制，任意状态均可）。"""
        if self.state_manager.is_stopped:
            return
        self._stopped_at = datetime.now()
        self.state_manager.stop(reason or "系统停止")
        self._state_record.update(TradingState.STOPPED, reason)
        self._publish_raw(EVENT_PROD_STOP, {"state": TradingState.STOPPED.value})
        self._log(f"Live Production System 已停止。{('  原因: ' + reason) if reason else ''}")

    # ------------------------------------------------------------------ #
    #  状态转换代理（Phase 2）
    # ------------------------------------------------------------------ #

    def update_state(self, new_state: TradingState, reason: str = "") -> None:
        """
        通用状态更新（经 StateManager 合法性校验）。
        广播 EVENT_STATE_CHANGE 由 StateManager 内部完成。
        """
        ok = self.state_manager.transition_to(
            new_state, trigger=TRIGGER_MANUAL, reason=reason
        )
        if ok:
            self._state_record.update(new_state, reason)

    def mark_degraded(self, reason: str = "", trigger: str = TRIGGER_MODULE_ERROR) -> bool:
        """RUNNING → DEGRADED。外部模块异常时调用。"""
        ok = self.state_manager.mark_degraded(reason, trigger)
        if ok:
            self._state_record.update(TradingState.DEGRADED, reason)
        return ok

    def start_recovery(self, reason: str = "") -> bool:
        """DEGRADED → RECOVERY。"""
        ok = self.state_manager.start_recovery(reason)
        if ok:
            self._state_record.update(TradingState.RECOVERY, reason)
        return ok

    def recovery_success(self, reason: str = "") -> bool:
        """RECOVERY → RUNNING。"""
        ok = self.state_manager.recovery_success(reason)
        if ok:
            self._state_record.update(TradingState.RUNNING, reason)
        return ok

    def recovery_fail(self, reason: str = "") -> bool:
        """RECOVERY → STOPPED。"""
        ok = self.state_manager.recovery_fail(reason)
        if ok:
            self._state_record.update(TradingState.STOPPED, reason)
        return ok

    def clear_degraded(self, reason: str = "") -> bool:
        """DEGRADED → RUNNING（降级原因消除）。"""
        ok = self.state_manager.clear_degraded(reason)
        if ok:
            self._state_record.update(TradingState.RUNNING, reason)
        return ok

    def reset(self, reason: str = "") -> bool:
        """STOPPED → INIT（准备重启）。"""
        ok = self.state_manager.reset(reason)
        if ok:
            self._state_record.update(TradingState.INIT, reason)
            self._started_at = None
            self._stopped_at = None
        return ok

    # ------------------------------------------------------------------ #
    #  Recovery 代理（Phase 3）
    # ------------------------------------------------------------------ #

    def save_checkpoint(self) -> str:
        """保存当前系统快照到 Checkpoint。"""
        snapshot = self.get_summary()
        return self.recovery_engine.save_checkpoint(snapshot)

    def trigger_recovery(
        self,
        trigger: RecoveryTrigger = RecoveryTrigger.MANUAL,
        reason:  str = "",
    ):
        """触发一次完整恢复流程。"""
        return self.recovery_engine.trigger_recovery(trigger, reason)

    def load_latest_checkpoint(self):
        """加载最新 Checkpoint 数据。"""
        return self.recovery_engine.load_latest()

    def list_checkpoints(self) -> list:
        """列出所有 Checkpoint 文件元信息。"""
        return self.recovery_engine.list_checkpoints()

    # ------------------------------------------------------------------ #
    #  Failover 代理（Phase 4）
    # ------------------------------------------------------------------ #

    def downgrade(self, reason: FailoverReason = FailoverReason.MANUAL,
                  detail: str = "", force_safe: bool = False) -> bool:
        return self.failover_engine.downgrade(reason, detail, force_safe)

    def upgrade(self, reason: FailoverReason = FailoverReason.AUTO_RECOVERY,
                detail: str = "") -> bool:
        return self.failover_engine.upgrade(reason, detail)

    def upgrade_full(self, reason: FailoverReason = FailoverReason.AUTO_RECOVERY,
                     detail: str = "") -> bool:
        return self.failover_engine.upgrade_full(reason, detail)

    def trigger_risk_takeover(self, detail: str = "") -> bool:
        return self.failover_engine.trigger_risk_takeover(detail)

    def release_risk_takeover(self, detail: str = "") -> bool:
        return self.failover_engine.release_risk_takeover(detail)

    # ------------------------------------------------------------------ #
    #  OrderSync 代理（Phase 4）
    # ------------------------------------------------------------------ #

    def register_order(self, order_id: str, **kwargs) -> None:
        self.order_sync_engine.register_order(order_id, **kwargs)

    def reconcile_orders(self, exchange_statuses: dict) -> list:
        return self.order_sync_engine.reconcile(exchange_statuses)

    def batch_reconcile(self, orders: list) -> list:
        return self.order_sync_engine.batch_reconcile(orders)

    def mark_order_resolved(self, order_id: str) -> bool:
        return self.order_sync_engine.mark_resolved(order_id)

    # ------------------------------------------------------------------ #
    #  HealthMonitor 代理（Phase 5）
    # ------------------------------------------------------------------ #

    def record_latency(self, latency_ms: float) -> None:
        self.health_monitor.record_latency(latency_ms)

    def record_order_result(self, success: bool) -> None:
        self.health_monitor.record_order_result(success)

    def record_data_delay(self, delay_s: float) -> None:
        self.health_monitor.record_data_delay(delay_s)

    def record_heartbeat(self, ok: bool = True) -> None:
        self.health_monitor.record_heartbeat(ok)

    def evaluate_health(self):
        """触发一次健康评估并广播 EVENT_HEALTH_UPDATE。"""
        snap = self.health_monitor.evaluate()
        self._health_snapshot.health_state = snap.health_state
        return snap

    # ------------------------------------------------------------------ #
    #  事件分发
    # ------------------------------------------------------------------ #

    def dispatch_event(self, event_type: str, data: dict | None = None) -> None:
        self._publish_raw(event_type, data or {})

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    @property
    def state(self) -> TradingState:
        return self.state_manager.state

    @property
    def health(self) -> SystemHealthState:
        return self.health_monitor.state

    @property
    def uptime_seconds(self) -> float:
        if self._started_at is None:
            return 0.0
        end = self._stopped_at or datetime.now()
        return (end - self._started_at).total_seconds()

    def get_summary(self) -> dict:
        sm = self.state_manager.summary()
        rm = self.recovery_engine.summary()
        fm = self.failover_engine.summary()
        om = self.order_sync_engine.summary()
        hm = self.health_monitor.summary()
        return {
            "state":           self.state.value,
            "health":          self.health.value,
            "uptime":          round(self.uptime_seconds, 1),
            "failover_mode":   fm["mode"],
            "state_manager":   sm,
            "recovery_engine": rm,
            "failover_engine": fm,
            "order_sync":      om,
            "health_monitor":  hm,
            "transitions":     sm["transitions"],
        }

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    def _publish_bus(self, event_type: str, data: dict) -> None:
        """EventBus 内部发布（StateManager 回调）。"""
        self._publish_raw(event_type, data)

    def _publish_raw(self, event_type: str, data: dict) -> None:
        from vnpy.event import Event
        e      = Event(event_type)
        e.data = data
        self._put(e)

    def _log(self, msg: str) -> None:
        self._publish_raw("eLiveProd.log", {"message": msg})
