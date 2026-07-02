"""
strategy_lifecycle_ai/datasource/performance_loader.py  (Phase 1 Stub)

PerformanceLoader — 从 Portfolio Engine 只读绩效数据。
"""

from __future__ import annotations
from typing import Any

_PORTFOLIO_ENGINE_NAME = "PortfolioStrategy"


class PerformanceLoader:
    """从 Portfolio Engine 读取绩效数据（Phase 1: 骨架，Phase 2+ 实现）。"""

    def __init__(self, main_engine: Any = None) -> None:
        self._main_engine    = main_engine
        self._portfolio_engine = None

    def _get_engine(self):
        if self._portfolio_engine is not None:
            return self._portfolio_engine
        if self._main_engine is None:
            return None
        try:
            engine = self._main_engine.get_engine(_PORTFOLIO_ENGINE_NAME)
            if engine is not None:
                self._portfolio_engine = engine
            return engine
        except Exception:
            return None

    def is_available(self) -> bool:
        return self._get_engine() is not None

    def get_pnl_series(self, strategy_id: str) -> list[float]:
        """获取策略 PnL 序列（Phase 1 stub → 空列表）。"""
        return []

    def get_trade_count(self, strategy_id: str) -> int:
        """获取策略交易次数（Phase 1 stub → 0）。"""
        return 0

    def summary(self) -> dict:
        return {"source": "portfolio_engine", "available": self.is_available(), "phase": 1}
