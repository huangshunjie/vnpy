"""
market_reality_ai/datasource/market_loader.py

Phase 1: Stub — 只读接口，从 DIL / HistoricalData 拉取市场数据。
❌ 禁止写入任何现有模块。
"""
from __future__ import annotations
from datetime import datetime


class MarketLoader:
    """
    历史市场数据加载器 (只读)。

    Phase 2+: 从 DataIntelligenceAI / vnpy DataManager 拉取
              OHLCV / tick / depth 数据，供仿真引擎使用。
    """

    def __init__(self, main_engine=None) -> None:
        self._main_engine = main_engine

    def load_bars(self, symbol: str, start: datetime,
                   end: datetime, interval: str = "1d") -> list:
        """Phase 2+: 加载历史K线数据。只读，不修改任何状态。"""
        return []   # stub

    def load_ticks(self, symbol: str, start: datetime,
                    end: datetime) -> list:
        """Phase 3+: 加载历史Tick数据。"""
        return []   # stub

    def load_depth(self, symbol: str, timestamp: datetime) -> dict:
        """Phase 3+: 加载历史盘口深度快照。"""
        return {}   # stub

    def get_available_symbols(self) -> list[str]:
        """Phase 2+: 返回可用合约列表。"""
        return []   # stub
