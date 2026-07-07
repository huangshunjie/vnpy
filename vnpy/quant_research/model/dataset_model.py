"""
quant_research/model/dataset_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from ..constant import DatasetStatus


@dataclass
class DatasetSnapshot:
    snapshot_id:    str             = ""
    dataset_id:     str             = ""
    version:        str             = ""
    row_count:      int             = 0
    size_mb:        float           = 0.0
    fields:         List[str]       = field(default_factory=list)
    quality_score:  float           = 0.0
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    taken_at:       datetime        = field(default_factory=datetime.now)
    note:           str             = ""

    def to_dict(self) -> dict:
        return {
            "snapshot_id":   self.snapshot_id,
            "dataset_id":    self.dataset_id,
            "version":       self.version,
            "row_count":     self.row_count,
            "size_mb":       self.size_mb,
            "quality_score": round(self.quality_score, 4),
            "taken_at":      self.taken_at.isoformat(),
        }


@dataclass
class DatasetRecord:
    dataset_id:      str             = ""
    name:            str             = ""
    version:         str             = "v1.0"
    description:     str             = ""
    status:          DatasetStatus   = DatasetStatus.PENDING
    source:          str             = ""
    symbols:         List[str]       = field(default_factory=list)
    start_date:      str             = ""
    end_date:        str             = ""
    fields:          List[str]       = field(default_factory=list)
    row_count:       int             = 0
    size_mb:         float           = 0.0
    quality_score:   float           = 0.0
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    tags:            List[str]       = field(default_factory=list)
    dependencies:    List[str]       = field(default_factory=list)
    snapshots:       List[DatasetSnapshot] = field(default_factory=list)
    created_at:      datetime        = field(default_factory=datetime.now)
    updated_at:      datetime        = field(default_factory=datetime.now)
    created_by:      str             = ""
    snapshot_path:   Optional[str]   = None
    metadata:        Dict            = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "dataset_id":    self.dataset_id,
            "name":          self.name,
            "version":       self.version,
            "status":        self.status.value,
            "source":        self.source,
            "row_count":     self.row_count,
            "size_mb":       self.size_mb,
            "quality_score": round(self.quality_score, 4),
            "tags":          self.tags,
            "dependencies":  self.dependencies,
            "created_at":    self.created_at.isoformat(),
            "updated_at":    self.updated_at.isoformat(),
            "created_by":    self.created_by,
        }
