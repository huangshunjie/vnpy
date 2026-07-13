"""
cross_market_ai/engine/cross_market_engine.py

Cross-Market Engine 子引擎协调器。
Phase 1: 骨架，仅定义接口。
"""
from __future__ import annotations


class CrossMarketSubEngine:
    """五大子引擎的基类骨架。Phase 2+ 各自实现。"""

    def init(self) -> None:
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
