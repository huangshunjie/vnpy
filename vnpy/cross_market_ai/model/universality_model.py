"""
cross_market_ai/model/universality_model.py

Phase 4: 普适性评分数据模型 — 完整字段定义。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DimensionScore:
    """单个评分维度的详细分解。"""
    name:        str   = ""
    score:       float = 0.0   # ∈ [0, 1]
    weight:      float = 0.0
    contribution: float = 0.0  # score × weight
    evidence:    str   = ""    # 评分依据说明

    def to_dict(self) -> dict:
        return {
            "name":         self.name,
            "score":        round(self.score, 4),
            "weight":       round(self.weight, 4),
            "contribution": round(self.contribution, 4),
            "evidence":     self.evidence,
        }


@dataclass
class MarketPerformanceSlice:
    """Alpha 在单个市场的性能切片（用于跨市场稳定性计算）。"""
    market_id:        str   = ""
    transfer_coeff:   float = 0.0
    ic_estimated:     float = 0.0
    ic_decay:         float = 0.0
    alignment_score:  float = 0.0
    portability_prior: float = 0.0
    is_transferable:  bool  = False

    def to_dict(self) -> dict:
        return {
            "market_id":        self.market_id,
            "transfer_coeff":   round(self.transfer_coeff,  4),
            "ic_estimated":     round(self.ic_estimated,    5),
            "ic_decay":         round(self.ic_decay,        4),
            "alignment_score":  round(self.alignment_score, 4),
            "portability_prior":round(self.portability_prior, 4),
            "is_transferable":  self.is_transferable,
        }


@dataclass
class UniversalityScoreRecord:
    """
    单次普适性评分完整记录。

    四个评分维度：
      1. cross_market_stability   — 跨市场稳定性
      2. regime_robustness        — Regime 鲁棒性
      3. structural_invariance    — 结构不变性
      4. execution_independence   — 执行独立性

    综合评分 ∈ [0, 1]，等级：UNIVERSAL / PORTABLE / LOCAL / FRAGILE
    """
    alpha_id:   str  = ""
    markets:    list = field(default_factory=list)

    # 四个维度评分对象
    dim_cross_market:   DimensionScore = field(default_factory=DimensionScore)
    dim_regime:         DimensionScore = field(default_factory=DimensionScore)
    dim_structural:     DimensionScore = field(default_factory=DimensionScore)
    dim_execution:      DimensionScore = field(default_factory=DimensionScore)

    # 各市场切片（用于稳定性计算来源）
    market_slices:      list = field(default_factory=list)  # list[MarketPerformanceSlice]

    # 统计指标
    n_markets_tested:      int   = 0
    n_markets_transferable: int  = 0
    avg_transfer_coeff:    float = 0.0
    transfer_coeff_std:    float = 0.0
    avg_alignment_score:   float = 0.0
    avg_ic_decay:          float = 0.0

    # 综合输出
    score:   float = 0.0   # ∈ [0, 1]
    grade:   str   = ""    # UNIVERSAL / PORTABLE / LOCAL / FRAGILE
    verdict: str   = ""    # 一句话结论

    status:    str = "computed"
    scored_at: str = ""

    def to_dict(self) -> dict:
        return {
            "alpha_id":               self.alpha_id,
            "markets":                self.markets,
            "dim_cross_market":       self.dim_cross_market.to_dict(),
            "dim_regime":             self.dim_regime.to_dict(),
            "dim_structural":         self.dim_structural.to_dict(),
            "dim_execution":          self.dim_execution.to_dict(),
            "market_slices":          [s.to_dict() for s in self.market_slices],
            "n_markets_tested":       self.n_markets_tested,
            "n_markets_transferable": self.n_markets_transferable,
            "avg_transfer_coeff":     round(self.avg_transfer_coeff,  4),
            "transfer_coeff_std":     round(self.transfer_coeff_std,  4),
            "avg_alignment_score":    round(self.avg_alignment_score, 4),
            "avg_ic_decay":           round(self.avg_ic_decay,        4),
            "score":                  round(self.score,               4),
            "grade":                  self.grade,
            "verdict":                self.verdict,
            "status":                 self.status,
            "scored_at":              self.scored_at,
        }


@dataclass
class UniversalityState:
    """普适性评分引擎运行状态。"""
    total_scored:    int   = 0
    avg_score:       float = 0.0
    top_alpha:       str   = ""
    top_score:       float = 0.0
    universal_count: int   = 0   # 达到 UNIVERSAL 等级的 Alpha 数量
    portable_count:  int   = 0
    local_count:     int   = 0
    fragile_count:   int   = 0
    status:          str   = "idle"

    def to_dict(self) -> dict:
        return {
            "total_scored":    self.total_scored,
            "avg_score":       round(self.avg_score, 4),
            "top_alpha":       self.top_alpha,
            "top_score":       round(self.top_score, 4),
            "universal_count": self.universal_count,
            "portable_count":  self.portable_count,
            "local_count":     self.local_count,
            "fragile_count":   self.fragile_count,
            "status":          self.status,
        }
