"""
capital_allocation_ai/datasource/alpha_loader.py  (Phase 2)

AlphaLoader — Alpha 评分数据加载器。

Phase 2 实现：
  - 接入 Alpha Factory 2.0 dispatcher（AlphaFactoryEngine）
  - 加载 LIVE 状态 Alpha 列表
  - 加载 Alpha 评分快照（IC / RankIC / Stability / Decay / Turnover）
  - 模拟数据回退（当 Alpha Factory 不可用时）

❌ 只读，绝不写入 Alpha Factory
"""

from __future__ import annotations

import random
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
#  模拟数据（当 Alpha Factory 不可用时使用）
# ─────────────────────────────────────────────────────────────────────────────

_SIMULATED_ALPHAS = [f"ALPHA_{i:04d}" for i in range(1, 21)]


def _simulate_score(alpha_id: str, seed: int = 42) -> dict:
    """生成可复现的模拟评分数据（用于开发/测试）。"""
    rng  = random.Random(seed + sum(ord(c) for c in alpha_id))
    ic   = rng.uniform(-0.06, 0.10)
    return {
        "alpha_id":   alpha_id,
        "ic":         round(ic, 4),
        "rank_ic":    round(ic * rng.uniform(0.8, 1.1), 4),
        "stability":  round(rng.uniform(-0.5, 2.0), 4),   # IR
        "decay":      round(rng.uniform(0.5, 15.0), 2),   # 半衰期（日）
        "turnover":   round(rng.uniform(0.2, 0.9), 4),
        "total_score": round(rng.uniform(0.1, 0.8), 4),
        "status":     "live",
    }


def _simulate_ic_series(alpha_id: str, n: int = 60, seed: int = 42) -> list[float]:
    """生成可复现的模拟 IC 序列。"""
    rng  = random.Random(seed + sum(ord(c) for c in alpha_id))
    base = rng.uniform(-0.05, 0.08)
    return [round(base + rng.gauss(0, 0.03), 6) for _ in range(n)]


def _simulate_returns(alpha_id: str, n: int = 252, seed: int = 42) -> list[float]:
    """生成可复现的模拟日度收益率序列。"""
    rng = random.Random(seed + sum(ord(c) for c in alpha_id) + 1)
    return [round(rng.gauss(0.0003, 0.012), 6) for _ in range(n)]


def _simulate_ic_decay(alpha_id: str, max_lag: int = 20, seed: int = 42) -> list[float]:
    """生成可复现的模拟 IC Decay 曲线（逐渐衰减）。"""
    rng  = random.Random(seed + sum(ord(c) for c in alpha_id) + 2)
    base = rng.uniform(0.01, 0.08)
    decay_rate = rng.uniform(0.05, 0.25)
    return [
        round(base * (1 - decay_rate) ** lag + rng.gauss(0, 0.005), 6)
        for lag in range(max_lag)
    ]


# ─────────────────────────────────────────────────────────────────────────────
#  AlphaLoader
# ─────────────────────────────────────────────────────────────────────────────

class AlphaLoader:
    """
    从 Alpha Factory 2.0 加载 Alpha 数据（Phase 2）。

    当 Alpha Factory 不可用时自动回退到模拟数据，
    保证 ScoringEngine 在任何环境下均可运行。
    """

    def __init__(
        self,
        alpha_factory_engine=None,
        use_simulated:  bool = True,
        n_simulated:    int  = 20,
        seed:           int  = 42,
    ) -> None:
        self._engine       = alpha_factory_engine
        self._use_simulated = use_simulated
        self._n_simulated   = n_simulated
        self._seed          = seed

    # ------------------------------------------------------------------ #
    #  Alpha 列表
    # ------------------------------------------------------------------ #

    def list_alpha_ids(self) -> list[str]:
        """返回所有可用 Alpha ID 列表。"""
        if self._engine is not None:
            try:
                alphas = self._engine.list_alphas()
                if alphas:
                    return [a["alpha_id"] for a in alphas]
            except Exception:
                pass
        if self._use_simulated:
            return list(_SIMULATED_ALPHAS[:self._n_simulated])
        return []

    def list_live_alpha_ids(self) -> list[str]:
        """返回所有 LIVE 状态 Alpha 的 ID 列表。"""
        if self._engine is not None:
            try:
                live = self._engine.list_live_alphas() if hasattr(
                    self._engine, 'list_live_alphas') else []
                if live:
                    return [a["alpha_id"] for a in live]
            except Exception:
                pass
        if self._use_simulated:
            return list(_SIMULATED_ALPHAS[:self._n_simulated])
        return []

    # ------------------------------------------------------------------ #
    #  评分快照
    # ------------------------------------------------------------------ #

    def load_scores(self) -> dict[str, dict]:
        """
        加载所有 Alpha 的评分快照。

        Returns
        -------
        dict  {alpha_id: score_dict}
          score_dict keys: ic, rank_ic, stability, decay, turnover, total_score
        """
        if self._engine is not None:
            try:
                raw = self._engine.list_scores() if hasattr(
                    self._engine, 'list_scores') else []
                if raw:
                    return {s["alpha_id"]: s for s in raw}
            except Exception:
                pass
        if self._use_simulated:
            return {
                aid: _simulate_score(aid, self._seed)
                for aid in _SIMULATED_ALPHAS[:self._n_simulated]
            }
        return {}

    def load_score(self, alpha_id: str) -> dict | None:
        """加载单个 Alpha 的评分快照。"""
        all_scores = self.load_scores()
        return all_scores.get(alpha_id)

    # ------------------------------------------------------------------ #
    #  时序数据（用于 IC/Sharpe 计算）
    # ------------------------------------------------------------------ #

    def load_ic_series(
        self,
        alpha_id: str,
        n:        int = 60,
    ) -> list[float]:
        """
        加载 Alpha 的 IC 时序数据。

        Phase 2: 若来自 Alpha Factory，从 score.ic 推断；否则模拟。
        Phase 3+: 接入真实 IC 时序存储。
        """
        score = self.load_score(alpha_id)
        if score is not None and self._engine is not None:
            # 从评分快照的 ic 字段为基础生成合理时序（过渡方案）
            base = score.get("ic", 0.0)
            rng  = random.Random(self._seed + hash(alpha_id) & 0x7FFFFFFF)
            return [
                round(base + rng.gauss(0, abs(base) * 0.3 + 0.01), 6)
                for _ in range(n)
            ]
        if self._use_simulated:
            return _simulate_ic_series(alpha_id, n=n, seed=self._seed)
        return []

    def load_returns(
        self,
        alpha_id: str,
        n:        int = 252,
    ) -> list[float]:
        """
        加载 Alpha 的日度收益率序列（用于 Sharpe 计算）。

        Phase 2: 使用模拟数据。
        Phase 3+: 接入真实策略收益率。
        """
        if self._use_simulated:
            return _simulate_returns(alpha_id, n=n, seed=self._seed)
        return []

    def load_ic_decay(
        self,
        alpha_id: str,
        max_lag:  int = 20,
    ) -> list[float]:
        """
        加载 Alpha 的 IC Decay 曲线（用于衰减评分）。

        Phase 2: 若有评分快照则基于半衰期重构衰减曲线；否则模拟。
        """
        score = self.load_score(alpha_id)
        if score is not None:
            hl   = score.get("decay", 5.0)   # 半衰期（日）
            base = abs(score.get("ic", 0.03))
            if hl > 0 and base > 0:
                decay_rate = 1 - 0.5 ** (1.0 / hl)
                rng = random.Random(self._seed + hash(alpha_id) & 0x7FFFFFFF)
                return [
                    round(base * (1 - decay_rate) ** lag + rng.gauss(0, 0.002), 6)
                    for lag in range(max_lag)
                ]
        if self._use_simulated:
            return _simulate_ic_decay(alpha_id, max_lag=max_lag, seed=self._seed)
        return []

    def load_volatility(self, alpha_id: str) -> float:
        """
        加载 Alpha 的年化波动率（用于容量估算）。

        Phase 2: 由 turnover 代理估算。
        Phase 4+: 接入 RiskLoader。
        """
        score = self.load_score(alpha_id)
        if score is not None:
            turnover = score.get("turnover", 0.5)
            return round(0.1 + turnover * 0.3, 4)
        rng = random.Random(self._seed + hash(alpha_id) & 0x7FFFFFFF + 3)
        return round(rng.uniform(0.10, 0.40), 4)

    # ------------------------------------------------------------------ #
    #  元数据
    # ------------------------------------------------------------------ #

    def get_alpha_meta(self, alpha_id: str) -> dict:
        """返回 Alpha 元数据（因子数、表达式等）。"""
        if self._engine is not None:
            try:
                alphas = self._engine.list_alphas()
                for a in alphas:
                    if a.get("alpha_id") == alpha_id:
                        return a
            except Exception:
                pass
        return {"alpha_id": alpha_id, "factors": [], "expression": ""}

    def is_available(self) -> bool:
        return self._engine is not None or self._use_simulated

    def summary(self) -> dict:
        return {
            "source":        "alpha_factory" if self._engine else "simulated",
            "n_alphas":      len(self.list_alpha_ids()),
            "n_live":        len(self.list_live_alpha_ids()),
        }
