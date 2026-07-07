"""Patch engine.py: add Artifact + Workspace methods."""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\engine.py"
)
txt = P.read_text(encoding="utf-8")

# ── 1. imports ─────────────────────────────────────────────────────
txt = txt.replace(
    "from .model.pipeline_model import PipelineRecord, PipelineStepRecord, PipelineRun",
    "from .model.pipeline_model import PipelineRecord, PipelineStepRecord, PipelineRun\n"
    "from .model.artifact_model import ArtifactRecord\n"
    "from .model.workspace_model import WorkspaceRecord, ProjectRecord",
)

# ── 2. Artifact + Workspace methods ────────────────────────────────
METHODS = """
    # ------------------------------------------------------------------
    # Artifact Center — Phase 10
    # ------------------------------------------------------------------

    def _gen_artifact_id(self) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        key = f"ART-{date_str}"
        count = self._exp_counter.get(key, 0) + 1
        self._exp_counter[key] = count
        return f"ART-{date_str}-{count:03d}"

    def register_artifact(
        self,
        name:          str,
        artifact_type: "ArtifactType"           = None,
        description:   str                       = "",
        author:        str                       = "",
        file_path:     str                       = "",
        file_size_kb:  float                     = 0.0,
        checksum:      str                       = "",
        version:       str                       = "v1.0",
        experiment_id: Optional[str]             = None,
        pipeline_id:   Optional[str]             = None,
        strategy_id:   Optional[str]             = None,
        model_id:      Optional[str]             = None,
        backtest_id:   Optional[str]             = None,
        report_id:     Optional[str]             = None,
        tags:          Optional[List[str]]       = None,
        metadata:      Optional[Dict[str, Any]]  = None,
    ) -> ArtifactRecord:
        from .constant import ArtifactType as AT
        now = datetime.now()
        record = ArtifactRecord(
            artifact_id   = self._gen_artifact_id(),
            name          = name,
            artifact_type = artifact_type or AT.OTHER,
            description   = description,
            author        = author,
            file_path     = file_path,
            file_size_kb  = file_size_kb,
            checksum      = checksum,
            version       = version,
            experiment_id = experiment_id,
            pipeline_id   = pipeline_id,
            strategy_id   = strategy_id,
            model_id      = model_id,
            backtest_id   = backtest_id,
            report_id     = report_id,
            tags          = tags or [],
            metadata      = metadata or {},
            created_by    = author,
            created_at    = now,
            updated_at    = now,
        )
        self.artifact_registry.create(record)
        self._put(EVENT_ARTIFACT_CREATED, record)
        return record

    def update_artifact(self, record: ArtifactRecord) -> None:
        record.updated_at = datetime.now()
        self.artifact_registry.update(record)

    def delete_artifact(self, artifact_id: str) -> None:
        self.artifact_registry.delete(artifact_id)
        self._put(EVENT_ARTIFACT_DELETED, artifact_id)

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactRecord]:
        return self.artifact_registry.get(artifact_id)

    def list_artifacts(
        self,
        artifact_type: Optional["ArtifactType"] = None,
        tag:           Optional[str]             = None,
        author:        Optional[str]             = None,
        archived:      Optional[bool]            = None,
        experiment_id: Optional[str]             = None,
        pipeline_id:   Optional[str]             = None,
    ) -> List[ArtifactRecord]:
        return self.artifact_registry.filter(
            artifact_type=artifact_type, tag=tag, author=author,
            archived=archived, experiment_id=experiment_id,
            pipeline_id=pipeline_id,
        )

    def search_artifacts(self, keyword: str) -> List[ArtifactRecord]:
        return self.artifact_registry.search(keyword)

    def archive_artifact(self, artifact_id: str) -> None:
        self.artifact_registry.archive(artifact_id)

    def unarchive_artifact(self, artifact_id: str) -> None:
        self.artifact_registry.unarchive(artifact_id)

    def download_artifact(self, artifact_id: str) -> None:
        self.artifact_registry.increment_download(artifact_id)

    def artifact_total_size_kb(self) -> float:
        return self.artifact_registry.total_size_kb()

    def artifact_type_counts(self) -> Dict:
        return self.artifact_registry.type_counts()

    # ------------------------------------------------------------------
    # Workspace Manager — Phase 10
    # ------------------------------------------------------------------

    def _gen_workspace_id(self) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        key = f"WS-{date_str}"
        count = self._exp_counter.get(key, 0) + 1
        self._exp_counter[key] = count
        return f"WS-{date_str}-{count:03d}"

    def _gen_project_id(self) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        key = f"PRJ-{date_str}"
        count = self._exp_counter.get(key, 0) + 1
        self._exp_counter[key] = count
        return f"PRJ-{date_str}-{count:03d}"

    def create_workspace(
        self,
        name:        str,
        description: str              = "",
        root_path:   str              = "",
        members:     Optional[List[str]] = None,
        tags:        Optional[List[str]] = None,
        created_by:  str              = "",
    ) -> WorkspaceRecord:
        from .constant import WorkspaceStatus
        now = datetime.now()
        record = WorkspaceRecord(
            workspace_id = self._gen_workspace_id(),
            name         = name,
            description  = description,
            root_path    = root_path,
            members      = members or [],
            tags         = tags or [],
            created_by   = created_by,
            created_at   = now,
            updated_at   = now,
        )
        self.workspace_registry.create_workspace(record)
        self._put(EVENT_WORKSPACE_SWITCHED, record)
        return record

    def update_workspace(self, record: WorkspaceRecord) -> None:
        self.workspace_registry.update_workspace(record)

    def delete_workspace(self, workspace_id: str) -> None:
        self.workspace_registry.delete_workspace(workspace_id)

    def get_workspace(self, workspace_id: str) -> Optional[WorkspaceRecord]:
        return self.workspace_registry.get_workspace(workspace_id)

    def list_workspaces(self) -> List[WorkspaceRecord]:
        return self.workspace_registry.list_workspaces()

    def get_active_workspace(self) -> Optional[WorkspaceRecord]:
        return self.workspace_registry.get_active()

    def switch_workspace(self, workspace_id: str) -> None:
        self.workspace_registry.set_active(workspace_id)
        record = self.workspace_registry.get_workspace(workspace_id)
        if record:
            self._put(EVENT_WORKSPACE_SWITCHED, record)

    def archive_workspace(self, workspace_id: str) -> None:
        self.workspace_registry.archive_workspace(workspace_id)

    def add_workspace_member(self, workspace_id: str, member: str) -> None:
        self.workspace_registry.add_member(workspace_id, member)

    def remove_workspace_member(self, workspace_id: str, member: str) -> None:
        self.workspace_registry.remove_member(workspace_id, member)

    def create_project(
        self,
        name:         str,
        workspace_id: str              = "",
        description:  str              = "",
        tags:         Optional[List[str]] = None,
        created_by:   str              = "",
    ) -> ProjectRecord:
        now = datetime.now()
        if not workspace_id:
            ws = self.workspace_registry.get_active()
            workspace_id = ws.workspace_id if ws else ""
        record = ProjectRecord(
            project_id   = self._gen_project_id(),
            name         = name,
            description  = description,
            workspace_id = workspace_id,
            tags         = tags or [],
            created_by   = created_by,
            created_at   = now,
            updated_at   = now,
        )
        self.workspace_registry.create_project(record)
        self._put(EVENT_PROJECT_CREATED, record)
        return record

    def update_project(self, record: ProjectRecord) -> None:
        self.workspace_registry.update_project(record)
        self._put(EVENT_PROJECT_UPDATED, record)

    def delete_project(self, project_id: str) -> None:
        self.workspace_registry.delete_project(project_id)

    def get_project(self, project_id: str) -> Optional[ProjectRecord]:
        return self.workspace_registry.get_project(project_id)

    def list_projects(
        self, workspace_id: Optional[str] = None
    ) -> List[ProjectRecord]:
        return self.workspace_registry.list_projects(workspace_id)

    def search_projects(self, keyword: str) -> List[ProjectRecord]:
        return self.workspace_registry.search_projects(keyword)

    def star_project(self, project_id: str) -> None:
        self.workspace_registry.star_project(project_id)

    def unstar_project(self, project_id: str) -> None:
        self.workspace_registry.unstar_project(project_id)

    def get_starred_projects(self) -> List[ProjectRecord]:
        return self.workspace_registry.get_starred()

    def link_project_experiment(
        self, project_id: str, experiment_id: str
    ) -> None:
        self.workspace_registry.link_experiment(project_id, experiment_id)

    def unlink_project_experiment(
        self, project_id: str, experiment_id: str
    ) -> None:
        self.workspace_registry.unlink_experiment(project_id, experiment_id)

"""

INSERT_BEFORE = (
    "    # ------------------------------------------------------------------\n"
    "    # 内部事件广播\n"
    "    # ------------------------------------------------------------------"
)
txt = txt.replace(INSERT_BEFORE, METHODS + INSERT_BEFORE)

P.write_text(txt, encoding="utf-8")
print("engine.py Artifact+Workspace patched OK, size:", P.stat().st_size)
