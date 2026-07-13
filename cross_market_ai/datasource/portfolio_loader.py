"""
cross_market_ai/datasource/portfolio_loader.py

只读接口 — 从 Portfolio Engine 加载组合状态。
Phase 1: 骨架。Phase 2+ 实现。
"""
from __future__ import annotations


class PortfolioDataLoader:
    """
    从 Portfolio Engine 读取组合持仓、权重、暴露信息。
    只读，不修改任何组合逻辑。
    """

    def load_portfolio_state(self) -> dict:
        """Phase 2 实现。"""
        return {"state": None, "status": "stub"}

    def load_holdings(self, market_id: str | None = None) -> dict:
        """Phase 2 实现。"""
        return {"market_id": market_id, "holdings": None, "status": "stub"}

    def load_factor_exposure(self, market_id: str | None = None) -> dict:
        """Phase 2 实现。"""
        return {"market_id": market_id, "exposure": None, "status": "stub"}
