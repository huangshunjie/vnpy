"""
quant_research/registry/workspace_registry.py  — Phase 10 完整实现
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from ..model.workspace_model import WorkspaceRecord, ProjectRecord
from ..constant import WorkspaceStatus


class WorkspaceRegistry:
    def __init__(self) -> None:
        self._workspaces: Dict[str, WorkspaceRecord] = {}
        self._projects:   Dict[str, ProjectRecord]   = {}
        self._active_workspace_id: Optional[str]     = None

    # ------------------------------------------------------------------
    # Workspace CRUD
    # ------------------------------------------------------------------

    def create_workspace(self, record: WorkspaceRecord) -> WorkspaceRecord:
        self._workspaces[record.workspace_id] = record
        if self._active_workspace_id is None:
            self._active_workspace_id = record.workspace_id
        return record

    def get_workspace(self, workspace_id: str) -> Optional[WorkspaceRecord]:
        return self._workspaces.get(workspace_id)

    def list_workspaces(self) -> List[WorkspaceRecord]:
        return list(self._workspaces.values())

    def update_workspace(self, record: WorkspaceRecord) -> None:
        record.updated_at = datetime.now()
        self._workspaces[record.workspace_id] = record

    def delete_workspace(self, workspace_id: str) -> None:
        self._workspaces.pop(workspace_id, None)
        if self._active_workspace_id == workspace_id:
            remaining = list(self._workspaces.keys())
            self._active_workspace_id = remaining[0] if remaining else None

    # ------------------------------------------------------------------
    # 活跃 Workspace
    # ------------------------------------------------------------------

    def get_active(self) -> Optional[WorkspaceRecord]:
        if self._active_workspace_id:
            return self._workspaces.get(self._active_workspace_id)
        return None

    def set_active(self, workspace_id: str) -> None:
        if workspace_id in self._workspaces:
            self._active_workspace_id = workspace_id

    # ------------------------------------------------------------------
    # Workspace 成员管理
    # ------------------------------------------------------------------

    def add_member(self, workspace_id: str, member: str) -> None:
        ws = self._workspaces.get(workspace_id)
        if ws and member not in ws.members:
            ws.members.append(member)
            ws.updated_at = datetime.now()

    def remove_member(self, workspace_id: str, member: str) -> None:
        ws = self._workspaces.get(workspace_id)
        if ws and member in ws.members:
            ws.members.remove(member)
            ws.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # Workspace 状态
    # ------------------------------------------------------------------

    def archive_workspace(self, workspace_id: str) -> None:
        ws = self._workspaces.get(workspace_id)
        if ws:
            ws.status     = WorkspaceStatus.ARCHIVED
            ws.updated_at = datetime.now()

    def activate_workspace(self, workspace_id: str) -> None:
        ws = self._workspaces.get(workspace_id)
        if ws:
            ws.status     = WorkspaceStatus.ACTIVE
            ws.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # Project CRUD
    # ------------------------------------------------------------------

    def create_project(self, record: ProjectRecord) -> ProjectRecord:
        self._projects[record.project_id] = record
        ws = self._workspaces.get(record.workspace_id)
        if ws and record.project_id not in ws.project_ids:
            ws.project_ids.append(record.project_id)
            ws.updated_at = datetime.now()
        return record

    def get_project(self, project_id: str) -> Optional[ProjectRecord]:
        return self._projects.get(project_id)

    def list_projects(
        self, workspace_id: Optional[str] = None
    ) -> List[ProjectRecord]:
        if workspace_id:
            return [p for p in self._projects.values()
                    if p.workspace_id == workspace_id]
        return list(self._projects.values())

    def update_project(self, record: ProjectRecord) -> None:
        record.updated_at = datetime.now()
        self._projects[record.project_id] = record

    def delete_project(self, project_id: str) -> None:
        proj = self._projects.pop(project_id, None)
        if proj:
            ws = self._workspaces.get(proj.workspace_id)
            if ws and project_id in ws.project_ids:
                ws.project_ids.remove(project_id)
                ws.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # Project 操作
    # ------------------------------------------------------------------

    def star_project(self, project_id: str) -> None:
        proj = self._projects.get(project_id)
        if proj:
            proj.starred    = True
            proj.updated_at = datetime.now()

    def unstar_project(self, project_id: str) -> None:
        proj = self._projects.get(project_id)
        if proj:
            proj.starred    = False
            proj.updated_at = datetime.now()

    def link_experiment(self, project_id: str, experiment_id: str) -> None:
        proj = self._projects.get(project_id)
        if proj and experiment_id not in proj.experiment_ids:
            proj.experiment_ids.append(experiment_id)
            proj.updated_at = datetime.now()

    def unlink_experiment(self, project_id: str, experiment_id: str) -> None:
        proj = self._projects.get(project_id)
        if proj and experiment_id in proj.experiment_ids:
            proj.experiment_ids.remove(experiment_id)
            proj.updated_at = datetime.now()

    def search_projects(self, keyword: str) -> List[ProjectRecord]:
        kw = keyword.lower()
        return [
            p for p in self._projects.values()
            if kw in p.name.lower()
            or kw in p.description.lower()
            or any(kw in t.lower() for t in p.tags)
        ]

    def get_starred(self) -> List[ProjectRecord]:
        return [p for p in self._projects.values() if p.starred]

    # ------------------------------------------------------------------
    # 清理
    # ------------------------------------------------------------------

    def clear(self) -> None:
        self._workspaces.clear()
        self._projects.clear()
        self._active_workspace_id = None
