"""
strategy_lifecycle_ai/engine/lifecycle_engine.py  (Phase 1 Stub)

LifecycleEngine — 策略生命周期主调度引擎。
"""

from __future__ import annotations
from datetime import datetime
from typing import Callable
from ..constant import StrategyPhase
from ..model.strategy_model import StrategyState


class LifecycleEngine:
    """策略生命周期主调度引擎（Phase 1: 骨架，Phase 2+ 实现）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log      = log_fn or (lambda m: None)
        self._bar      = 0
        self._strategies: dict[str, StrategyState] = {}

    def init(self) -> None:
        self._log("[LifecycleEngine] init()")

    def start(self) -> None:
        self._log("[LifecycleEngine] start()")

    def stop(self) -> None:
        self._log("[LifecycleEngine] stop()")

    def update_strategy_state(
        self,
        strategy_id: str,
        **kwargs,
    ) -> StrategyState:
        """更新策略状态（Phase 1: stub）。"""
        if strategy_id not in self._strategies:
            self._strategies[strategy_id] = StrategyState(
                strategy_id=strategy_id)
        state = self._strategies[strategy_id]
        for k, v in kwargs.items():
            if hasattr(state, k):
                setattr(state, k, v)
        state.updated_at = datetime.now()
        return state

    def get_state(self, strategy_id: str) -> StrategyState | None:
        return self._strategies.get(strategy_id)

    def get_all_states(self) -> list[StrategyState]:
        return list(self._strategies.values())

    def summary(self) -> dict:
        return {
            "strategy_count": len(self._strategies),
            "phase":          1,
        }
