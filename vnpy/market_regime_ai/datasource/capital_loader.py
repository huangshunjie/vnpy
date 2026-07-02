"""
market_regime_ai/datasource/capital_loader.py  (Phase 5)

CapitalLoader — 从 Capital Allocation AI 只读取数据。

Phase 5 实现：
  - 读取当前资本分配比例
  - 读取风险快照
  - 读取 Alpha 评分排名
  - 向 Capital Allocation AI 输出 regime_weight_modifier

❌ 只读 Capital Allocation AI 状态，不修改其策略或分配逻辑
✔  通过 MainEngine.get_engine() 获取引擎引用
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_CAI_ENGINE_NAME = "CapitalAllocationAI"


class CapitalLoader:
    """
    从 Capital Allocation AI 读取数据（Phase 5 完整实现）。

    通过 MainEngine 获取 CapitalAllocationEngine 引用，
    仅调用只读方法，不触发任何写操作。
    """

    def __init__(
        self,
        main_engine: Any = None,
        engine_name: str = _CAI_ENGINE_NAME,
    ) -> None:
        self._main_engine  = main_engine
        self._engine_name  = engine_name
        self._cai_engine   = None
        self._last_ratios: dict[str, float] = {}
        self._last_modifier: float = 1.0

    # ------------------------------------------------------------------ #
    #  引擎获取（懒加载）
    # ------------------------------------------------------------------ #

    def _get_cai_engine(self):
        """懒加载获取 CapitalAllocationEngine。"""
        if self._cai_engine is not None:
            return self._cai_engine
        if self._main_engine is None:
            return None
        try:
            engine = self._main_engine.get_engine(self._engine_name)
            if engine is not None:
                self._cai_engine = engine
            return engine
        except Exception as e:
            logger.debug(f"[CapitalLoader] get_engine failed: {e}")
            return None

    def is_available(self) -> bool:
        """检查 Capital Allocation AI 是否可用。"""
        return self._get_cai_engine() is not None

    # ------------------------------------------------------------------ #
    #  只读数据获取
    # ------------------------------------------------------------------ #

    def get_capital_ratios(self) -> dict[str, float]:
        """
        获取当前各 Alpha 资本分配比例。

        Returns
        -------
        dict  {alpha_id: ratio}，ratio ∈ [0, 1]
        """
        engine = self._get_cai_engine()
        if engine is None:
            return dict(self._last_ratios)
        try:
            ratios = engine.get_capital_ratios()
            if ratios:
                self._last_ratios = dict(ratios)
            return dict(self._last_ratios)
        except Exception as e:
            logger.debug(f"[CapitalLoader] get_capital_ratios: {e}")
            return dict(self._last_ratios)

    def get_risk_adjusted_ratios(self) -> dict[str, float]:
        """获取风险调整后的资本分配比例。"""
        engine = self._get_cai_engine()
        if engine is None:
            return {}
        try:
            return engine.get_risk_adjusted_ratios() or {}
        except Exception as e:
            logger.debug(f"[CapitalLoader] get_risk_adjusted_ratios: {e}")
            return {}

    def get_allocation_snapshot(self) -> dict:
        """获取完整分配快照（只读）。"""
        engine = self._get_cai_engine()
        if engine is None:
            return {}
        try:
            snap = engine.get_allocation_snapshot()
            if snap is None:
                return {}
            return snap.to_dict() if hasattr(snap, "to_dict") else {}
        except Exception as e:
            logger.debug(f"[CapitalLoader] get_allocation_snapshot: {e}")
            return {}

    def get_risk_snapshot(self) -> dict:
        """获取风险快照（只读）。"""
        engine = self._get_cai_engine()
        if engine is None:
            return {}
        try:
            snap = engine.get_risk_snapshot()
            if snap is None:
                return {}
            return snap.to_dict() if hasattr(snap, "to_dict") else {}
        except Exception as e:
            logger.debug(f"[CapitalLoader] get_risk_snapshot: {e}")
            return {}

    def get_alpha_ranking(self, limit: int = 10) -> list[dict]:
        """获取 Alpha 评分排名（只读，前 N 名）。"""
        engine = self._get_cai_engine()
        if engine is None:
            return []
        try:
            ranking = engine.get_alpha_ranking()
            if not ranking:
                return []
            result = []
            for item in ranking[:limit]:
                if hasattr(item, "to_dict"):
                    result.append(item.to_dict())
                elif isinstance(item, dict):
                    result.append(item)
            return result
        except Exception as e:
            logger.debug(f"[CapitalLoader] get_alpha_ranking: {e}")
            return []

    def get_breached_alphas(self) -> list[dict]:
        """获取当前违规（风险超限）Alpha 列表。"""
        engine = self._get_cai_engine()
        if engine is None:
            return []
        try:
            breached = engine.get_breached_alphas()
            if not breached:
                return []
            result = []
            for b in breached:
                if hasattr(b, "to_dict"):
                    result.append(b.to_dict())
                elif isinstance(b, dict):
                    result.append(b)
            return result
        except Exception as e:
            logger.debug(f"[CapitalLoader] get_breached_alphas: {e}")
            return []

    # ------------------------------------------------------------------ #
    #  Phase 5 联动：输出 regime_weight_modifier
    # ------------------------------------------------------------------ #

    def get_regime_weight_modifier(self) -> float:
        """
        返回上次设置的 regime_weight_modifier。

        该系数由 dispatcher 根据 MarketRegime 计算后设置，
        供 Capital Allocation AI 参考（Phase 5 联动核心）。

        Returns
        -------
        float [0.5, 1.5]，1.0 = 无调整
        """
        return self._last_modifier

    def set_regime_weight_modifier(self, modifier: float) -> None:
        """
        设置 regime_weight_modifier（由 dispatcher 调用）。

        ❌ 不直接修改 Capital Allocation AI 内部逻辑
        ✔  通过事件总线传播修正系数
        """
        self._last_modifier = max(0.5, min(1.5, modifier))

    # ------------------------------------------------------------------ #
    #  摘要
    # ------------------------------------------------------------------ #

    def summary(self) -> dict:
        ratios = self.get_capital_ratios()
        return {
            "source":          "capital_allocation_ai",
            "available":       self.is_available(),
            "alpha_count":     len(ratios),
            "regime_modifier": round(self._last_modifier, 4),
            "phase":           5,
        }
