"""
execution_intelligence_ai/datasource/market_loader.py  (Phase 1 stub)

MarketLoader — 行情数据访问封装（只使用 VeighNa 内部数据）。
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vnpy.trader.engine import MainEngine


class MarketLoader:
    """行情数据访问。Phase 2+ 实现盘口/成交量/波动率加载。"""

    def __init__(self, main_engine=None) -> None:
        self._main_engine = main_engine

    def is_available(self) -> bool:
        return self._main_engine is not None

    def get_tick(self, vt_symbol: str) -> dict | None:
        """获取最新 tick 数据（Phase 2+ 实现）。"""
        return None

    def get_bar_history(self, vt_symbol: str, count: int = 60) -> list:
        """获取历史 K 线（Phase 2+ 实现）。"""
        return []

    def get_volatility(self, vt_symbol: str, window: int = 20) -> float:
        """获取近期波动率（Phase 3+ 实现）。"""
        return 0.0
