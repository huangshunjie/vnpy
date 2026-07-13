"""
global_portfolio_intelligence/__init__.py

顶层导出。
"""
from .app    import GlobalPortfolioIntelligenceApp
from .engine import GlobalPortfolioEngine
from .constant import (
    APP_NAME, OptimizationMode, RebalanceTrigger,
    AllocationMode, SystemStatus,
)
from .event import (
    EVENT_GLOBAL_STATE_UPDATED,
    EVENT_OBJECTIVE_UPDATED,
    EVENT_ALLOCATION_UPDATED,
    EVENT_REBALANCE_TRIGGERED,
    EVENT_SYSTEM_OPTIMIZED,
)

__all__ = [
    "GlobalPortfolioIntelligenceApp",
    "GlobalPortfolioEngine",
    "APP_NAME",
    "OptimizationMode",
    "RebalanceTrigger",
    "AllocationMode",
    "SystemStatus",
    "EVENT_GLOBAL_STATE_UPDATED",
    "EVENT_OBJECTIVE_UPDATED",
    "EVENT_ALLOCATION_UPDATED",
    "EVENT_REBALANCE_TRIGGERED",
    "EVENT_SYSTEM_OPTIMIZED",
]
