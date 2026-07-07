"""
quant_research/model/experiment_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import ExperimentStatus


@dataclass
class ExperimentRecord:
    experiment_id:  str                  = ""
    name:           str                  = ""
    description:    str                  = ""
    status:         ExperimentStatus     = ExperimentStatus.DRAFT
    tags:           List[str]            = field(default_factory=list)
    params:         Dict[str, Any]       = field(default_factory=dict)
    metrics:        Dict[str, float]     = field(default_factory=dict)
    notes:          str                  = ""
    starred:        bool                 = False
    created_at:     datetime             = field(default_factory=datetime.now)
    updated_at:     datetime             = field(default_factory=datetime.now)
    created_by:     str                  = ""
    parent_id:      Optional[str]        = None
    artifact_ids:   List[str]            = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "name":          self.name,
            "description":   self.description,
            "status":        self.status.value,
            "tags":          self.tags,
            "params":        self.params,
            "metrics":       self.metrics,
            "notes":         self.notes,
            "starred":       self.starred,
            "created_at":    self.created_at.isoformat(),
            "updated_at":    self.updated_at.isoformat(),
            "created_by":    self.created_by,
            "parent_id":     self.parent_id,
        }
