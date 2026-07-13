"""
research_ops/model/registry_model.py

Dataset / Feature / Strategy / Model 四类注册中心数据模型。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import (
    DatasetStatus, FeatureStatus, StrategyStatus, ModelStatus
)


# ─────────────────────────────────────────────────────────────────────
# Dataset Entry
# ─────────────────────────────────────────────────────────────────────

@dataclass
class DatasetVersion:
    version_id:    str      = ""
    dataset_id:    str      = ""
    version:       str      = "v1.0"
    row_count:     int      = 0
    size_mb:       float    = 0.0
    checksum:      str      = ""
    storage_path:  str      = ""
    note:          str      = ""
    created_at:    datetime = field(default_factory=datetime.now)
    created_by:    str      = ""


@dataclass
class DatasetEntry:
    dataset_id:     str           = ""
    name:           str           = ""
    version:        str           = "v1.0"
    description:    str           = ""
    status:         DatasetStatus = DatasetStatus.PENDING
    source:         str           = ""
    symbols:        List[str]     = field(default_factory=list)
    start_date:     str           = ""
    end_date:       str           = ""
    fields:         List[str]     = field(default_factory=list)
    row_count:      int           = 0
    size_mb:        float         = 0.0
    quality_score:  float         = 0.0
    storage_path:   str           = ""
    upstream_ids:   List[str]     = field(default_factory=list)
    versions:       List[DatasetVersion] = field(default_factory=list)
    tags:           List[str]     = field(default_factory=list)
    metadata:       Dict[str, Any] = field(default_factory=dict)
    created_at:     datetime      = field(default_factory=datetime.now)
    updated_at:     datetime      = field(default_factory=datetime.now)
    created_by:     str           = ""

    def to_dict(self) -> dict:
        return {
            "dataset_id":    self.dataset_id,
            "name":          self.name,
            "version":       self.version,
            "status":        self.status.value,
            "source":        self.source,
            "row_count":     self.row_count,
            "quality_score": round(self.quality_score, 4),
            "created_at":    self.created_at.isoformat(),
        }


# ─────────────────────────────────────────────────────────────────────
# Feature Entry
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ICRecord:
    record_id:  str      = ""
    feature_id: str      = ""
    period:     str      = ""
    ic:         float    = 0.0
    rank_ic:    float    = 0.0
    ir:         float    = 0.0
    icir:       float    = 0.0
    coverage:   float    = 0.0
    decay_5:    float    = 0.0
    decay_10:   float    = 0.0
    decay_20:   float    = 0.0
    universe:   str      = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class FeatureEntry:
    feature_id:   str           = ""
    name:         str           = ""
    version:      str           = "v1.0"
    description:  str           = ""
    status:       FeatureStatus = FeatureStatus.DRAFT
    category:     str           = ""
    author:       str           = ""
    formula:      str           = ""
    ic:           float         = 0.0
    rank_ic:      float         = 0.0
    ir:           float         = 0.0
    icir:         float         = 0.0
    coverage:     float         = 0.0
    dataset_ids:  List[str]     = field(default_factory=list)
    upstream_ids: List[str]     = field(default_factory=list)
    ic_history:   List[ICRecord] = field(default_factory=list)
    tags:         List[str]     = field(default_factory=list)
    git_commit:   str           = ""
    metadata:     Dict[str, Any] = field(default_factory=dict)
    created_at:   datetime      = field(default_factory=datetime.now)
    updated_at:   datetime      = field(default_factory=datetime.now)
    created_by:   str           = ""

    def to_dict(self) -> dict:
        return {
            "feature_id": self.feature_id,
            "name":       self.name,
            "version":    self.version,
            "status":     self.status.value,
            "ic":         round(self.ic, 4),
            "rank_ic":    round(self.rank_ic, 4),
            "icir":       round(self.icir, 4),
            "coverage":   round(self.coverage, 4),
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────────────────────────────────
# Strategy Entry
# ─────────────────────────────────────────────────────────────────────

@dataclass
class StrategyVersion:
    version_id:    str      = ""
    strategy_id:   str      = ""
    version:       str      = "v1.0"
    git_commit:    str      = ""
    params:        Dict[str, Any] = field(default_factory=dict)
    note:          str      = ""
    is_frozen:     bool     = False
    created_at:    datetime = field(default_factory=datetime.now)
    created_by:    str      = ""


@dataclass
class StrategyEntry:
    strategy_id:    str            = ""
    name:           str            = ""
    version:        str            = "v1.0"
    description:    str            = ""
    status:         StrategyStatus = StrategyStatus.IDEA
    author:         str            = ""
    annual_return:  float          = 0.0
    max_drawdown:   float          = 0.0
    sharpe:         float          = 0.0
    sortino:        float          = 0.0
    calmar:         float          = 0.0
    win_rate:       float          = 0.0
    feature_ids:    List[str]      = field(default_factory=list)
    dataset_ids:    List[str]      = field(default_factory=list)
    model_ids:      List[str]      = field(default_factory=list)
    backtest_ids:   List[str]      = field(default_factory=list)
    experiment_ids: List[str]      = field(default_factory=list)
    versions:       List[StrategyVersion] = field(default_factory=list)
    tags:           List[str]      = field(default_factory=list)
    git_commit:     str            = ""
    metadata:       Dict[str, Any] = field(default_factory=dict)
    created_at:     datetime       = field(default_factory=datetime.now)
    updated_at:     datetime       = field(default_factory=datetime.now)
    created_by:     str            = ""

    def to_dict(self) -> dict:
        return {
            "strategy_id":   self.strategy_id,
            "name":          self.name,
            "version":       self.version,
            "status":        self.status.value,
            "annual_return": round(self.annual_return, 4),
            "sharpe":        round(self.sharpe, 4),
            "max_drawdown":  round(self.max_drawdown, 4),
            "created_at":    self.created_at.isoformat(),
        }


# ─────────────────────────────────────────────────────────────────────
# Model Entry
# ─────────────────────────────────────────────────────────────────────

@dataclass
class TrainingRun:
    run_id:       str             = ""
    model_id:     str             = ""
    version:      str             = ""
    framework:    str             = ""
    hyperparams:  Dict[str, Any]  = field(default_factory=dict)
    metrics:      Dict[str, float] = field(default_factory=dict)
    dataset_id:   str             = ""
    duration_sec: float           = 0.0
    artifact_path: str            = ""
    note:         str             = ""
    created_at:   datetime        = field(default_factory=datetime.now)
    created_by:   str             = ""


@dataclass
class ModelEntry:
    model_id:     str         = ""
    name:         str         = ""
    version:      str         = "v1.0"
    description:  str         = ""
    status:       ModelStatus = ModelStatus.TRAINING
    model_type:   str         = ""
    framework:    str         = ""
    author:       str         = ""
    accuracy:     float       = 0.0
    auc:          float       = 0.0
    f1:           float       = 0.0
    hyperparams:  Dict[str, Any]  = field(default_factory=dict)
    feature_ids:  List[str]  = field(default_factory=list)
    dataset_ids:  List[str]  = field(default_factory=list)
    training_runs: List[TrainingRun] = field(default_factory=list)
    artifact_path: str        = ""
    deploy_env:   str         = ""
    deploy_endpoint: str      = ""
    git_commit:   str         = ""
    tags:         List[str]   = field(default_factory=list)
    metadata:     Dict[str, Any] = field(default_factory=dict)
    created_at:   datetime    = field(default_factory=datetime.now)
    updated_at:   datetime    = field(default_factory=datetime.now)
    created_by:   str         = ""

    def to_dict(self) -> dict:
        return {
            "model_id":    self.model_id,
            "name":        self.name,
            "version":     self.version,
            "status":      self.status.value,
            "model_type":  self.model_type,
            "framework":   self.framework,
            "accuracy":    round(self.accuracy, 4),
            "auc":         round(self.auc, 4),
            "created_at":  self.created_at.isoformat(),
        }
