"""
cross_market_ai/datasource/execution_loader.py

只读接口 — 从 Execution Intelligence 加载执行数据。
Phase 1: 骨架。Phase 3+ 实现。
"""
from __future__ import annotations


class ExecutionDataLoader:
    """
    从 Execution Intelligence Layer 读取执行成本、滑点、冲击数据。
    只读，不修改任何执行逻辑。
    """

    def load_execution_costs(self, market_id: str) -> dict:
        """Phase 3 实现。"""
        return {"market_id": market_id, "costs": None, "status": "stub"}

    def load_slippage_profile(self, market_id: str) -> dict:
        """Phase 3 实现。"""
        return {"market_id": market_id, "slippage": None, "status": "stub"}

    def load_fill_rate(self, market_id: str) -> dict:
        """Phase 3 实现。"""
        return {"market_id": market_id, "fill_rate": None, "status": "stub"}
