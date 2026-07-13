"""
cross_market_ai/model/regime_model.py

Phase 3: Regime 对齐数据模型 — 完整字段定义。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RegimeAlignmentRecord:
    """单次 Regime 对齐计算结果。"""
    market_a:          str   = ""
    market_b:          str   = ""

    # 分布相似度指标
    overlap_score:     float = 0.0   # Bhattacharyya 系数 ∈ [0,1]
    kl_divergence:     float = 0.0   # KL 散度（越小越相似）
    entropy_a:         float = 0.0
    entropy_b:         float = 0.0
    entropy_diff:      float = 0.0

    # 对齐结果
    aligned_regimes:   dict  = field(default_factory=dict)   # {regime_a: regime_b}
    unmatched_a:       list  = field(default_factory=list)   # 无法对齐的 A 状态
    unmatched_b:       list  = field(default_factory=list)   # 无法对齐的 B 状态

    # 状态稳定性对比
    persistence_a:     float = 0.0
    persistence_b:     float = 0.0
    persistence_gap:   float = 0.0

    # 综合对齐评分
    alignment_score:   float = 0.0   # ∈ [0,1]，越高越适合 Alpha 迁移
    is_alignable:      bool  = False
    status:            str   = "computed"
    aligned_at:        str   = ""

    def to_dict(self) -> dict:
        return {
            "market_a":        self.market_a,
            "market_b":        self.market_b,
            "overlap_score":   self.overlap_score,
            "kl_divergence":   self.kl_divergence,
            "entropy_a":       self.entropy_a,
            "entropy_b":       self.entropy_b,
            "entropy_diff":    self.entropy_diff,
            "aligned_regimes": self.aligned_regimes,
            "unmatched_a":     self.unmatched_a,
            "unmatched_b":     self.unmatched_b,
            "persistence_a":   self.persistence_a,
            "persistence_b":   self.persistence_b,
            "persistence_gap": self.persistence_gap,
            "alignment_score": self.alignment_score,
            "is_alignable":    self.is_alignable,
            "status":          self.status,
            "aligned_at":      self.aligned_at,
        }


@dataclass
class RegimeAlignmentState:
    """Regime 对齐引擎运行状态。"""
    total_alignments: int   = 0
    successful:       int   = 0
    failed:           int   = 0
    avg_alignment:    float = 0.0
    last_pair:        str   = ""
    status:           str   = "idle"

    def to_dict(self) -> dict:
        return {
            "total_alignments": self.total_alignments,
            "successful":       self.successful,
            "failed":           self.failed,
            "avg_alignment":    round(self.avg_alignment, 4),
            "last_pair":        self.last_pair,
            "status":           self.status,
        }
