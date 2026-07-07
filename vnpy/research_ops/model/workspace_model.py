"""
research_ops/model/workspace_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from ..constant import WorkspaceStatus, ProjectStatus


@dataclass
class FolderRecord:
    folder_id:   str       = ""
    name:        str       = ""
    parent_id:   str       = ""
    project_id:  str       = ""
    description: str       = ""
    color:       str       = "#6c757d"
    created_at:  datetime  = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {"folder_id": self.folder_id, "name": self.name,
                "parent_id": self.parent_id, "project_id": self.project_id}


@dataclass
class ProjectRecord:
    project_id:     str           = ""
    workspace_id:   str           = ""
    name:           str           = ""
    description:    str           = ""
    status:         ProjectStatus = ProjectStatus.ACTIVE
    starred:        bool          = False
    color:          str           = "#4a6cf7"
    tags:           List[str]     = field(default_factory=list)
    folder_ids:     List[str]     = field(default_factory=list)
    experiment_ids: List[str]     = field(default_factory=list)
    dataset_ids:    List[str]     = field(default_factory=list)
    feature_ids:    List[str]     = field(default_factory=list)
    strategy_ids:   List[str]     = field(default_factory=list)
    model_ids:      List[str]     = field(default_factory=list)
    created_at:     datetime      = field(default_factory=datetime.now)
    updated_at:     datetime      = field(default_factory=datetime.now)
    created_by:     str           = ""

    def to_dict(self) -> dict:
        return {
            "project_id":   self.project_id,
            "workspace_id": self.workspace_id,
            "name":         self.name,
            "status":       self.status.value,
            "starred":      self.starred,
            "tags":         self.tags,
            "created_at":   self.created_at.isoformat(),
        }


@dataclass
class WorkspaceRecord:
    workspace_id: str             = ""
    name:         str             = ""
    description:  str             = ""
    status:       WorkspaceStatus = WorkspaceStatus.ACTIVE
    root_path:    str             = ""
    members:      List[str]       = field(default_factory=list)
    tags:         List[str]       = field(default_factory=list)
    project_ids:  List[str]       = field(default_factory=list)
    active_project_id: Optional[str] = None
    created_at:   datetime        = field(default_factory=datetime.now)
    updated_at:   datetime        = field(default_factory=datetime.now)
    created_by:   str             = ""

    def to_dict(self) -> dict:
        return {
            "workspace_id": self.workspace_id,
            "name":         self.name,
            "status":       self.status.value,
            "root_path":    self.root_path,
            "members":      self.members,
            "created_at":   self.created_at.isoformat(),
        }
