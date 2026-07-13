"""
portfolio_engine/engine/factor_bridge.py

FactorBridge — FactorResearch ↔ PortfolioEngine 桥接层（Phase 4）。

职责：
  1. 从 FactorResearch 引擎（或其事件 payload）中提取 IcStats / FactorScore
  2. 通过 factor_utils 把信号映射为权重
  3. 构造 FactorSignal 供 dispatcher 使用
  4. 管理信号缓存（last_signal），供 AllocationEngine 在 FACTOR_DRIVEN 模式下消费

耦合隔离原则：
  - 对 factor_research 包的 import 全部用 try/except 包裹
  - 若 factor_research 不可用，优雅降级（返回等权）
  - AllocationEngine / dispatcher 无需关心 factor_research 的内部结构
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import TYPE_CHECKING

import pandas as pd

from ..model.factor_signal_model import FactorSignal
from ..utils.factor_utils import (
    ic_to_weights,
    factor_score_to_weights,
    rank_ic_weights,
    blend_factor_weights,
)

if TYPE_CHECKING:
    from ..model.portfolio_model import Portfolio


class FactorBridge:
    """
    FactorResearch ↔ PortfolioEngine 桥接层（无状态计算 + 信号缓存）。

    使用方式：
        bridge = FactorBridge()
        bridge.ingest_ic_stats(ic_stats, symbols)   # 收到因子研究结果时调用
        signal = bridge.last_signal                  # dispatcher 取信号
    """

    _ICIR_MIN: float = 0.3    # 低于此 ICIR 时信号强度 → 0（不采纳）
    _ICIR_HIGH: float = 2.0   # 高于此 ICIR 时信号强度 → 1（满仓采纳）

    def __init__(self) -> None:
        self._last_signal: FactorSignal | None = None
        self._blend_ratio: float = 0.6         # IC 权重 vs 评分权重混合比

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def ingest_ic_stats(
        self,
        ic_stats,                  # factor_research.model.IcStats
        symbols: list[str],
        method: str = "rank",
    ) -> FactorSignal:
        """
        消化 IcStats，生成 FactorSignal。

        Parameters
        ----------
        ic_stats : IcStats（来自 IcEngine.compute()）
        symbols  : 参与组合的合约列表
        method   : "rank" / "score" / "blend"

        Returns
        -------
        FactorSignal（已写入 self._last_signal）
        """
        signal = FactorSignal(
            factor_name=getattr(ic_stats, "factor_name", "unknown"),
            generated_at=datetime.now(),
        )

        ic_mean    = getattr(ic_stats, "ic_mean",    float("nan"))
        rank_ic    = getattr(ic_stats, "rank_ic_mean", float("nan"))
        icir       = getattr(ic_stats, "icir",       float("nan"))
        rank_icir  = getattr(ic_stats, "rank_icir",  float("nan"))

        signal.ic_mean      = ic_mean
        signal.rank_ic_mean = rank_ic
        signal.icir         = icir
        signal.rank_icir    = rank_icir

        # 信号强度：用 ICIR 插值
        signal.signal_strength = self._compute_signal_strength(icir, rank_icir)

        # 若信号强度过低，直接返回空权重（等权退回由 AllocationEngine 处理）
        if signal.signal_strength < 0.05:
            signal.is_valid = False
            self._last_signal = signal
            return signal

        # 构造截面 IC（用 rank_ic_series 最后一期；若无则用 ic_mean 标量广播）
        cross_ic = self._extract_cross_section(ic_stats, symbols)
        signal.cross_section_ic = cross_ic

        # 计算建议权重
        if method == "rank":
            weights = rank_ic_weights(cross_ic) if cross_ic else {}
        elif method == "score":
            weights = ic_to_weights(
                pd.Series(cross_ic), symbols, method="score"
            ) if cross_ic else {}
        else:
            # blend：rank_ic_weights + ic_to_weights score 混合
            w_rank  = rank_ic_weights(cross_ic) if cross_ic else {}
            w_score = ic_to_weights(pd.Series(cross_ic), symbols, method="score") \
                if cross_ic else {}
            weights = blend_factor_weights(w_rank, w_score, self._blend_ratio) \
                if (w_rank or w_score) else {}

        # 等权兜底
        if not weights and symbols:
            n = len(symbols)
            weights = {s: 1.0 / n for s in symbols}

        signal.suggested_weights = weights
        signal.is_valid = True
        self._last_signal = signal
        return signal

    def ingest_factor_scores(
        self,
        factor_scores: dict[str, float],
        symbols: list[str],
        long_quantile: float = 0.8,
        long_only: bool = True,
    ) -> FactorSignal:
        """
        消化截面因子评分（0~100 字典），生成 FactorSignal。

        Parameters
        ----------
        factor_scores  : {symbol: score(0~100)}
        symbols        : 参与组合的合约子集
        long_quantile  : 做多分位数阈值
        long_only      : 是否仅做多
        """
        signal = FactorSignal(
            factor_name="factor_score",
            generated_at=datetime.now(),
        )

        subset_scores = {s: factor_scores[s] for s in symbols if s in factor_scores}
        if not subset_scores:
            signal.is_valid = False
            self._last_signal = signal
            return signal

        signal.cross_section_score = subset_scores
        weights = factor_score_to_weights(
            subset_scores,
            long_quantile=long_quantile,
            long_only=long_only,
        )

        if not weights:
            n = len(symbols)
            weights = {s: 1.0 / n for s in symbols}

        # 评分的信号强度：用分布集中度（高分集中 → 强信号）
        vals = list(subset_scores.values())
        if len(vals) >= 2:
            import numpy as np
            top20 = float(np.quantile(vals, 0.8))
            bot20 = float(np.quantile(vals, 0.2))
            spread = (top20 - bot20) / 100.0   # 0~1
            signal.signal_strength = min(spread * 2, 1.0)
        else:
            signal.signal_strength = 0.5

        signal.suggested_weights = weights
        signal.is_valid = True
        self._last_signal = signal
        return signal

    def get_weights_for_portfolio(
        self,
        portfolio: "Portfolio",
        fallback_equal: bool = True,
    ) -> dict[str, float]:
        """
        获取当前信号对应的合约权重。

        若无有效信号或信号强度不足，返回等权（fallback）。

        Parameters
        ----------
        portfolio      : 组合定义（用于获取合约列表）
        fallback_equal : True → 无信号时等权；False → 返回 {}

        Returns
        -------
        dict[str, float]  slot_name -> weight
        """
        slots = [s for s in portfolio.slots if s.enabled]
        if not slots:
            return {}

        slot_names = [s.name for s in slots]

        if self._last_signal is None or not self._last_signal.is_valid:
            if fallback_equal:
                n = len(slot_names)
                return {s: 1.0 / n for s in slot_names}
            return {}

        w = self._last_signal.suggested_weights
        if not w:
            if fallback_equal:
                n = len(slot_names)
                return {s: 1.0 / n for s in slot_names}
            return {}

        # 过滤仅属于此 portfolio 的槽位
        filtered = {s: w[s] for s in slot_names if s in w}
        if not filtered:
            if fallback_equal:
                n = len(slot_names)
                return {s: 1.0 / n for s in slot_names}
            return {}

        # 重新归一化（subset 可能不到 1）
        total = sum(filtered.values())
        if total < 1e-12:
            n = len(filtered)
            return {s: 1.0 / n for s in filtered}
        return {s: v / total for s, v in filtered.items()}

    # ------------------------------------------------------------------ #
    #  属性
    # ------------------------------------------------------------------ #

    @property
    def last_signal(self) -> FactorSignal | None:
        return self._last_signal

    def set_blend_ratio(self, ratio: float) -> None:
        """设置 IC 权重混合比例（0=全评分，1=全 IC 排名）。"""
        if not 0 <= ratio <= 1:
            raise ValueError(f"blend_ratio must be in [0, 1], got {ratio}")
        self._blend_ratio = ratio

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    def _compute_signal_strength(self, icir: float, rank_icir: float) -> float:
        """
        从 ICIR / RankICIR 派生信号强度（0~1）。

        取绝对值较大者（双重确认），线性插值到 [0, 1]。
        """
        vals = [v for v in (icir, rank_icir) if not math.isnan(v)]
        if not vals:
            return 0.0
        best = max(abs(v) for v in vals)
        if best <= self._ICIR_MIN:
            return 0.0
        if best >= self._ICIR_HIGH:
            return 1.0
        return (best - self._ICIR_MIN) / (self._ICIR_HIGH - self._ICIR_MIN)

    def _extract_cross_section(
        self,
        ic_stats,
        symbols: list[str],
    ) -> dict[str, float]:
        """
        从 IcStats 中提取截面 IC 快照。

        优先用 rank_ic_series 的最后一期；若为空则用 ic_mean 标量广播给所有 symbols。
        """
        rank_ic_series = getattr(ic_stats, "rank_ic_series", None)
        if rank_ic_series is not None and not rank_ic_series.empty:
            last_val = float(rank_ic_series.dropna().iloc[-1])
            if not math.isnan(last_val):
                # 标量广播：用同一 IC 值但加入微小噪声保持区分度
                # 真实多合约截面由 CrossSectionEngine 提供；此处单合约兼容处理
                return {s: last_val for s in symbols}

        ic_mean = getattr(ic_stats, "ic_mean", float("nan"))
        if not math.isnan(ic_mean):
            return {s: ic_mean for s in symbols}

        return {}
