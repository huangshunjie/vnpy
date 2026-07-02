"""
quant_os/engine/os_engine.py

OSEngine — Quant OS 内核（Phase 5 最终版）。

Phase 5 新增：
  - 持有 SystemController（全局控制 + Fail-safe）
  - 代理 start/stop/pause/resume_system
  - 代理 isolate_module / handle_module_error / health_check
"""

from __future__ import annotations

from datetime import datetime

from ..constant import ModuleType, ModuleState, OsState
from ..event import (
    EVENT_OS_START, EVENT_OS_STOP,
    EVENT_LIFECYCLE_CHANGE, EVENT_SYSTEM_LOG,
)
from .module_registry   import ModuleRegistry
from .event_bus         import EventBus
from .lifecycle_manager import LifecycleManager
from .orchestrator      import Orchestrator
from .system_controller import SystemController, SystemHealth
from ..model.lifecycle_model import AlphaState, StrategyState
from ..model.strategy_model  import TriggerType, TriggerRecord, StrategyRecord


class OSEngine:
    """Quant OS 内核（Phase 5 最终版）。"""

    def __init__(self, vnpy_event_put_fn) -> None:
        self._put        = vnpy_event_put_fn
        self._state      = OsState.IDLE
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None

        self.registry          = ModuleRegistry(event_put_fn=self._publish_vnpy)
        self.event_bus         = EventBus(max_history=1000)
        self.lifecycle_manager = LifecycleManager(
            event_publish_fn=self._publish_bus_and_vnpy
        )
        self.orchestrator      = Orchestrator(
            event_publish_fn=self._publish_bus_and_vnpy
        )
        self.system_controller = SystemController(
            registry     = self.registry,
            event_pub_fn = self._publish_bus_and_vnpy,
            log_fn       = self._log,
        )

    # ------------------------------------------------------------------ #
    #  OS 生命周期
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        if self._state == OsState.RUNNING:
            self._log("[WARN] OSEngine 已在运行中。")
            return
        self._state      = OsState.RUNNING
        self._started_at = datetime.now()
        self._log("Quant OS 内核启动。")
        self.event_bus.publish(EVENT_OS_START, {"state": "RUNNING"})
        self._publish_vnpy_raw(EVENT_OS_START, {"state": "RUNNING"})

    def stop(self) -> None:
        if self._state == OsState.STOPPED:
            return
        self._state      = OsState.STOPPED
        self._stopped_at = datetime.now()
        self._log("Quant OS 内核停止。")
        self.event_bus.publish(EVENT_OS_STOP, {"state": "STOPPED"})
        self._publish_vnpy_raw(EVENT_OS_STOP, {"state": "STOPPED"})

    def pause(self) -> None:
        if self._state != OsState.RUNNING:
            return
        self._state = OsState.PAUSED
        self._log("Quant OS 内核暂停。")

    def resume(self) -> None:
        if self._state != OsState.PAUSED:
            return
        self._state = OsState.RUNNING
        self._log("Quant OS 内核恢复运行。")

    @property
    def state(self) -> OsState:
        return self._state

    @property
    def uptime_seconds(self) -> float:
        if self._started_at is None:
            return 0.0
        end = self._stopped_at or datetime.now()
        return (end - self._started_at).total_seconds()

    # ------------------------------------------------------------------ #
    #  模块注册
    # ------------------------------------------------------------------ #

    def register_module(self, name: str, module_type: ModuleType | str, *,
                         description: str = "", version: str = "1.0",
                         tags: list[str] | None = None) -> bool:
        if self.registry.get(name) is not None:
            return False
        self.registry.register(name, module_type, description=description,
                                version=version, tags=tags)
        self._log(f"已注册模块：{name}（{module_type}）")
        return True

    def set_module_state(self, name: str, new_state: ModuleState | str,
                         *, error_msg: str = "") -> bool:
        ok = self.registry.set_state(name, new_state, error_msg=error_msg)
        if ok:
            ns = new_state if isinstance(new_state, str) else new_state.value
            self._log(f"模块状态变更：{name} → {ns}")
        return ok

    def start_module(self,  name: str) -> bool: return self.set_module_state(name, ModuleState.RUNNING)
    def stop_module(self,   name: str) -> bool: return self.set_module_state(name, ModuleState.STOPPED)
    def pause_module(self,  name: str) -> bool: return self.set_module_state(name, ModuleState.PAUSED)
    def resume_module(self, name: str) -> bool: return self.set_module_state(name, ModuleState.RUNNING)
    def mark_error(self, name: str, error_msg: str = "") -> bool:
        return self.set_module_state(name, ModuleState.ERROR, error_msg=error_msg)

    # ------------------------------------------------------------------ #
    #  Alpha 生命周期
    # ------------------------------------------------------------------ #

    def create_alpha(self, factor_name: str, *, alpha_id: str | None = None,
                     validation_score: float = 0.0, notes: str = "",
                     tags: list[str] | None = None) -> str:
        aid = self.lifecycle_manager.create_alpha(
            factor_name, alpha_id=alpha_id,
            validation_score=validation_score, notes=notes, tags=tags)
        self._log(f"Alpha 创建：{factor_name}（id={aid}）")
        return aid

    def advance_alpha(self, alpha_id: str, new_state: AlphaState | str,
                      *, reason: str = "", score: float | None = None) -> bool:
        ok = self.lifecycle_manager.advance_alpha(
            alpha_id, new_state, reason=reason, score=score)
        if ok:
            ns = new_state if isinstance(new_state, str) else new_state.value
            self._log(f"Alpha 状态推进：{alpha_id} → {ns}")
        return ok

    def retire_alpha(self, alpha_id: str, reason: str = "手动退役") -> bool:
        ok = self.lifecycle_manager.retire_alpha(alpha_id, reason)
        if ok:
            self._log(f"Alpha 退役：{alpha_id}")
        return ok

    # ------------------------------------------------------------------ #
    #  Strategy 生命周期
    # ------------------------------------------------------------------ #

    def create_strategy(self, strategy_name: str, *, strategy_id: str | None = None,
                         alpha_id: str = "", backtest_sharpe: float = 0.0,
                         backtest_ic: float = 0.0, notes: str = "",
                         tags: list[str] | None = None) -> str:
        sid = self.lifecycle_manager.create_strategy(
            strategy_name, strategy_id=strategy_id, alpha_id=alpha_id,
            backtest_sharpe=backtest_sharpe, backtest_ic=backtest_ic,
            notes=notes, tags=tags)
        self._log(f"Strategy 创建：{strategy_name}（id={sid}）")
        return sid

    def advance_strategy(self, strategy_id: str, new_state: StrategyState | str,
                         *, reason: str = "", live_sharpe: float | None = None) -> bool:
        ok = self.lifecycle_manager.advance_strategy(
            strategy_id, new_state, reason=reason, live_sharpe=live_sharpe)
        if ok:
            ns = new_state if isinstance(new_state, str) else new_state.value
            self._log(f"Strategy 状态推进：{strategy_id} → {ns}")
        return ok

    def disable_strategy(self, strategy_id: str, reason: str = "手动禁用") -> bool:
        ok = self.lifecycle_manager.disable_strategy(strategy_id, reason)
        if ok:
            self._log(f"Strategy 禁用：{strategy_id}")
        return ok

    # ------------------------------------------------------------------ #
    #  Orchestrator 代理
    # ------------------------------------------------------------------ #

    def add_trigger_rule(self, name: str, trigger_type: TriggerType | str, *,
                          rule_id: str | None = None, source_module: str = "",
                          target_modules: list[str] | None = None,
                          description: str = "", enabled: bool = True) -> str:
        return self.orchestrator.add_rule(
            name, trigger_type, rule_id=rule_id, source_module=source_module,
            target_modules=target_modules, description=description, enabled=enabled)

    def trigger(self, rule_id: str, *, strategy_id: str | None = None,
                payload: dict | None = None) -> TriggerRecord | None:
        return self.orchestrator.trigger(rule_id, strategy_id=strategy_id, payload=payload)

    def trigger_by_type(self, trigger_type: TriggerType | str, *,
                         strategy_id: str | None = None,
                         payload: dict | None = None) -> list[TriggerRecord]:
        return self.orchestrator.trigger_by_type(
            trigger_type, strategy_id=strategy_id, payload=payload)

    def register_strategy_to_orchestrator(self, strategy_id: str, strategy_name: str,
                                           alpha_id: str = "") -> StrategyRecord:
        return self.orchestrator.register_strategy(
            strategy_id, strategy_name, alpha_id=alpha_id)

    def schedule_strategy(self, strategy_id: str) -> bool:
        return self.orchestrator.schedule_strategy(strategy_id)

    def unschedule_strategy(self, strategy_id: str) -> bool:
        return self.orchestrator.unschedule_strategy(strategy_id)

    # ------------------------------------------------------------------ #
    #  SystemController 代理（Phase 5）
    # ------------------------------------------------------------------ #

    def start_system(self) -> bool:
        return self.system_controller.start_system()

    def stop_system(self) -> bool:
        return self.system_controller.stop_system()

    def pause_system(self) -> bool:
        return self.system_controller.pause_system()

    def resume_system(self) -> bool:
        return self.system_controller.resume_system()

    def isolate_module(self, name: str, reason: str = "") -> bool:
        return self.system_controller.isolate_module(name, reason)

    def handle_module_error(self, name: str, error_msg: str = "") -> None:
        self.system_controller.handle_module_error(name, error_msg)

    def health_check(self) -> SystemHealth:
        return self.system_controller.health_check()

    @property
    def system_health(self) -> SystemHealth:
        return self.system_controller.health

    # ------------------------------------------------------------------ #
    #  EventBus 代理
    # ------------------------------------------------------------------ #

    def subscribe(self, event_type: str, callback) -> None:
        self.event_bus.subscribe(event_type, callback)

    def unsubscribe(self, event_type: str, callback) -> None:
        self.event_bus.unsubscribe(event_type, callback)

    def dispatch(self, event_type: str, data: dict | None = None) -> None:
        self.event_bus.publish(event_type, data or {})
        self._publish_vnpy_raw(event_type, data or {})

    # ------------------------------------------------------------------ #
    #  汇总查询
    # ------------------------------------------------------------------ #

    def get_summary(self) -> dict:
        return {
            "os_state":        self._state.value,
            "uptime":          round(self.uptime_seconds, 1),
            "system_health":   self.system_controller.health.value,
            "modules":         self.registry.summary(),
            "lifecycle":       self.lifecycle_manager.summary(),
            "orchestrator":    self.orchestrator.summary(),
            "controller":      self.system_controller.summary(),
            "event_stats":     self.event_bus.get_stats(),
        }

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    def _log(self, msg: str) -> None:
        self.event_bus.publish(EVENT_SYSTEM_LOG, {"message": msg})
        self._publish_vnpy_raw(EVENT_SYSTEM_LOG, {"message": msg})

    def _publish_vnpy(self, event) -> None:
        self._put(event)

    def _publish_vnpy_raw(self, event_type: str, data: dict) -> None:
        from vnpy.event import Event
        e = Event(event_type)
        e.data = data
        self._put(e)

    def _publish_bus_and_vnpy(self, event_type: str, data: dict) -> None:
        self.event_bus.publish(event_type, data)
        self._publish_vnpy_raw(event_type, data)
