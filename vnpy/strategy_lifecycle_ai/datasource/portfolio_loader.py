"""
strategy_lifecycle_ai/datasource/portfolio_loader.py  (Phase 1 Stub)

PortfolioLoader — 从 Capital Allocation AI 只读资本分配比例。
"""

from __future__ import annotations
from typing import Any

_CAI_ENGINE_NAME = "CapitalAllocationAI"


class PortfolioLoader:
    """从 Capital Allocation AI 读取分配数据（Phase 1: 骨架，Phase 2+ 实现）。"""

    def __init__(self, main_engine: Any = None) -> None:
        self._main_engine = main_engine
        self._cai_engine  = None

    def _get_engine(self):
        if self._cai_engine is not None:
            return self._cai_engine
        if self._main_engine is None:
            return None
        try:
            engine = self._main_engine.get_engine(_CAI_ENGINE_NAME)
            if engine is not None:
                self._cai_engine = engine
            return engine
        except Exception:
            return None

    def is_available(self) -> bool:
        return self._get_engine() is not None

    def get_capital_ratio(self, strategy_id: str) -> float:
        """获取策略资本分配比例（Phase 1 stub → 0.0）。"""
        return 0.0

    def get_all_ratios(self) -> dict[str, float]:
        """获取全部策略资本比例（Phase 1 stub → 空字典）。"""
        return {}

    def summary(self) -> dict:
        return {"source": "capital_allocation_ai", "available": self.is_available(), "phase": 1}
