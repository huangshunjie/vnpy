"""
execution_intelligence_ai/datasource/order_loader.py  (Phase 1 stub)

OrderLoader — 订单数据访问封装。
"""
from __future__ import annotations


class OrderLoader:
    """订单数据访问。Phase 2+ 实现父订单/子订单状态查询。"""

    def __init__(self, main_engine=None) -> None:
        self._main_engine = main_engine

    def is_available(self) -> bool:
        return self._main_engine is not None

    def get_active_orders(self) -> list:
        return []

    def get_order(self, order_id: str) -> dict | None:
        return None
