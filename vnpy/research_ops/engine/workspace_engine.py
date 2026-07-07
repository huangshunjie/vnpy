"""
research_ops/engine/workspace_engine.py  — Phase 1 骨架
负责：Workspace / Project / Folder 的 CRUD、标签、收藏、全文搜索。
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from ..constant import WorkspaceStatus, ProjectStatus
from ..model.workspace_model import WorkspaceRecord, ProjectRecord, FolderRecord
from ..repository.memory import InMemoryRepository
from ..utils.id_gen import (
    gen_workspace_id, gen_project_id, gen_folder_id,
)


class WorkspaceEngine:
    def __init__(self) -> None:
        self._ws_repo:      InMemoryRepository = InMemoryRepository()
        self._proj_repo:    InMemoryRepository = InMemoryRepository()
        self._folder_repo:  InMemoryRepository = InMemoryRepository()
        self._active_ws_id: Optional[str]      = None

    # ------------------------------------------------------------------
    # Workspace
    # ------------------------------------------------------------------

    def create_workspace(
        self,
        name:        str,
        description: str       = "",
        root_path:   str       = "",
        members:     Optional[List[str]] = None,
        tags:        Optional[List[str]] = None,
        created_by:  str       = "",
    ) -> WorkspaceRecord:
        now = datetime.now()
        ws  = WorkspaceRecord(
            workspace_id = gen_workspace_id(),
            name         = name,
            description  = description,
            root_path    = root_path,
            members      = members or [],
            tags         = tags or [],
            created_by   = created_by,
            created_at   = now,
            updated_at   = now,
        )
        self._ws_repo.save(ws)
        if self._active_ws_id is None:
            self._active_ws_id = ws.workspace_id
        return ws

    def get_workspace(self, workspace_id: str) -> Optional[WorkspaceRecord]:
        return self._ws_repo.get(workspace_id)

    def list_workspaces(self) -> List[WorkspaceRecord]:
        return self._ws_repo.list()

    def update_workspace(self, ws: WorkspaceRecord) -> None:
        ws.updated_at = datetime.now()
        self._ws_repo.save(ws)

    def delete_workspace(self, workspace_id: str) -> None:
        self._ws_repo.delete(workspace_id)
        if self._active_ws_id == workspace_id:
            remaining = self._ws_repo.all_ids()
            self._active_ws_id = remaining[0] if remaining else None

    def get_active_workspace(self) -> Optional[WorkspaceRecord]:
        return self._ws_repo.get(self._active_ws_id) if self._active_ws_id else None

    def switch_workspace(self, workspace_id: str) -> bool:
        if self._ws_repo.exists(workspace_id):
            self._active_ws_id = workspace_id
            return True
        return False

    def archive_workspace(self, workspace_id: str) -> None:
        ws = self._ws_repo.get(workspace_id)
        if ws:
            ws.status     = WorkspaceStatus.ARCHIVED
            ws.updated_at = datetime.now()
            self._ws_repo.save(ws)

    # ------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------

    def create_project(
        self,
        name:         str,
        workspace_id: str              = "",
        description:  str              = "",
        tags:         Optional[List[str]] = None,
        created_by:   str              = "",
    ) -> ProjectRecord:
        if not workspace_id:
            ws = self.get_active_workspace()
            workspace_id = ws.workspace_id if ws else ""
        now  = datetime.now()
        proj = ProjectRecord(
            project_id   = gen_project_id(),
            workspace_id = workspace_id,
            name         = name,
            description  = description,
            tags         = tags or [],
            created_by   = created_by,
            created_at   = now,
            updated_at   = now,
        )
        self._proj_repo.save(proj)
        ws = self._ws_repo.get(workspace_id)
        if ws and proj.project_id not in ws.project_ids:
            ws.project_ids.append(proj.project_id)
            ws.updated_at = now
            self._ws_repo.save(ws)
        return proj

    def get_project(self, project_id: str) -> Optional[ProjectRecord]:
        return self._proj_repo.get(project_id)

    def list_projects(
        self, workspace_id: Optional[str] = None
    ) -> List[ProjectRecord]:
        if workspace_id:
            return self._proj_repo.query(workspace_id=workspace_id)
        return self._proj_repo.list()

    def update_project(self, proj: ProjectRecord) -> None:
        proj.updated_at = datetime.now()
        self._proj_repo.save(proj)

    def delete_project(self, project_id: str) -> None:
        proj = self._proj_repo.get(project_id)
        if proj:
            ws = self._ws_repo.get(proj.workspace_id)
            if ws and project_id in ws.project_ids:
                ws.project_ids.remove(project_id)
                self._ws_repo.save(ws)
        self._proj_repo.delete(project_id)

    def star_project(self, project_id: str) -> None:
        proj = self._proj_repo.get(project_id)
        if proj:
            proj.starred    = True
            proj.updated_at = datetime.now()
            self._proj_repo.save(proj)

    def unstar_project(self, project_id: str) -> None:
        proj = self._proj_repo.get(project_id)
        if proj:
            proj.starred    = False
            proj.updated_at = datetime.now()
            self._proj_repo.save(proj)

    def get_starred_projects(self) -> List[ProjectRecord]:
        return self._proj_repo.query(starred=True)

    def search_projects(self, keyword: str) -> List[ProjectRecord]:
        return self._proj_repo.search(
            keyword, fields=["name", "description", "tags"])

    def set_project_status(
        self, project_id: str, status: ProjectStatus
    ) -> None:
        proj = self._proj_repo.get(project_id)
        if proj:
            proj.status     = status
            proj.updated_at = datetime.now()
            self._proj_repo.save(proj)

    # ------------------------------------------------------------------
    # Folder
    # ------------------------------------------------------------------

    def create_folder(
        self,
        name:       str,
        project_id: str,
        parent_id:  str = "",
        description: str = "",
    ) -> FolderRecord:
        folder = FolderRecord(
            folder_id   = gen_folder_id(),
            name        = name,
            project_id  = project_id,
            parent_id   = parent_id,
            description = description,
        )
        self._folder_repo.save(folder)
        proj = self._proj_repo.get(project_id)
        if proj and folder.folder_id not in proj.folder_ids:
            proj.folder_ids.append(folder.folder_id)
            proj.updated_at = datetime.now()
            self._proj_repo.save(proj)
        return folder

    def list_folders(self, project_id: str) -> List[FolderRecord]:
        return self._folder_repo.query(project_id=project_id)

    def delete_folder(self, folder_id: str) -> None:
        folder = self._folder_repo.get(folder_id)
        if folder:
            proj = self._proj_repo.get(folder.project_id)
            if proj and folder_id in proj.folder_ids:
                proj.folder_ids.remove(folder_id)
                self._proj_repo.save(proj)
        self._folder_repo.delete(folder_id)

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        return {
            "workspaces": self._ws_repo.count(),
            "projects":   self._proj_repo.count(),
            "folders":    self._folder_repo.count(),
            "starred":    len(self.get_starred_projects()),
        }
