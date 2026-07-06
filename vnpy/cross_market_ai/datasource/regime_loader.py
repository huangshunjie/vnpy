"""
cross_market_ai/datasource/regime_loader.py

Phase 3: 只读 Regime 数据加载器。
数据来源：MarketRegimeAI（只读），不可用时返回先验分布。
禁止写入或修改 MarketRegimeAI。
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Optional


class RegimeDataLoader:
    """
    从 MarketRegimeAI 读取 Regime 状态数据。
    纯只读；上层不可用时返回统计先验。
    """

    # 各市场先验 Regime 分布
    _REGIME_PRIORS: dict[str, dict] = {
        "equity_cn":    {"bull": 0.38, "bear": 0.28, "sideways": 0.22, "high_vol": 0.12},
        "futures_cn":   {"trend_up": 0.30, "trend_down": 0.25, "range": 0.35, "extreme": 0.10},
        "equity_us":    {"bull": 0.45, "bear": 0.20, "sideways": 0.28, "high_vol": 0.07},
        "crypto":       {"bull": 0.30, "bear": 0.35, "sideways": 0.20, "extreme": 0.15},
        "forex":        {"trend": 0.40, "range": 0.50, "volatile": 0.10},
        "fixed_income": {"rally": 0.35, "selloff": 0.20, "stable": 0.45},
    }
    _DEFAULT_PRIOR = {"bull": 0.35, "bear": 0.25, "sideways": 0.30, "extreme": 0.10}

    # 各市场先验转移矩阵（regime_a -> regime_b 概率，简化为停留概率）
    _PERSISTENCE: dict[str, float] = {
        "equity_cn":    0.72,
        "futures_cn":   0.68,
        "equity_us":    0.78,
        "crypto":       0.60,
        "forex":        0.75,
        "fixed_income": 0.85,
    }

    def __init__(self, main_engine=None) -> None:
        self._main_engine = main_engine

    # ── 主接口 ────────────────────────────────────────────────────────

    def load_current_regime(self, market_id: str) -> dict:
        """加载当前 Regime 状态快照。优先从 MarketRegimeAI 读取。"""
        live = self._try_fetch_live_regime(market_id)
        if live:
            return {**live, "source": "live", "market_id": market_id, "loaded_at": _now()}

        dist    = self._get_prior(market_id)
        dominant = max(dist, key=lambda k: dist[k])
        return {
            "market_id":       market_id,
            "regime":          dominant,
            "confidence":      dist[dominant],
            "distribution":    dist,
            "regime_changed":  False,
            "duration_bars":   0,
            "stability":       self._PERSISTENCE.get(market_id, 0.72),
            "source":          "prior",
            "loaded_at":       _now(),
        }

    def load_regime_distribution(self, market_id: str) -> dict:
        """加载历史 Regime 分布（各状态占比）。"""
        dist = self._get_prior(market_id)
        entropy = _shannon_entropy(dist)
        persistence = self._PERSISTENCE.get(market_id, 0.72)
        return {
            "market_id":    market_id,
            "distribution": dist,
            "n_regimes":    len(dist),
            "entropy":      round(entropy, 4),
            "persistence":  round(persistence, 4),
            "dominant":     max(dist, key=lambda k: dist[k]),
            "source":       "prior",
            "loaded_at":    _now(),
        }

    def load_transition_matrix(self, market_id: str) -> dict:
        """
        加载 Regime 转移矩阵。
        近似构造：对角线为留存概率，非对角按均匀分布。
        """
        dist        = self._get_prior(market_id)
        regimes     = list(dist.keys())
        n           = len(regimes)
        persistence = self._PERSISTENCE.get(market_id, 0.72)
        off_diag    = (1.0 - persistence) / max(n - 1, 1)

        matrix: dict[str, dict[str, float]] = {}
        for r in regimes:
            row: dict[str, float] = {}
            for c in regimes:
                row[c] = round(persistence if r == c else off_diag, 4)
            matrix[r] = row

        return {
            "market_id": market_id,
            "regimes":   regimes,
            "matrix":    matrix,
            "source":    "prior",
            "loaded_at": _now(),
        }

    def load_regime_history(
        self, market_id: str, lookback_days: int = 252
    ) -> dict:
        """加载历史 Regime 序列摘要。"""
        dist = self._get_prior(market_id)
        n_bars = lookback_days
        sequence = []
        regimes = list(dist.keys())
        probs   = list(dist.values())
        import random
        rng = random.Random(42)
        current_idx = regimes.index(max(dist, key=lambda k: dist[k]))
        for _ in range(min(n_bars, 100)):
            if rng.random() > self._PERSISTENCE.get(market_id, 0.72):
                current_idx = rng.choices(range(len(regimes)), weights=probs)[0]
            sequence.append(regimes[current_idx])

        return {
            "market_id":     market_id,
            "sequence":      sequence,
            "lookback_days": lookback_days,
            "n_bars":        len(sequence),
            "source":        "prior",
            "loaded_at":     _now(),
        }

    def load_cross_regime_overlap(
        self, market_a: str, market_b: str
    ) -> dict:
        """
        计算两市场 Regime 分布的重叠度。
        两分布共享越多高概率状态，越适合 Alpha 迁移。
        """
        dist_a = self._get_prior(market_a)
        dist_b = self._get_prior(market_b)
        overlap = _compute_distribution_overlap(dist_a, dist_b)
        kl      = _kl_divergence(dist_a, dist_b)
        return {
            "market_a":  market_a,
            "market_b":  market_b,
            "overlap":   round(overlap, 4),
            "kl_div":    round(kl, 4),
            "alignable": overlap >= 0.4,
            "source":    "prior",
            "loaded_at": _now(),
        }

    # ── 只读上层引擎 ──────────────────────────────────────────────────

    def _try_fetch_live_regime(self, market_id: str) -> Optional[dict]:
        if self._main_engine is None:
            return None
        try:
            reng = self._main_engine.get_engine("MarketRegimeAI")
            if reng and hasattr(reng, "get_current_state"):
                state = reng.get_current_state()
                if state:
                    d = state.to_dict() if hasattr(state, "to_dict") else dict(state)
                    return d
        except Exception:
            pass
        return None

    def _get_prior(self, market_id: str) -> dict:
        if market_id in self._REGIME_PRIORS:
            return self._REGIME_PRIORS[market_id]
        prefix = market_id.split("_")[0]
        for key in self._REGIME_PRIORS:
            if key.startswith(prefix):
                return self._REGIME_PRIORS[key]
        return self._DEFAULT_PRIOR


# ── 纯函数工具 ────────────────────────────────────────────────────────

def _now() -> str:
    return str(datetime.now())[:19]


def _shannon_entropy(dist: dict) -> float:
    values = [v for v in dist.values() if v > 0]
    if not values:
        return 0.0
    raw = -sum(p * math.log2(p) for p in values)
    max_e = math.log2(len(values)) if len(values) > 1 else 1.0
    return raw / max_e if max_e > 0 else 0.0


def _compute_distribution_overlap(dist_a: dict, dist_b: dict) -> float:
    """Bhattacharyya 系数作为分布重叠度。"""
    all_keys = set(dist_a) | set(dist_b)
    bc = sum(
        math.sqrt(dist_a.get(k, 0.0) * dist_b.get(k, 0.0))
        for k in all_keys
    )
    return min(bc, 1.0)


def _kl_divergence(p: dict, q: dict) -> float:
    """KL 散度 D_KL(P||Q)，处理零概率。"""
    eps = 1e-9
    all_keys = set(p) | set(q)
    return sum(
        p.get(k, eps) * math.log(p.get(k, eps) / max(q.get(k, eps), eps))
        for k in all_keys
        if p.get(k, 0) > 0
    )
