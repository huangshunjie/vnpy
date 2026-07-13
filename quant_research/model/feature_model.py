"""
quant_research/model/feature_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from ..constant import FeatureStatus


@dataclass
class ICRecord:
    """单次 IC 评估记录。"""
    eval_id:    str     = ""
    ic:         float   = 0.0
    rank_ic:    float   = 0.0
    ir:         float   = 0.0
    icir:       float   = 0.0
    coverage:   float   = 0.0
    period:     str     = ""        # 评估周期，如 "2024Q1"
    dataset_id: str     = ""
    evaluated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "eval_id":  self.eval_id,
            "ic":       round(self.ic, 6),
            "rank_ic":  round(self.rank_ic, 6),
            "ir":       round(self.ir, 6),
            "icir":     round(self.icir, 6),
            "coverage": round(self.coverage, 4),
            "period":   self.period,
        }


@dataclass
class FeatureRecord:
    feature_id:       str              = ""
    name:             str              = ""
    version:          str              = "v1.0"
    description:      str              = ""
    status:           FeatureStatus    = FeatureStatus.EXPERIMENTAL
    category:         str              = ""       # momentum / value / quality / technical / alternative
    author:           str              = ""
    formula:          str              = ""       # 计算公式 / 代码描述
    ic:               float            = 0.0
    rank_ic:          float            = 0.0
    ir:               float            = 0.0
    icir:             float            = 0.0
    coverage:         float            = 0.0
    ic_history:       List[ICRecord]   = field(default_factory=list)
    dependencies:     List[str]        = field(default_factory=list)   # 上游因子 ID
    dataset_ids:      List[str]        = field(default_factory=list)   # 依赖数据集
    tags:             List[str]        = field(default_factory=list)
    created_at:       datetime         = field(default_factory=datetime.now)
    updated_at:       datetime         = field(default_factory=datetime.now)
    published_at:     Optional[datetime] = None
    deprecated_at:    Optional[datetime] = None
    deprecated_reason: str             = ""
    created_by:       str              = ""
    metadata:         Dict             = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "feature_id":  self.feature_id,
            "name":        self.name,
            "version":     self.version,
            "status":      self.status.value,
            "category":    self.category,
            "author":      self.author,
            "ic":          round(self.ic, 6),
            "rank_ic":     round(self.rank_ic, 6),
            "ir":          round(self.ir, 6),
            "icir":        round(self.icir, 6),
            "coverage":    round(self.coverage, 4),
            "tags":        self.tags,
            "created_at":  self.created_at.isoformat(),
            "updated_at":  self.updated_at.isoformat(),
            "deprecated":  self.deprecated_at is not None,
        }
