"""
alpha_factory_2/engine/scoring_engine.py  (Phase 3)

ScoringEngine — Alpha 评分引擎。

评分维度：
  IC         Pearson IC（因子值与下期收益的相关系数）
  RankIC     Spearman RankIC
  Stability  IR = mean(IC) / std(IC)
  Decay      IC 半衰期（交易日数）
  Turnover   平均换手率

综合评分：
  Total = IC_norm*0.3 + Stability_norm*0.3 + Decay_norm*0.2 + Turnover_norm*0.2

❌ 不执行任何交易逻辑
✔  仅读取 ValidationLoader 提供的验证结果
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..model.alpha_model import AlphaSignal
from ..model.score_model import AlphaScore
from ..datasource.validation_loader import ValidationLoader, ValidationResult
from ..datasource.factor_loader import FactorLoader
from ..utils.scoring_utils import compute_total_score
from ..utils.decay_utils import decay_score


class ScoringEngine:
    """
    Alpha 评分引擎（Phase 3）。

    使用方式：
        se = ScoringEngine(validation_loader=ValidationLoader())
        score = se.score(alpha)
        scores = se.batch_score(alphas)
        ranking = se.rank(scores)
    """

    def __init__(
        self,
        validation_loader: ValidationLoader | None = None,
        factor_loader:     FactorLoader | None     = None,
        log_fn:            Callable | None         = None,
        score_weights:     tuple[float, ...] | None = None,
    ) -> None:
        self._vloader = validation_loader or ValidationLoader(
            factor_loader=factor_loader or FactorLoader()
        )
        self._log     = log_fn or (lambda msg: None)
        # IC, Stability, Decay, Turnover
        self._weights = score_weights or (0.3, 0.3, 0.2, 0.2)
        self._history: list[AlphaScore] = []

    # ------------------------------------------------------------------ #
    #  单个评分
    # ------------------------------------------------------------------ #

    def score(self, alpha: AlphaSignal) -> AlphaScore:
        """
        对单个 Alpha 进行综合评分。

        流程：
          1. 拉取每个因子的验证结果
          2. 按权重加权平均各因子的 IC/RankIC/IR/HalfLife/Turnover
          3. 计算综合评分
        """
        factors = alpha.factors
        weights = alpha.weights

        if not factors:
            self._log(f"[ScoringEngine] {alpha.alpha_id} has no factors")
            return AlphaScore(alpha_id=alpha.alpha_id)

        # 拉取每个因子的验证结果
        val_results: dict[str, ValidationResult] = {}
        for f in factors:
            val_results[f] = self._vloader.load_result(f)

        # 按 Alpha 权重加权各因子指标
        # 权重取绝对值（负权重因子的 IC 方向已体现在因子选取，这里只看幅度）
        abs_weights = [abs(w) for w in weights]
        total_w     = sum(abs_weights) or 1.0
        norm_w      = [w / total_w for w in abs_weights]

        ic_agg        = sum(val_results[f].ic            * norm_w[i] for i, f in enumerate(factors))
        rank_ic_agg   = sum(val_results[f].rank_ic       * norm_w[i] for i, f in enumerate(factors))
        stability_agg = sum(val_results[f].ic_ir         * norm_w[i] for i, f in enumerate(factors))
        decay_agg     = sum(val_results[f].half_life     * norm_w[i] for i, f in enumerate(factors))
        turnover_agg  = sum(val_results[f].mean_turnover * norm_w[i] for i, f in enumerate(factors))

        total = compute_total_score(
            ic        = ic_agg,
            stability = stability_agg,
            decay     = decay_agg,
            turnover  = turnover_agg,
            weights   = self._weights,
        )

        sc = AlphaScore(
            alpha_id    = alpha.alpha_id,
            ic          = round(ic_agg, 6),
            rank_ic     = round(rank_ic_agg, 6),
            stability   = round(stability_agg, 6),
            turnover    = round(turnover_agg, 6),
            decay       = round(decay_agg, 2),
            total_score = total,
        )
        self._history.append(sc)

        self._log(
            f"[ScoringEngine] scored {alpha.alpha_id}"
            f"  IC={sc.ic:.4f}  IR={sc.stability:.3f}"
            f"  HL={sc.decay:.1f}  TO={sc.turnover:.3f}"
            f"  total={sc.total_score:.4f}"
        )
        return sc

    # ------------------------------------------------------------------ #
    #  批量评分
    # ------------------------------------------------------------------ #

    def batch_score(self, alphas: list[AlphaSignal]) -> list[AlphaScore]:
        """批量评分，返回与输入等长的评分列表。"""
        results = [self.score(a) for a in alphas]
        self._log(
            f"[ScoringEngine] batch_score: {len(results)} alphas scored"
        )
        return results

    # ------------------------------------------------------------------ #
    #  排名
    # ------------------------------------------------------------------ #

    def rank(
        self,
        scores:     list[AlphaScore],
        descending: bool = True,
    ) -> list[AlphaScore]:
        """
        按 total_score 排名，返回新列表（不修改原列表）。

        Parameters
        ----------
        scores     : AlphaScore 列表
        descending : True = 高分在前

        Returns
        -------
        list[AlphaScore]  排名后的列表
        """
        return sorted(scores, key=lambda s: s.total_score, reverse=descending)

    def top_n(
        self,
        scores: list[AlphaScore],
        n:      int = 10,
    ) -> list[AlphaScore]:
        """返回评分最高的 n 个 Alpha。"""
        return self.rank(scores)[:n]

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_score_history(self, limit: int = 200) -> list[AlphaScore]:
        return self._history[-limit:]

    def summary(self) -> dict:
        if not self._history:
            return {"scored": 0}
        scores = [s.total_score for s in self._history]
        return {
            "scored":      len(self._history),
            "mean_score":  round(sum(scores) / len(scores), 4),
            "max_score":   round(max(scores), 4),
            "min_score":   round(min(scores), 4),
        }
