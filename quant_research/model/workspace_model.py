"""
quant_research/model/workspace_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from ..constant import WorkspaceStatus


@dataclass
class ProjectRecord:
    project_id:     str             = ""
    name:           str             = ""
    description:    str             = ""
    workspace_id:   str             = ""
    experiment_ids: List[str]       = field(default_factory=list)
    tags:           List[str]       = field(default_factory=list)
    starred:        bool            = False
    created_at:     datetime        = field(default_factory=datetime.now)
    updated_at:     datetime        = field(default_factory=datetime.now)
    created_by:     str             = ""

    def to_dict(self) -> dict:
        return {
            "project_id":  self.project_id,
            "name":        self.name,
            "workspace_id": self.workspace_id,
            "starred":     self.starred,
            "created_at":  self.created_at.isoformat(),
        }


@dataclass
class WorkspaceRecord:
    workspace_id:   str             = ""
    name:           str             = ""
    description:    str             = ""
    status:         WorkspaceStatus = WorkspaceStatus.ACTIVE
    root_path:      str             = ""
    project_ids:    List[str]       = field(default_factory=list)
    members:        List[str]       = field(default_factory=list)
    tags:           List[str]       = field(default_factory=list)
    created_at:     datetime        = field(default_factory=datetime.now)
    updated_at:     datetime        = field(default_factory=datetime.now)
    created_by:     str             = ""
    active_project: Optional[str]   = None

    def to_dict(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "name":         self.name,
            "status":       self.status.value,
            "root_path":    self.root_path,
            "created_at":   self.created_at.isoformat(),
        }
