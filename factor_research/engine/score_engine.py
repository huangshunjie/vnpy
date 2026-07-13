"""
factor_research/engine/score_engine.py

ScoreEngine — 因子综合评分引擎。

评分维度（6维，与 ScoreTab 保持一致）：
  1. |IC 均值|        满分基准 0.10
  2. |ICIR|           满分基准 2.0
  3. IC 胜率          偏离50%满分基准 25%
  4. 单调性           满分基准 |mono|=1.0
  5. |L-S Sharpe|     满分基准 2.0
  6. L-S 抗回撤       满分基准 MDD=0%
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..model import (
    FactorScore,
    IcStats,
    QuantileResult,
    ScoreDimension,
)

_TRADING_DAYS = 252


class ScoreEngine:
    """因子综合评分引擎。"""

    _DEFAULT_WEIGHTS: dict[str, float] = {
        "|IC| 均值":    1.0,
        "|ICIR|":       1.0,
        "IC 胜率":      1.0,
        "单调性":       1.0,
        "|L-S Sharpe|": 1.0,
        "L-S 抗回撤":   1.0,
    }

    def __init__(self) -> None:
        self._weights: dict[str, float] = dict(self._DEFAULT_WEIGHTS)

    def set_weights(self, weights: dict[str, float]) -> None:
        """设置各维度评分权重（key 为维度名称，value 为权重值）。"""
        if not weights:
            raise ValueError("weights 不能为空")
        invalid = [k for k in weights if k not in self._DEFAULT_WEIGHTS]
        if invalid:
            raise ValueError(f"未知维度名称：{invalid}")
        self._weights.update(weights)

    def compute_score(
        self,
        metrics: dict[str, Any] | None = None,
        *,
        ic_stats: IcStats | None = None,
        quantile_result: QuantileResult | None = None,
    ) -> FactorScore:
        """
        计算因子综合评分。

        支持两种调用方式：
          1. compute_score(ic_stats=ic, quantile_result=qr)  — 强类型
          2. compute_score({"ic_stats": ic, "quantile_result": qr})  — 字典

        返回 FactorScore，包含各维度得分、综合评分、等级。
        """
        if metrics is not None:
            ic_stats        = metrics.get("ic_stats", ic_stats)
            quantile_result = metrics.get("quantile_result", quantile_result)

        if ic_stats is None:
            raise ValueError("compute_score() 需要 ic_stats 参数")

        def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
            return max(lo, min(hi, v))

        def _nan(v: float) -> bool:
            return math.isnan(v) if isinstance(v, float) else False

        dims: list[ScoreDimension] = []

        # ── 1. |IC 均值| ────────────────────────────────────────────
        ic_abs = abs(ic_stats.ic_mean) if not _nan(ic_stats.ic_mean) else float("nan")
        ic_score = _clamp(ic_abs / 0.10 * 100) if not _nan(ic_abs) else 0.0
        dims.append(ScoreDimension(
            name="|IC| 均值",
            raw_value=ic_abs,
            score=ic_score,
            weight=self._weights["|IC| 均值"],
            description="满分基准 |IC|=0.10",
        ))

        # ── 2. |ICIR| ───────────────────────────────────────────────
        icir_abs = abs(ic_stats.icir) if not _nan(ic_stats.icir) else float("nan")
        icir_score = _clamp(icir_abs / 2.0 * 100) if not _nan(icir_abs) else 0.0
        dims.append(ScoreDimension(
            name="|ICIR|",
            raw_value=icir_abs,
            score=icir_score,
            weight=self._weights["|ICIR|"],
            description="满分基准 |ICIR|=2.0",
        ))

        # ── 3. IC 胜率 ──────────────────────────────────────────────
        pr = ic_stats.ic_positive_rate if not _nan(ic_stats.ic_positive_rate) else float("nan")
        if not _nan(pr):
            deviation = abs(pr - 0.5) * 100
            wr_score  = _clamp(deviation / 25.0 * 100)
        else:
            wr_score = 0.0
        dims.append(ScoreDimension(
            name="IC 胜率",
            raw_value=pr * 100 if not _nan(pr) else float("nan"),
            score=wr_score,
            weight=self._weights["IC 胜率"],
            description="胜率偏离50%越大越好，满分基准75%",
        ))

        # ── 4. 单调性 ───────────────────────────────────────────────
        if quantile_result is not None and not _nan(quantile_result.monotonicity_score):
            mono = quantile_result.monotonicity_score
        else:
            mono = float("nan")
        mono_score = _clamp(abs(mono) * 100) if not _nan(mono) else 0.0
        dims.append(ScoreDimension(
            name="单调性",
            raw_value=mono,
            score=mono_score,
            weight=self._weights["单调性"],
            description="满分基准 |单调性|=1.0",
        ))

        # ── 5. |L-S Sharpe| ─────────────────────────────────────────
        ls_sharpe = self._calc_ls_sharpe(quantile_result)
        ls_abs    = abs(ls_sharpe) if not _nan(ls_sharpe) else float("nan")
        ls_score  = _clamp(ls_abs / 2.0 * 100) if not _nan(ls_abs) else 0.0
        dims.append(ScoreDimension(
            name="|L-S Sharpe|",
            raw_value=ls_sharpe,
            score=ls_score,
            weight=self._weights["|L-S Sharpe|"],
            description="满分基准 |Sharpe|=2.0",
        ))

        # ── 6. L-S 抗回撤 ────────────────────────────────────────────
        ls_mdd = self._calc_ls_mdd(quantile_result)
        if not _nan(ls_mdd):
            mdd_score = _clamp(max(0.0, 1.0 - abs(ls_mdd) / 0.5) * 100)
        else:
            mdd_score = 0.0
        dims.append(ScoreDimension(
            name="L-S 抗回撤",
            raw_value=ls_mdd,
            score=mdd_score,
            weight=self._weights["L-S 抗回撤"],
            description="满分基准 MDD=0%，MDD≥50%得0分",
        ))

        # ── 加权综合得分 ──────────────────────────────────────────────
        total_w = sum(d.weight for d in dims)
        total_s = (
            sum(d.score * d.weight for d in dims) / total_w
            if total_w > 0 else 0.0
        )
        grade = FactorScore.grade_from_score(total_s)

        return FactorScore(
            vt_symbol=ic_stats.vt_symbol,
            factor_name=ic_stats.factor_name,
            dimensions=dims,
            total_score=total_s,
            grade=grade,
        )

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _calc_ls_sharpe(qr: QuantileResult | None) -> float:
        if qr is None:
            return float("nan")
        ls = qr.long_short_series
        if ls is None or ls.empty:
            return float("nan")
        nav = (1 + ls.dropna()).values
        if len(nav) < 3:
            return float("nan")
        r   = np.diff(nav) / np.maximum(nav[:-1], 1e-12)
        std = float(np.std(r, ddof=1))
        if std < 1e-12:
            return float("nan")
        ann_factor = math.sqrt(_TRADING_DAYS / max(qr.lag, 1))
        return float(np.mean(r)) / std * ann_factor

    @staticmethod
    def _calc_ls_mdd(qr: QuantileResult | None) -> float:
        if qr is None:
            return float("nan")
        ls = qr.long_short_series
        if ls is None or ls.empty:
            return float("nan")
        nav = (1 + ls.dropna()).values
        if len(nav) < 2:
            return float("nan")
        peak = np.maximum.accumulate(nav)
        return float(np.min((nav - peak) / np.maximum(peak, 1e-12)))
