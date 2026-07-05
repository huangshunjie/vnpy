"""
execution_intelligence_ai/engine/execution_engine.py  (Phase 1 stub)

ExecutionEngine — 执行子引擎骨架（Phase 1 空实现）。
"""
from __future__ import annotations
from typing import Callable


class ExecutionEngine:
    """执行子引擎骨架。Phase 2+ 实现具体执行逻辑。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log = log_fn or (lambda m: None)

    def init(self) -> None:
        self._log("[ExecutionEngine] init()")

    def start(self) -> None:
        self._log("[ExecutionEngine] start()")

    def stop(self) -> None:
        self._log("[ExecutionEngine] stop()")

    def process_order(self, order_data: dict) -> None:
        """接收父订单，启动执行流水线（Phase 2+ 实现）。"""
        pass

    def summary(self) -> dict:
        return {"phase": 1, "status": "stub"}
