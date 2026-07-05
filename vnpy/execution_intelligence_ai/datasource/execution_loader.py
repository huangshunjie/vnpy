"""
execution_intelligence_ai/datasource/execution_loader.py  (Phase 1 stub)

ExecutionLoader — 成交反馈数据访问封装。
"""
from __future__ import annotations


class ExecutionLoader:
    """成交反馈数据访问。Phase 5+ 实现成交回报/滑点/延迟加载。"""

    def __init__(self, main_engine=None) -> None:
        self._main_engine = main_engine

    def is_available(self) -> bool:
        return self._main_engine is not None

    def get_trades(self, execution_id: str) -> list:
        return []

    def get_slippage(self, execution_id: str) -> float:
        return 0.0
