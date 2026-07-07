"""
research_ops/model/experiment_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import ExperimentStatus, RunStatus, ArtifactType


@dataclass
class MetricPoint:
    """单个指标记录点（支持多步骤时序）。"""
    key:       str      = ""
    value:     float    = 0.0
    step:      int      = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ArtifactRef:
    """实验产出物引用（轻量，指向 Artifact Center）。"""
    artifact_id:   str          = ""
    name:          str          = ""
    artifact_type: ArtifactType = ArtifactType.OTHER
    file_path:     str          = ""
    size_kb:       float        = 0.0
    created_at:    datetime     = field(default_factory=datetime.now)


@dataclass
class RunRecord:
    """单次实验运行。"""
    run_id:        str              = ""
    experiment_id: str              = ""
    name:          str              = ""
    status:        RunStatus        = RunStatus.PENDING
    params:        Dict[str, Any]   = field(default_factory=dict)
    metrics:       Dict[str, float] = field(default_factory=dict)
    metric_history: List[MetricPoint] = field(default_factory=list)
    tags:          List[str]        = field(default_factory=list)
    artifacts:     List[ArtifactRef] = field(default_factory=list)
    git_commit:    str              = ""
    data_version:  str              = ""
    note:          str              = ""
    error_msg:     str              = ""
    duration_sec:  float            = 0.0
    started_at:    Optional[datetime] = None
    finished_at:   Optional[datetime] = None
    created_at:    datetime         = field(default_factory=datetime.now)
    created_by:    str              = ""

    def to_dict(self) -> dict:
        return {
            "run_id":       self.run_id,
            "experiment_id": self.experiment_id,
            "name":         self.name,
            "status":       self.status.value,
            "git_commit":   self.git_commit,
            "data_version": self.data_version,
            "duration_sec": round(self.duration_sec, 2),
            "created_at":   self.created_at.isoformat(),
        }


@dataclass
class ExperimentRecord:
    experiment_id: str              = ""
    project_id:    str              = ""
    workspace_id:  str              = ""
    name:          str              = ""
    description:   str              = ""
    status:        ExperimentStatus = ExperimentStatus.DRAFT
    hypothesis:    str              = ""
    objective:     str              = ""
    tags:          List[str]        = field(default_factory=list)
    run_ids:       List[str]        = field(default_factory=list)
    best_run_id:   Optional[str]    = None
    primary_metric: str             = ""
    git_repo:      str              = ""
    note:          str              = ""
    created_at:    datetime         = field(default_factory=datetime.now)
    updated_at:    datetime         = field(default_factory=datetime.now)
    created_by:    str              = ""

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "project_id":    self.project_id,
            "name":          self.name,
            "status":        self.status.value,
            "run_count":     len(self.run_ids),
            "best_run_id":   self.best_run_id,
            "primary_metric": self.primary_metric,
            "created_at":    self.created_at.isoformat(),
        }
