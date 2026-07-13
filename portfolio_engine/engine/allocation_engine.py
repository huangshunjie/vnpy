"""
portfolio_engine/engine/allocation_engine.py

AllocationEngine — 权重分配引擎。

三种权重模型（Phase 2 实现）：
  1. Equal Weight         w_i = 1/N
  2. Volatility Target    w_i ∝ 1/σ_i，归一化后求和=1
  3. Risk Parity          w_i ∝ 1/σ_i（简化近似，无需优化器）

风险平价说明：
  严格的风险平价需要迭代优化（minimize RC_i - RC_j）。
  Phase 2 使用 Inverse Volatility 近似（等价于假设资产间零相关），
  Phase 3 可替换为基于相关矩阵的精确解。
"""

from __future__ import annotations

import math
from datetime import datetime

import numpy as np
import pandas as pd

from ..constant import WeightMethod
from ..model.allocation_model import AllocationResult
from ..model.portfolio_model import Portfolio
from ..utils.math_utils import annualised_volatility


class AllocationEngine:
    """权重分配引擎（纯函数风格，无状态存储）。"""

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def compute(
        self,
        portfolio: Portfolio,
        returns_map: dict[str, pd.Series],
    ) -> AllocationResult:
        """根据 portfolio.weight_method 路由到对应模型。"""
        method = portfolio.weight_method
        if method == WeightMethod.EQUAL:
            return self.compute_equal(portfolio)
        elif method == WeightMethod.VOLATILITY_TARGET:
            return self.compute_vol_target(portfolio, returns_map)
        elif method == WeightMethod.RISK_PARITY:
            return self.compute_risk_parity(portfolio, returns_map)
        else:
            raise ValueError(f"Unknown WeightMethod: {method}")

    # ------------------------------------------------------------------ #
    #  1. Equal Weight
    # ------------------------------------------------------------------ #

    def compute_equal(self, portfolio: Portfolio) -> AllocationResult:
        """等权：w_i = 1/N（只考虑 enabled slots）。"""
        slots = [s for s in portfolio.slots if s.enabled]
        n = len(slots)
        if n == 0:
            return AllocationResult(
                method=WeightMethod.EQUAL,
                weights={},
                n_slots=0,
                is_valid=False,
            )
        w = round(1.0 / n, 10)
        weights = {s.name: w for s in slots}
        # 因浮点舍入，把最后一项补齐到精确 1.0
        names = list(weights)
        total = sum(weights.values())
        weights[names[-1]] += round(1.0 - total, 10)

        return AllocationResult(
            method=WeightMethod.EQUAL,
            weights=weights,
            n_slots=n,
            is_valid=True,
        )

    # ------------------------------------------------------------------ #
    #  2. Volatility Target
    # ------------------------------------------------------------------ #

    def compute_vol_target(
        self,
        portfolio: Portfolio,
        returns_map: dict[str, pd.Series],
    ) -> AllocationResult:
        """
        波动率目标：w_i ∝ 1/σ_i，归一化后求和=1。
        σ_i 无法计算的槽位退化为等权参与。
        """
        slots = [s for s in portfolio.slots if s.enabled]
        n = len(slots)
        if n == 0:
            return AllocationResult(
                method=WeightMethod.VOLATILITY_TARGET,
                weights={}, n_slots=0, is_valid=False,
            )

        vols: dict[str, float] = {}
        for s in slots:
            r = returns_map.get(s.name)
            if r is not None and len(r.dropna()) >= 5:
                v = annualised_volatility(r)
                vols[s.name] = v if (not math.isnan(v) and v > 1e-10) else float("nan")
            else:
                vols[s.name] = float("nan")

        # 对 vol 有效的槽位用 1/σ；无效的槽位用其余平均 1/σ 代替
        valid_inv = {k: 1.0 / v for k, v in vols.items() if not math.isnan(v)}
        if valid_inv:
            fallback = float(np.mean(list(valid_inv.values())))
        else:
            fallback = 1.0

        raw = {s.name: valid_inv.get(s.name, fallback) for s in slots}
        total = sum(raw.values())
        weights = {k: v / total for k, v in raw.items()}

        return AllocationResult(
            method=WeightMethod.VOLATILITY_TARGET,
            weights=weights,
            n_slots=n,
            volatilities={k: v for k, v in vols.items() if not math.isnan(v)},
            is_valid=True,
        )

    # ------------------------------------------------------------------ #
    #  3. Risk Parity（Inverse Volatility 近似）
    # ------------------------------------------------------------------ #

    def compute_risk_parity(
        self,
        portfolio: Portfolio,
        returns_map: dict[str, pd.Series],
    ) -> AllocationResult:
        """
        风险平价（Inverse Volatility 近似）：w_i ∝ 1/σ_i。

        当资产间相关性为零时，inverse-vol 权重使得每个资产的
        风险贡献 RC_i = w_i × σ_i 恰好相等。
        对于低相关多策略组合，这是一个合理的 Phase 2 近似。
        """
        result = self.compute_vol_target(portfolio, returns_map)

        # 计算理论风险贡献（供 UI 显示）
        vols = result.volatilities
        risk_contribs: dict[str, float] = {}
        for name, w in result.weights.items():
            sigma = vols.get(name, float("nan"))
            rc = w * sigma if not math.isnan(sigma) else float("nan")
            risk_contribs[name] = rc

        result.method        = WeightMethod.RISK_PARITY
        result.risk_contribs = risk_contribs
        return result

    # ------------------------------------------------------------------ #
    #  工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _normalise(raw: dict[str, float]) -> dict[str, float]:
        """把任意正值字典归一化为权重（和=1）。"""
        total = sum(raw.values())
        if total < 1e-12:
            n = len(raw)
            return {k: 1.0 / n for k in raw}
        return {k: v / total for k, v in raw.items()}
