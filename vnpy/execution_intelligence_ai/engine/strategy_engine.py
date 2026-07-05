"""
execution_intelligence_ai/engine/strategy_engine.py  (Phase 1 stub)

StrategyEngine — 执行策略选择引擎骨架。
"""
from __future__ import annotations
from typing import Callable
from ..constant import ExecutionStrategy


class StrategyEngine:
    """执行策略选择引擎。Phase 2+ 实现 TWAP/VWAP/POV/Adaptive 选择逻辑。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log = log_fn or (lambda m: None)

    def init(self) -> None:
        self._log("[StrategyEngine] init()")

    def start(self) -> None:
        self._log("[StrategyEngine] start()")

    def stop(self) -> None:
        self._log("[StrategyEngine] stop()")

    def select_strategy(self, order_data: dict) -> ExecutionStrategy:
        """根据订单特征选择执行策略（Phase 2+ 实现）。"""
        return ExecutionStrategy.TWAP

    def summary(self) -> dict:
        return {"phase": 1, "status": "stub"}
