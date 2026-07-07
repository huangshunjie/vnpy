"""
quant_research/model/model_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import ModelStatus

MODEL_TYPES = [
    "lightgbm", "xgboost", "catboost",
    "lstm", "transformer", "gru",
    "linear", "ridge", "lasso",
    "random_forest", "svm", "custom",
]


@dataclass
class TrainingRun:
    run_id:       str             = ""
    model_id:     str             = ""
    run_note:     str             = ""
    hyperparams:  Dict[str, Any]  = field(default_factory=dict)
    metrics:      Dict[str, float] = field(default_factory=dict)
    dataset_id:   str             = ""
    duration_sec: float           = 0.0
    started_at:   datetime        = field(default_factory=datetime.now)
    finished_at:  Optional[datetime] = None
    created_by:   str             = ""

    def to_dict(self) -> dict:
        return {
            "run_id":       self.run_id,
            "model_id":     self.model_id,
            "run_note":     self.run_note,
            "metrics":      {k: round(v, 6) for k, v in self.metrics.items()},
            "duration_sec": round(self.duration_sec, 2),
            "started_at":   self.started_at.isoformat(),
        }


@dataclass
class MLModelRecord:
    model_id:       str            = ""
    name:           str            = ""
    version:        str            = "v1.0"
    description:    str            = ""
    status:         ModelStatus    = ModelStatus.TRAINING
    model_type:     str            = ""
    author:         str            = ""
    model_path:     str            = ""
    config_path:    str            = ""

    # 评估指标
    accuracy:       float          = 0.0
    auc:            float          = 0.0
    rmse:           float          = 0.0
    mae:            float          = 0.0
    f1:             float          = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)

    # 超参数
    hyperparams:    Dict[str, Any] = field(default_factory=dict)

    # 部署信息
    deploy_env:     str            = ""
    deploy_at:      Optional[datetime] = None
    endpoint:       str            = ""

    # 训练历史
    training_runs:  List[TrainingRun] = field(default_factory=list)

    # 关联
    feature_ids:    List[str]      = field(default_factory=list)
    dataset_ids:    List[str]      = field(default_factory=list)
    strategy_ids:   List[str]      = field(default_factory=list)
    experiment_ids: List[str]      = field(default_factory=list)

    tags:           List[str]      = field(default_factory=list)
    created_at:     datetime       = field(default_factory=datetime.now)
    updated_at:     datetime       = field(default_factory=datetime.now)
    retired_at:     Optional[datetime] = None
    created_by:     str            = ""
    framework:      str            = ""   # e.g. "sklearn 1.4", "torch 2.2"

    def to_dict(self) -> dict:
        return {
            "model_id":    self.model_id,
            "name":        self.name,
            "version":     self.version,
            "status":      self.status.value,
            "model_type":  self.model_type,
            "author":      self.author,
            "accuracy":    round(self.accuracy, 6),
            "auc":         round(self.auc, 6),
            "f1":          round(self.f1, 6),
            "tags":        self.tags,
            "created_at":  self.created_at.isoformat(),
            "updated_at":  self.updated_at.isoformat(),
        }
