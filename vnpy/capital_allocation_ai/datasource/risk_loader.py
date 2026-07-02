"""
capital_allocation_ai/datasource/risk_loader.py  (Phase 4)

RiskLoader — 风险指标加载器。

Phase 4 实现：
  - 模拟 Alpha 级风险指标（Volatility / Drawdown / Beta / VaR / Sharpe）
  - 接入 Risk Engine 2.0 的接口占位（Phase 5+ 实际接入）
  - 组合级 VaR / 整体风险评估

❌ 只读，绝不写入 Risk Engine
"""

from __future__ import annotations

import math
import random
from datetime import datetime


def _rng(seed: int, alpha_id: str) -> random.Random:
    return random.Random(seed + sum(ord(c) for c in alpha_id) + 99)


class RiskLoader:
    """
    从 Risk Engine 加载风险指标数据（Phase 4）。

    Phase 4: 模拟数据，接口已对齐真实 Risk Engine 输出。
    Phase 5+: 替换模拟数据为 RiskEngine.get_alpha_risk()。
    """

    def __init__(
        self,
        risk_engine=None,
        seed: int = 42,
    ) -> None:
        self._engine = risk_engine
        self._seed   = seed
        self._cache: dict[str, dict] = {}   # {alpha_id: risk_dict}

    # ------------------------------------------------------------------ #
    #  单 Alpha 风险指标
    # ------------------------------------------------------------------ #

    def get_alpha_risk(self, alpha_id: str) -> dict:
        """
        返回单个 Alpha 的全套风险指标。

        Keys: vol, drawdown, beta, var_95, sharpe, calmar
        """
        if alpha_id in self._cache:
            return self._cache[alpha_id]

        if self._engine is not None:
            try:
                data = self._engine.get_alpha_risk(alpha_id)
                if data:
                    self._cache[alpha_id] = data
                    return data
            except Exception:
                pass

        rng = _rng(self._seed, alpha_id)
        data = {
            "alpha_id":  alpha_id,
            "vol":       round(rng.uniform(0.08, 0.40), 4),   # 年化波动率
            "drawdown":  round(rng.uniform(0.02, 0.25), 4),   # 最大回撤
            "beta":      round(rng.uniform(-0.3, 1.2),  4),   # 市场敞口
            "var_95":    round(rng.uniform(0.01, 0.06), 4),   # 95% VaR（日度）
            "sharpe":    round(rng.uniform(-0.5, 2.5),  4),   # Sharpe
            "calmar":    round(rng.uniform(0.0,  3.0),  4),   # Calmar
            "ts":        str(datetime.now())[:19],
        }
        self._cache[alpha_id] = data
        return data

    def get_alpha_volatility(self, alpha_id: str) -> float:
        return self.get_alpha_risk(alpha_id)["vol"]

    def get_alpha_drawdown(self, alpha_id: str) -> float:
        return self.get_alpha_risk(alpha_id)["drawdown"]

    def get_alpha_beta(self, alpha_id: str) -> float:
        return self.get_alpha_risk(alpha_id)["beta"]

    def get_alpha_var(self, alpha_id: str) -> float:
        return self.get_alpha_risk(alpha_id)["var_95"]

    # ------------------------------------------------------------------ #
    #  批量 Alpha 风险指标
    # ------------------------------------------------------------------ #

    def get_all_risk_metrics(
        self,
        alpha_ids: list[str],
    ) -> dict[str, dict]:
        """
        批量加载风险指标。

        Returns
        -------
        dict  {alpha_id: risk_dict}
        """
        return {aid: self.get_alpha_risk(aid) for aid in alpha_ids}

    # ------------------------------------------------------------------ #
    #  组合级指标
    # ------------------------------------------------------------------ #

    def get_portfolio_var(
        self,
        alpha_ids:   list[str],
        ratios:      dict[str, float],
        corr_factor: float = 0.5,
    ) -> float:
        """
        估算加权组合 VaR（95%，日度）。

        简化模型（假设均匀相关系数 corr_factor）：
            portfolio_vol = sqrt( sum(w_i^2 * vol_i^2)
                                + corr * sum_{i!=j} w_i*w_j*vol_i*vol_j )
            VaR_95 = 1.645 * portfolio_vol

        Returns
        -------
        float  组合日度 95% VaR（占净值比例）
        """
        if not alpha_ids or not ratios:
            return 0.0

        vols = [
            self.get_alpha_volatility(aid) / math.sqrt(252)   # 日化
            for aid in alpha_ids
        ]
        ws = [ratios.get(aid, 0.0) for aid in alpha_ids]

        # 方差项
        var_diag = sum((w * v) ** 2 for w, v in zip(ws, vols))
        # 协方差项（均匀相关）
        cov_off = 0.0
        n = len(alpha_ids)
        for i in range(n):
            for j in range(i + 1, n):
                cov_off += 2 * corr_factor * ws[i] * ws[j] * vols[i] * vols[j]

        port_vol = math.sqrt(var_diag + cov_off)
        return round(1.645 * port_vol, 6)

    def get_portfolio_drawdown(
        self,
        alpha_ids: list[str],
        ratios:    dict[str, float],
    ) -> float:
        """加权组合最大回撤估算。"""
        if not alpha_ids:
            return 0.0
        weighted = sum(
            ratios.get(aid, 0.0) * self.get_alpha_drawdown(aid)
            for aid in alpha_ids
        )
        return round(weighted, 6)

    def get_portfolio_beta(
        self,
        alpha_ids: list[str],
        ratios:    dict[str, float],
    ) -> float:
        """加权组合 Beta（市场敞口）。"""
        if not alpha_ids:
            return 0.0
        weighted = sum(
            ratios.get(aid, 0.0) * self.get_alpha_beta(aid)
            for aid in alpha_ids
        )
        return round(weighted, 6)

    # ------------------------------------------------------------------ #
    #  缓存管理
    # ------------------------------------------------------------------ #

    def invalidate_cache(self, alpha_id: str | None = None) -> None:
        """清除缓存（None 则清除全部）。"""
        if alpha_id is None:
            self._cache.clear()
        else:
            self._cache.pop(alpha_id, None)

    def is_available(self) -> bool:
        return True   # 模拟数据始终可用

    def summary(self) -> dict:
        return {
            "source":   "risk_engine" if self._engine else "simulated",
            "cached":   len(self._cache),
        }
