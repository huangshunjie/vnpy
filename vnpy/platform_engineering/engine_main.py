"""
platform_engineering/engine.py
PlatformEngine — 主引擎，协调所有子引擎。
Phase 1 Stub：持有子引擎，注册事件，提供 stats。
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vnpy.event import EventEngine

from .engine.observability_engine import ObservabilityEngine
from .engine.task_engine          import TaskEngine
from .engine.deployment_engine    import DeploymentEngine
from .engine.health_engine        import HealthEngine
from .engine.config_engine        import ConfigEngine
from .engine.api_engine           import ApiEngine
from .engine.security_engine      import SecurityEngine
from .event import (
    EVENT_PE_ENGINE_STARTED,
    EVENT_PE_ENGINE_STOPPED,
    EVENT_PE_LOG,
)


class PlatformEngine:
    engine_name: str = "PlatformEngine"

    def __init__(self, main_engine, event_engine: "EventEngine") -> None:
        self.main_engine   = main_engine
        self.event_engine  = event_engine

        # sub-engines
        self.observability = ObservabilityEngine()
        self.tasks         = TaskEngine()
        self.deployment    = DeploymentEngine()
        self.health        = HealthEngine()
        self.config        = ConfigEngine()
        self.api           = ApiEngine()
        self.security      = SecurityEngine()

        self._started = False

    # ── lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        if self._started:
            return
        for eng in self._sub_engines():
            eng.start()
        self._started = True
        self._emit(EVENT_PE_ENGINE_STARTED, {"engine": self.engine_name})
        self._log("PlatformEngine started")

    def stop(self) -> None:
        if not self._started:
            return
        for eng in reversed(self._sub_engines()):
            eng.stop()
        self._started = False
        self._emit(EVENT_PE_ENGINE_STOPPED, {"engine": self.engine_name})

    def close(self) -> None:
        self.stop()

    # ── aggregate stats ───────────────────────────────────────────

    def get_platform_stats(self) -> dict:
        return {
            "observability": self.observability.stats(),
            "tasks":         self.tasks.stats(),
            "deployment":    self.deployment.stats(),
            "health":        self.health.stats(),
            "config":        self.config.stats(),
            "api":           self.api.stats(),
            "security":      self.security.stats(),
        }

    # ── helpers ───────────────────────────────────────────────────

    def _sub_engines(self):
        return [
            self.observability, self.tasks, self.deployment,
            self.health, self.config, self.api, self.security,
        ]

    def _emit(self, event_type: str, data: dict = None) -> None:
        try:
            from vnpy.event import Event
            self.event_engine.put(Event(event_type, data or {}))
        except Exception:
            pass

    def _log(self, msg: str) -> None:
        self._emit(EVENT_PE_LOG, {"msg": msg})
