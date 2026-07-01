"""
portfolio_engine/engine/portfolio_engine.py

PortfolioStateEngine — 组合状态管理器。
Phase 2：实现 set_portfolio / update_allocation / update_performance。
"""

from __future__ import annotations

from ..model.allocation_model import AllocationResult
from ..model.performance_model import PerformanceStats
from ..model.portfolio_model import Portfolio


class PortfolioStateEngine:
    """组合状态管理器（纯状态，无副作用）。"""

    def __init__(self) -> None:
        self._portfolio:   Portfolio | None        = None
        self._allocation:  AllocationResult | None = None
        self._performance: PerformanceStats | None = None

    # ------------------------------------------------------------------ #
    #  Phase 2 实现
    # ------------------------------------------------------------------ #

    def set_portfolio(self, portfolio: Portfolio) -> None:
        """设置当前活跃组合（替换旧组合，重置关联计算结果）。"""
        self._portfolio  = portfolio
        self._allocation = None
        self._performance = None

    def update_allocation(self, result: AllocationResult) -> None:
        """接收权重分配结果并更新槽位目标权重。"""
        self._allocation = result
        if self._portfolio is None or not result.is_valid:
            return
        weight_map = result.weights
        for slot in self._portfolio.slots:
            slot.target_weight = weight_map.get(slot.name, 0.0)

    def update_performance(self, stats: PerformanceStats) -> None:
        """接收绩效统计并缓存。"""
        self._performance = stats

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_portfolio(self) -> Portfolio | None:
        return self._portfolio

    def get_allocation(self) -> AllocationResult | None:
        return self._allocation

    def get_performance(self) -> PerformanceStats | None:
        return self._performance

    def is_ready(self) -> bool:
        return (
            self._portfolio  is not None
            and self._allocation is not None
            and self._allocation.is_valid
        )

    def reset(self) -> None:
        """清空所有状态（新 run 开始前调用）。"""
        self._portfolio   = None
        self._allocation  = None
        self._performance = None
