"""
strategy_lifecycle_ai/datasource/strategy_loader.py  (Phase 1 Stub)

StrategyLoader — 从 Quant OS 只读策略列表。
"""

from __future__ import annotations
from typing import Any

_QOS_ENGINE_NAME = "QuantOS"


class StrategyLoader:
    """从 Quant OS 读取策略数据（Phase 1: 骨架，Phase 2+ 实现）。"""

    def __init__(self, main_engine: Any = None) -> None:
        self._main_engine = main_engine
        self._qos_engine  = None

    def _get_engine(self):
        if self._qos_engine is not None:
            return self._qos_engine
        if self._main_engine is None:
            return None
        try:
            engine = self._main_engine.get_engine(_QOS_ENGINE_NAME)
            if engine is not None:
                self._qos_engine = engine
            return engine
        except Exception:
            return None

    def is_available(self) -> bool:
        return self._get_engine() is not None

    def get_strategy_ids(self) -> list[str]:
        """获取 Quant OS 中所有策略 ID（Phase 1 stub → 空列表）。"""
        return []

    def get_strategy_meta(self, strategy_id: str) -> dict:
        """获取策略元数据（Phase 1 stub）。"""
        return {}

    def summary(self) -> dict:
        return {"source": "quant_os", "available": self.is_available(), "phase": 1}
