"""
research_ops/model/pipeline_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import PipelineStatus, NodeStatus, NodeType, TriggerType


@dataclass
class DAGNode:
    node_id:      str            = ""
    pipeline_id:  str            = ""
    name:         str            = ""
    node_type:    NodeType       = NodeType.CUSTOM
    status:       NodeStatus     = NodeStatus.IDLE
    depends_on:   List[str]      = field(default_factory=list)
    params:       Dict[str, Any] = field(default_factory=dict)
    retries:      int            = 0
    max_retries:  int            = 3
    timeout_sec:  int            = 3600
    log:          str            = ""
    error_msg:    str            = ""
    order:        int            = 0
    started_at:   Optional[datetime] = None
    finished_at:  Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "node_id":    self.node_id,
            "name":       self.name,
            "node_type":  self.node_type.value,
            "status":     self.status.value,
            "depends_on": self.depends_on,
            "order":      self.order,
        }


@dataclass
class PipelineRunRecord:
    run_id:       str          = ""
    pipeline_id:  str          = ""
    trigger:      TriggerType  = TriggerType.MANUAL
    status:       str          = "running"
    triggered_by: str          = ""
    duration_sec: float        = 0.0
    node_logs:    Dict[str, str] = field(default_factory=dict)
    error_msg:    str          = ""
    started_at:   datetime     = field(default_factory=datetime.now)
    finished_at:  Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "run_id":      self.run_id,
            "pipeline_id": self.pipeline_id,
            "trigger":     self.trigger.value,
            "status":      self.status,
            "duration_sec": round(self.duration_sec, 2),
            "started_at":  self.started_at.isoformat(),
        }


@dataclass
class PipelineRecord:
    pipeline_id:   str            = ""
    project_id:    str            = ""
    name:          str            = ""
    description:   str            = ""
    status:        PipelineStatus = PipelineStatus.IDLE
    schedule:      str            = ""
    author:        str            = ""
    nodes:         List[DAGNode]  = field(default_factory=list)
    runs:          List[PipelineRunRecord] = field(default_factory=list)
    tags:          List[str]      = field(default_factory=list)
    run_count:     int            = 0
    success_count: int            = 0
    fail_count:    int            = 0
    last_run_at:   Optional[datetime] = None
    created_at:    datetime       = field(default_factory=datetime.now)
    updated_at:    datetime       = field(default_factory=datetime.now)
    created_by:    str            = ""

    def to_dict(self) -> dict:
        return {
            "pipeline_id":  self.pipeline_id,
            "name":         self.name,
            "status":       self.status.value,
            "node_count":   len(self.nodes),
            "run_count":    self.run_count,
            "success_count": self.success_count,
            "fail_count":   self.fail_count,
            "schedule":     self.schedule,
            "created_at":   self.created_at.isoformat(),
        }
