"""
strategy_lifecycle_ai/engine/registry_engine.py  (Phase 1 Stub)

RegistryEngine — 策略注册中心。
"""

from __future__ import annotations
from datetime import datetime
from typing import Callable
from ..constant import StrategyPhase
from ..model.strategy_model import StrategyState


class RegistryEngine:
    """策略注册中心（Phase 1: 骨架，Phase 2+ 实现）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log      = log_fn or (lambda m: None)
        self._registry: dict[str, StrategyState] = {}

    def register(
        self,
        strategy_id:   str,
        strategy_name: str = "",
        meta:          dict | None = None,
    ) -> StrategyState:
        """注册策略（Phase 1 stub）。"""
        if strategy_id in self._registry:
            return self._registry[strategy_id]
        state = StrategyState(
            strategy_id   = strategy_id,
            strategy_name = strategy_name or strategy_id,
            phase         = StrategyPhase.REGISTERED,
            meta          = meta or {},
        )
        self._registry[strategy_id] = state
        self._log(f"[RegistryEngine] registered: {strategy_id}")
        return state

    def unregister(self, strategy_id: str) -> bool:
        if strategy_id in self._registry:
            del self._registry[strategy_id]
            return True
        return False

    def get(self, strategy_id: str) -> StrategyState | None:
        return self._registry.get(strategy_id)

    def get_all(self) -> list[StrategyState]:
        return list(self._registry.values())

    def get_by_phase(self, phase: StrategyPhase) -> list[StrategyState]:
        return [s for s in self._registry.values() if s.phase == phase]

    def count(self) -> int:
        return len(self._registry)

    def summary(self) -> dict:
        phase_counts: dict[str, int] = {}
        for s in self._registry.values():
            k = s.phase.value
            phase_counts[k] = phase_counts.get(k, 0) + 1
        return {"total": self.count(), "by_phase": phase_counts, "phase": 1}
