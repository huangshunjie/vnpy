"""
capital_allocation_ai/datasource/portfolio_loader.py  (Phase 3)

PortfolioLoader — 组合状态加载器。

Phase 3 实现：
  - 模拟组合净值 / 总资金 / 回撤 / 波动率
  - 接入 Portfolio Engine 的接口占位（Phase 4+ 实际接入）

❌ 只读，绝不写入 Portfolio Engine
"""

from __future__ import annotations

import random
from datetime import datetime


class PortfolioLoader:
    """
    从 Portfolio Engine 加载组合状态数据（Phase 3）。

    Phase 3: 模拟数据，接口已对齐真实 Portfolio Engine 输出。
    Phase 4+: 替换模拟数据为 PortfolioEngine.get_portfolio_summary()。
    """

    def __init__(
        self,
        portfolio_engine = None,
        total_capital:   float = 10_000_000.0,   # 默认 1000 万
        seed:            int   = 42,
    ) -> None:
        self._engine        = portfolio_engine
        self._total_capital = total_capital
        self._seed          = seed
        self._rng           = random.Random(seed)

    # ------------------------------------------------------------------ #
    #  总资金
    # ------------------------------------------------------------------ #

    def get_total_capital(self) -> float:
        """返回当前总可分配资金。"""
        if self._engine is not None:
            try:
                return float(self._engine.get_total_capital())
            except Exception:
                pass
        return self._total_capital

    def set_total_capital(self, capital: float) -> None:
        """设置模拟总资金（测试/开发用）。"""
        self._total_capital = capital

    # ------------------------------------------------------------------ #
    #  组合净值
    # ------------------------------------------------------------------ #

    def get_portfolio_nav(self) -> float:
        """返回当前组合净值（Phase 3: 模拟）。"""
        if self._engine is not None:
            try:
                return float(self._engine.get_portfolio_nav())
            except Exception:
                pass
        rng = random.Random(self._seed + int(datetime.now().timestamp()) % 100)
        return round(1.0 + rng.uniform(-0.05, 0.15), 4)

    # ------------------------------------------------------------------ #
    #  风险指标
    # ------------------------------------------------------------------ #

    def get_drawdown(self) -> float:
        """返回当前最大回撤（Phase 3: 模拟 0~15%）。"""
        if self._engine is not None:
            try:
                return float(self._engine.get_drawdown())
            except Exception:
                pass
        return round(self._rng.uniform(0.0, 0.15), 4)

    def get_volatility(self) -> float:
        """返回当前组合年化波动率（Phase 3: 模拟 5%~25%）。"""
        if self._engine is not None:
            try:
                return float(self._engine.get_volatility())
            except Exception:
                pass
        return round(self._rng.uniform(0.05, 0.25), 4)

    # ------------------------------------------------------------------ #
    #  策略资金快照
    # ------------------------------------------------------------------ #

    def get_strategy_capitals(self) -> dict[str, float]:
        """
        返回各策略当前资金分配快照（Phase 3: 空）。

        Phase 4+: 接入 PortfolioEngine 策略资金映射。
        """
        if self._engine is not None:
            try:
                return dict(self._engine.get_strategy_capitals())
            except Exception:
                pass
        return {}

    # ------------------------------------------------------------------ #
    #  汇总
    # ------------------------------------------------------------------ #

    def get_summary(self) -> dict:
        return {
            "source":        "portfolio_engine" if self._engine else "simulated",
            "total_capital": self.get_total_capital(),
            "nav":           self.get_portfolio_nav(),
            "drawdown":      self.get_drawdown(),
            "volatility":    self.get_volatility(),
        }

    def is_available(self) -> bool:
        return True   # 模拟数据始终可用
