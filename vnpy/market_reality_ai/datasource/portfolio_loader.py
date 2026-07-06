"""
market_reality_ai/datasource/portfolio_loader.py

Phase 1: Stub — 只读接口，从 PortfolioEngine 拉取组合状态。
❌ 禁止写入或修改 PortfolioEngine。
"""
from __future__ import annotations
from datetime import datetime


class PortfolioLoader:
    """
    组合状态加载器 (只读)。

    Phase 2+: 从 PortfolioEngine 读取当前持仓、权重、
              暴露度，供仿真引擎评估压力影响。
    """

    def __init__(self, main_engine=None) -> None:
        self._main_engine = main_engine

    def get_current_positions(self) -> dict:
        """Phase 2+: 读取当前持仓快照。"""
        return {}   # stub

    def get_portfolio_weights(self) -> dict:
        """Phase 2+: 读取当前组合权重。"""
        return {}   # stub

    def get_exposure(self) -> dict:
        """Phase 3+: 读取当前市场暴露度（按资产类别）。"""
        return {}   # stub

    def get_historical_pnl(self, start: datetime,
                            end: datetime) -> list:
        """Phase 4+: 读取历史PnL序列（用于压力测试基准）。"""
        return []   # stub
