"""
capital_allocation_ai/engine/scoring_engine.py  (Phase 2)

AlphaCapitalScoringEngine — Alpha 资本评分引擎（完整实现）。

评分维度：
  IC Mean      Pearson IC 均值（因子与下期收益相关性）
  Stability    IC 信息比率 IR = mean(IC)/std(IC)
  Capacity     容量评分：|IC| × √N × (1/(1+vol))，归一化到 [0,1]
  Decay        IC 半衰期评分：half_life / 20，归一化到 [0,1]
  Sharpe       年化 Sharpe 比率（辅助，不进综合分）

综合资本评分：
  Capital Score = IC*0.30 + Stability*0.25 + Capacity*0.25 + Decay*0.20

❌ 不执行任何交易逻辑
✔  仅读取 AlphaLoader 提供的数据
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..constant import AllocationStatus
from ..model.alpha_capital_model import AlphaCapitalScore
from ..datasource.alpha_loader import AlphaLoader
from ..utils.scoring_utils import (
    compute_ic_mean,
    compute_stability,
    estimate_capacity,
    compute_decay_score,
    compute_sharpe,
    compute_capital_score,
    normalize_capital_scores,
    rank_alphas_by_score,
)


class AlphaCapitalScoringEngine:
    """
    Alpha 资本评分引擎（Phase 2）。

    使用方式：
        engine = AlphaCapitalScoringEngine(alpha_loader=AlphaLoader())
        score  = engine.score("ALPHA_0001")
        scores = engine.batch_score(["ALPHA_0001", "ALPHA_0002"])
        ranking = engine.get_ranking()
    """

    def __init__(
        self,
        alpha_loader:   AlphaLoader | None  = None,
        log_fn:         Callable | None     = None,
        score_weights:  tuple[float, ...] | None = None,
        n_symbols:      int   = 100,
        ic_series_len:  int   = 60,
        returns_len:    int   = 252,
        ic_decay_lag:   int   = 20,
    ) -> None:
        self._loader     = alpha_loader or AlphaLoader()
        self._log        = log_fn or (lambda msg: None)
        self._weights    = score_weights or (0.3, 0.25, 0.25, 0.2)
        self._n_symbols  = n_symbols
        self._ic_len     = ic_series_len
        self._ret_len    = returns_len
        self._decay_lag  = ic_decay_lag
        self._scores: dict[str, AlphaCapitalScore] = {}
        self._count  = 0

    # ------------------------------------------------------------------ #
    #  单个评分
    # ------------------------------------------------------------------ #

    def score(self, alpha_id: str) -> AlphaCapitalScore:
        """
        对单个 Alpha 进行资本评分。

        流程：
          1. 加载 IC 序列 → IC Mean + Stability
          2. 加载波动率 → Capacity
          3. 加载 IC Decay 曲线 → Decay Score
          4. 加载收益率序列 → Sharpe
          5. 计算综合 Capital Score
        """
        # 1. IC 序列
        ic_series = self._loader.load_ic_series(alpha_id, n=self._ic_len)
        ic_mean   = compute_ic_mean(ic_series)
        stability = compute_stability(ic_series)

        # 2. 容量评分
        vol      = self._loader.load_volatility(alpha_id)
        capacity = estimate_capacity(
            ic_mean    = ic_mean,
            volatility = vol,
            n_symbols  = self._n_symbols,
        )

        # 3. IC Decay → 衰减评分
        ic_decay    = self._loader.load_ic_decay(alpha_id, max_lag=self._decay_lag)
        decay_score = compute_decay_score(ic_decay, max_lag=float(self._decay_lag))

        # 4. 半衰期（用于展示）
        half_life = self._estimate_half_life(ic_decay)

        # 5. Sharpe（辅助）
        returns = self._loader.load_returns(alpha_id, n=self._ret_len)
        sharpe  = compute_sharpe(returns)

        # 6. 综合资本评分
        capital_sc = compute_capital_score(
            ic_mean   = ic_mean,
            stability = stability,
            capacity  = capacity,
            decay     = decay_score,
            weights   = self._weights,
        )

        sc = AlphaCapitalScore(
            alpha_id      = alpha_id,
            ic_mean       = round(ic_mean,    6),
            stability     = round(stability,  6),
            capacity      = round(capacity,   6),
            decay         = round(decay_score, 6),
            sharpe        = round(sharpe,     6),
            capital_score = capital_sc,
            ic_series_len = len(ic_series),
            half_life     = round(half_life,  2),
            volatility    = round(vol,        6),
            status        = AllocationStatus.ACTIVE,
        )
        self._scores[alpha_id] = sc
        self._count += 1

        self._log(
            f"[ScoringEngine] scored {alpha_id}"
            f"  IC={ic_mean:.4f}  IR={stability:.3f}"
            f"  cap={capacity:.3f}  decay={decay_score:.3f}"
            f"  Sharpe={sharpe:.3f}  Capital={capital_sc:.4f}"
        )
        return sc

    # ------------------------------------------------------------------ #
    #  批量评分
    # ------------------------------------------------------------------ #

    def batch_score(
        self,
        alpha_ids: list[str] | None = None,
    ) -> list[AlphaCapitalScore]:
        """
        批量评分。

        Parameters
        ----------
        alpha_ids : 指定 Alpha ID 列表；None 则评分所有可用 Alpha

        Returns
        -------
        list[AlphaCapitalScore]
        """
        if alpha_ids is None:
            alpha_ids = self._loader.list_alpha_ids()
        results = [self.score(aid) for aid in alpha_ids]
        self._log(
            f"[ScoringEngine] batch_score: {len(results)} alphas scored"
        )
        return results

    # ------------------------------------------------------------------ #
    #  排名与查询
    # ------------------------------------------------------------------ #

    def get_ranking(
        self,
        top_n:       int  = 50,
        live_only:   bool = False,
    ) -> list[AlphaCapitalScore]:
        """
        按 capital_score 降序返回 Alpha 排名。

        Parameters
        ----------
        top_n     : 返回前 N 个
        live_only : True 则只返回 status=ACTIVE 的 Alpha
        """
        candidates = list(self._scores.values())
        if live_only:
            candidates = [s for s in candidates
                          if s.status == AllocationStatus.ACTIVE]
        ranked = sorted(candidates,
                        key=lambda s: s.capital_score, reverse=True)
        return ranked[:top_n]

    def get_score(self, alpha_id: str) -> AlphaCapitalScore | None:
        return self._scores.get(alpha_id)

    def get_scores(self) -> dict[str, AlphaCapitalScore]:
        return dict(self._scores)

    def get_normalized_ratios(self) -> dict[str, float]:
        """返回按 capital_score 归一化后的资金比例字典。"""
        raw = {k: v.capital_score for k, v in self._scores.items()
               if v.status == AllocationStatus.ACTIVE}
        return normalize_capital_scores(raw)

    # ------------------------------------------------------------------ #
    #  内部辅助
    # ------------------------------------------------------------------ #

    @staticmethod
    def _estimate_half_life(ic_decay: list[float]) -> float:
        """从 IC Decay 曲线估算半衰期。"""
        if not ic_decay or abs(ic_decay[0]) < 1e-12:
            return 0.0
        base   = abs(ic_decay[0])
        target = base * 0.5
        n      = len(ic_decay)
        for lag in range(1, n):
            if abs(ic_decay[lag]) <= target:
                prev = abs(ic_decay[lag - 1])
                curr = abs(ic_decay[lag])
                if prev > curr:
                    frac = (prev - target) / (prev - curr)
                    return round(lag - 1 + frac, 2)
                return float(lag)
        return float(n)

    # ------------------------------------------------------------------ #
    #  摘要
    # ------------------------------------------------------------------ #

    def summary(self) -> dict:
        if not self._scores:
            return {"scored": 0, "phase": 2}
        scores = [s.capital_score for s in self._scores.values()]
        return {
            "scored":     len(self._scores),
            "mean_score": round(sum(scores) / len(scores), 4),
            "max_score":  round(max(scores), 4),
            "min_score":  round(min(scores), 4),
            "phase":      2,
        }
