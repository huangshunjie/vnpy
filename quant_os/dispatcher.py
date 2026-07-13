"""
quant_os/dispatcher.py

QuantOSEngine — Quant OS 顶层引擎（Phase 5 最终版）。

Phase 5 新增：
  - 暴露 SystemController 接口
  - start/stop/pause/resume_system
  - isolate_module / handle_module_error / health_check
"""

from __future__ import annotations

from vnpy.event import EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import OsState, ModuleType, ModuleState, APP_NAME
from .event import EVENT_SYSTEM_LOG
from .engine.os_engine import OSEngine
from .engine.system_controller import SystemHealth
from .model.lifecycle_model import AlphaState, StrategyState
from .model.strategy_model  import TriggerType, TriggerRecord, StrategyRecord


class QuantOSEngine(BaseEngine):
    """Quant OS 顶层引擎（Phase 5 最终版）。"""

    def __init__(
        self,
        main_engine:  MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._os_engine: OSEngine | None = None

    # ------------------------------------------------------------------ #
    #  OS 生命周期
    # ------------------------------------------------------------------ #

    def init(self) -> None:
        if self._os_engine is None:
            self._os_engine = OSEngine(vnpy_event_put_fn=self.event_engine.put)
        self._log("Quant OS 内核初始化完成。")

    def start(self) -> None:
        if self._os_engine is None:
            self.init()
        self._os_engine.start()

    def stop(self) -> None:
        if self._os_engine is None:
            return
        self._os_engine.stop()

    # ------------------------------------------------------------------ #
    #  模块注册
    # ------------------------------------------------------------------ #

    def register_module(self, module_name: str,
                         module_type: str | ModuleType = "factor", *,
                         description: str = "", version: str = "1.0",
                         tags: list[str] | None = None) -> bool:
        if self._os_engine is None:
            self.init()
        return self._os_engine.register_module(
            module_name, module_type,
            description=description, version=version, tags=tags)

    def set_module_state(self, module_name: str,
                          new_state: str | ModuleState, *,
                          error_msg: str = "") -> bool:
        if self._os_engine is None:
            return False
        return self._os_engine.set_module_state(
            module_name, new_state, error_msg=error_msg)

    # ------------------------------------------------------------------ #
    #  Alpha 生命周期
    # ------------------------------------------------------------------ #

    def create_alpha(self, factor_name: str, *, alpha_id: str | None = None,
                     validation_score: float = 0.0, notes: str = "",
                     tags: list[str] | None = None) -> str:
        if self._os_engine is None:
            self.init()
        return self._os_engine.create_alpha(
            factor_name, alpha_id=alpha_id,
            validation_score=validation_score, notes=notes, tags=tags)

    def advance_alpha(self, alpha_id: str, new_state: str | AlphaState,
                      *, reason: str = "", score: float | None = None) -> bool:
        if self._os_engine is None:
            return False
        return self._os_engine.advance_alpha(
            alpha_id, new_state, reason=reason, score=score)

    def retire_alpha(self, alpha_id: str, reason: str = "手动退役") -> bool:
        if self._os_engine is None:
            return False
        return self._os_engine.retire_alpha(alpha_id, reason)

    # ------------------------------------------------------------------ #
    #  Strategy 生命周期
    # ------------------------------------------------------------------ #

    def create_strategy(self, strategy_name: str, *,
                         strategy_id: str | None = None, alpha_id: str = "",
                         backtest_sharpe: float = 0.0, backtest_ic: float = 0.0,
                         notes: str = "", tags: list[str] | None = None) -> str:
        if self._os_engine is None:
            self.init()
        return self._os_engine.create_strategy(
            strategy_name, strategy_id=strategy_id, alpha_id=alpha_id,
            backtest_sharpe=backtest_sharpe, backtest_ic=backtest_ic,
            notes=notes, tags=tags)

    def advance_strategy(self, strategy_id: str,
                          new_state: str | StrategyState, *,
                          reason: str = "",
                          live_sharpe: float | None = None) -> bool:
        if self._os_engine is None:
            return False
        return self._os_engine.advance_strategy(
            strategy_id, new_state, reason=reason, live_sharpe=live_sharpe)

    def disable_strategy(self, strategy_id: str,
                          reason: str = "手动禁用") -> bool:
        if self._os_engine is None:
            return False
        return self._os_engine.disable_strategy(strategy_id, reason)

    # ------------------------------------------------------------------ #
    #  Orchestrator
    # ------------------------------------------------------------------ #

    def add_trigger_rule(self, name: str, trigger_type: str | TriggerType, *,
                          rule_id: str | None = None, source_module: str = "",
                          target_modules: list[str] | None = None,
                          description: str = "", enabled: bool = True) -> str:
        if self._os_engine is None:
            self.init()
        return self._os_engine.add_trigger_rule(
            name, trigger_type, rule_id=rule_id, source_module=source_module,
            target_modules=target_modules, description=description, enabled=enabled)

    def trigger(self, rule_id: str, *, strategy_id: str | None = None,
                payload: dict | None = None) -> TriggerRecord | None:
        if self._os_engine is None:
            return None
        return self._os_engine.trigger(rule_id, strategy_id=strategy_id, payload=payload)

    def trigger_by_type(self, trigger_type: str | TriggerType, *,
                         strategy_id: str | None = None,
                         payload: dict | None = None) -> list[TriggerRecord]:
        if self._os_engine is None:
            return []
        return self._os_engine.trigger_by_type(
            trigger_type, strategy_id=strategy_id, payload=payload)

    def register_strategy_to_orchestrator(self, strategy_id: str,
                                           strategy_name: str,
                                           alpha_id: str = "") -> StrategyRecord | None:
        if self._os_engine is None:
            return None
        return self._os_engine.register_strategy_to_orchestrator(
            strategy_id, strategy_name, alpha_id=alpha_id)

    def schedule_strategy(self, strategy_id: str) -> bool:
        if self._os_engine is None:
            return False
        return self._os_engine.schedule_strategy(strategy_id)

    def unschedule_strategy(self, strategy_id: str) -> bool:
        if self._os_engine is None:
            return False
        return self._os_engine.unschedule_strategy(strategy_id)

    # ------------------------------------------------------------------ #
    #  SystemController（Phase 5）
    # ------------------------------------------------------------------ #

    def start_system(self) -> bool:
        if self._os_engine is None:
            self.init()
        return self._os_engine.start_system()

    def stop_system(self) -> bool:
        if self._os_engine is None:
            return False
        return self._os_engine.stop_system()

    def pause_system(self) -> bool:
        if self._os_engine is None:
            return False
        return self._os_engine.pause_system()

    def resume_system(self) -> bool:
        if self._os_engine is None:
            return False
        return self._os_engine.resume_system()

    def isolate_module(self, module_name: str, reason: str = "") -> bool:
        if self._os_engine is None:
            return False
        return self._os_engine.isolate_module(module_name, reason)

    def handle_module_error(self, module_name: str, error_msg: str = "") -> None:
        if self._os_engine is None:
            return
        self._os_engine.handle_module_error(module_name, error_msg)

    def health_check(self) -> SystemHealth:
        if self._os_engine is None:
            return SystemHealth.STOPPED
        return self._os_engine.health_check()

    @property
    def system_health(self) -> SystemHealth:
        if self._os_engine is None:
            return SystemHealth.STOPPED
        return self._os_engine.system_health

    # ------------------------------------------------------------------ #
    #  事件分发
    # ------------------------------------------------------------------ #

    def dispatch_event(self, event_type: str, data: dict | None = None) -> None:
        if self._os_engine is None:
            self.init()
        self._os_engine.dispatch(event_type, data or {})

    # ------------------------------------------------------------------ #
    #  只读属性
    # ------------------------------------------------------------------ #

    @property
    def os_engine(self) -> OSEngine | None:
        return self._os_engine

    @property
    def state(self) -> OsState:
        if self._os_engine is None:
            return OsState.IDLE
        return self._os_engine.state

    @property
    def registered_modules(self) -> dict[str, dict]:
        if self._os_engine is None:
            return {}
        return {m.name: m.to_dict()
                for m in self._os_engine.registry.get_all()}

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    def _log(self, msg: str) -> None:
        write = getattr(self, "write_log", None)
        if callable(write):
            write(msg)
        from vnpy.event import Event
        e = Event(EVENT_SYSTEM_LOG)
        e.data = {"message": msg}
        self.event_engine.put(e)
