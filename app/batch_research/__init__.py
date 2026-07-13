"""
批量回测研究平台 (Batch Research)

基于 VeighNa 4.4.0 的 A 股批量回测与多因子研究扩展 App。

设计原则：
- 不修改任何官方核心模块
- 以 Extension 方式扩展 BacktestingEngine
- 一个 BacktestingEngine 只回测一只股票
- 批量回测通过 for 循环创建多个 BacktestingEngine 实现
"""

from .app import BatchResearchApp
from .manager import StockPoolManager, ImportResult, get_default_pool_defs

APP_NAME = "BatchResearch"

__all__ = [
    "BatchResearchApp",
    "APP_NAME",
    "StockPoolManager",
    "ImportResult",
    "get_default_pool_defs",
]
