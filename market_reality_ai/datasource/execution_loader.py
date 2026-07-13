"""
market_reality_ai/datasource/execution_loader.py

Phase 1: Stub — 只读接口，从 ExecutionIntelligenceAI 拉取执行数据。
❌ 禁止写入或修改 ExecutionIntelligenceAI。
"""
from __future__ import annotations
from datetime import datetime


class ExecutionLoader:
    """
    历史执行数据加载器 (只读)。

    Phase 2+: 从 ExecutionIntelligenceAI 读取历史成交记录，
              用于 ExecutionSimulator 参数校准。
    """

    def __init__(self, main_engine=None) -> None:
        self._main_engine = main_engine

    def load_trades(self, symbol: str, start: datetime,
                     end: datetime) -> list:
        """Phase 2+: 加载历史成交记录。只读。"""
        return []   # stub

    def load_order_history(self, start: datetime,
                            end: datetime) -> list:
        """Phase 2+: 加载历史订单记录（含rejection）。"""
        return []   # stub

    def get_execution_stats(self, symbol: str) -> dict:
        """Phase 2+: 获取历史执行统计（平均滑点、成交率等）。"""
        return {}   # stub
