"""
research_ops/engine.py

ResearchOpsEngine — Phase 1 主引擎骨架。
继承 VeighNa BaseEngine，统一调度 7 个子引擎，对 UI 暴露统一 API。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME, FeatureStatus, StrategyStatus, ModelStatus, AuditAction
from .event import EVENT_RO_LOG, EVENT_RO_ERROR
from .engine.workspace_engine   import WorkspaceEngine
from .engine.experiment_engine  import ExperimentEngine
from .engine.registry_engine    import RegistryEngine
from .engine.pipeline_engine    import PipelineEngine
from .engine.report_engine      import ReportEngine
from .engine.knowledge_engine   import KnowledgeEngine
from .engine.governance_engine  import GovernanceEngine

from .model.workspace_model   import WorkspaceRecord, ProjectRecord, FolderRecord
from .model.experiment_model  import ExperimentRecord, RunRecord, ArtifactRef
from .model.registry_model    import (
    DatasetEntry, DatasetVersion, FeatureEntry, ICRecord,
    StrategyEntry, StrategyVersion, ModelEntry, TrainingRun,
)
from .model.pipeline_model    import PipelineRecord, DAGNode, PipelineRunRecord
from .model.report_model      import ReportRecord, ReportSection, ReportTemplate
from .model.knowledge_model   import KnowledgeNote, ExperienceCard, FailureCaseRecord
from .model.governance_model  import ApprovalRequest, FreezeRecord, AuditLog


class ResearchOpsEngine(BaseEngine):
    """
    ResearchOps Platform 2.0 主引擎。
    持有 7 个子引擎实例，对外暴露统一 API。
    UI 层只允许通过本类访问数据，禁止直接调用子引擎。
    """

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self.workspace   = WorkspaceEngine()
        self.experiment  = ExperimentEngine()
        self.registry    = RegistryEngine()
        self.pipeline    = PipelineEngine()
        self.report      = ReportEngine()
        self.knowledge   = KnowledgeEngine()
        self.governance  = GovernanceEngine()

    # ------------------------------------------------------------------
    # 内部广播
    # ------------------------------------------------------------------

    def _put(self, event_type: str, data: Any = None) -> None:
        self.event_engine.put(Event(event_type, data))

    def _log(self, msg: str) -> None:
        self._put(EVENT_RO_LOG, msg)

    def _error(self, msg: str) -> None:
        self._put(EVENT_RO_ERROR, msg)

    # ==================================================================
    # Workspace API
    # ==================================================================

    def create_workspace(self, name: str, **kw) -> WorkspaceRecord:
        ws = self.workspace.create_workspace(name, **kw)
        from .event import EVENT_RO_WS_CREATED
        self._put(EVENT_RO_WS_CREATED, ws); return ws

    def get_workspace(self, workspace_id: str) -> Optional[WorkspaceRecord]:
        return self.workspace.get_workspace(workspace_id)

    def list_workspaces(self) -> List[WorkspaceRecord]:
        return self.workspace.list_workspaces()

    def switch_workspace(self, workspace_id: str) -> bool:
        ok = self.workspace.switch_workspace(workspace_id)
        if ok:
            from .event import EVENT_RO_WS_SWITCHED
            self._put(EVENT_RO_WS_SWITCHED, self.workspace.get_active_workspace())
        return ok

    def get_active_workspace(self) -> Optional[WorkspaceRecord]:
        return self.workspace.get_active_workspace()

    def create_project(self, name: str, **kw) -> ProjectRecord:
        proj = self.workspace.create_project(name, **kw)
        from .event import EVENT_RO_PRJ_CREATED
        self._put(EVENT_RO_PRJ_CREATED, proj); return proj

    def get_project(self, project_id: str) -> Optional[ProjectRecord]:
        return self.workspace.get_project(project_id)

    def list_projects(self, workspace_id: Optional[str] = None) -> List[ProjectRecord]:
        return self.workspace.list_projects(workspace_id)

    def update_project(self, proj: ProjectRecord) -> None:
        self.workspace.update_project(proj)
        from .event import EVENT_RO_PRJ_UPDATED
        self._put(EVENT_RO_PRJ_UPDATED, proj)

    def delete_project(self, project_id: str) -> None:
        self.workspace.delete_project(project_id)
        from .event import EVENT_RO_PRJ_DELETED
        self._put(EVENT_RO_PRJ_DELETED, project_id)

    def star_project(self, project_id: str) -> None:
        self.workspace.star_project(project_id)
        from .event import EVENT_RO_PRJ_STARRED
        self._put(EVENT_RO_PRJ_STARRED, project_id)

    def unstar_project(self, project_id: str) -> None:
        self.workspace.unstar_project(project_id)
        from .event import EVENT_RO_PRJ_UNSTARRED
        self._put(EVENT_RO_PRJ_UNSTARRED, project_id)

    def get_starred_projects(self) -> List[ProjectRecord]:
        return self.workspace.get_starred_projects()

    def search_projects(self, keyword: str) -> List[ProjectRecord]:
        return self.workspace.search_projects(keyword)


    # ==================================================================
    # Experiment API
    # ==================================================================

    def create_experiment(self, name: str, **kw) -> ExperimentRecord:
        exp = self.experiment.create_experiment(name, **kw)
        from .event import EVENT_RO_EXP_CREATED
        self._put(EVENT_RO_EXP_CREATED, exp); return exp

    def get_experiment(self, experiment_id: str) -> Optional[ExperimentRecord]:
        return self.experiment.get_experiment(experiment_id)

    def list_experiments(self, **kw) -> List[ExperimentRecord]:
        return self.experiment.list_experiments(**kw)

    def update_experiment(self, exp: ExperimentRecord) -> None:
        self.experiment.update_experiment(exp)
        from .event import EVENT_RO_EXP_UPDATED
        self._put(EVENT_RO_EXP_UPDATED, exp)

    def delete_experiment(self, experiment_id: str) -> None:
        self.experiment.delete_experiment(experiment_id)
        from .event import EVENT_RO_EXP_DELETED
        self._put(EVENT_RO_EXP_DELETED, experiment_id)

    def search_experiments(self, keyword: str) -> List[ExperimentRecord]:
        return self.experiment.search_experiments(keyword)

    def start_run(self, experiment_id: str, **kw) -> RunRecord:
        run = self.experiment.start_run(experiment_id, **kw)
        from .event import EVENT_RO_RUN_CREATED
        self._put(EVENT_RO_RUN_CREATED, run); return run

    def complete_run(self, run_id: str, metrics: Optional[Dict] = None) -> None:
        self.experiment.complete_run(run_id, metrics)
        from .event import EVENT_RO_RUN_COMPLETED
        self._put(EVENT_RO_RUN_COMPLETED, run_id)

    def fail_run(self, run_id: str, error_msg: str = "") -> None:
        self.experiment.fail_run(run_id, error_msg)
        from .event import EVENT_RO_RUN_FAILED
        self._put(EVENT_RO_RUN_FAILED, run_id)

    def log_metric(self, run_id: str, key: str, value: float, step: int = 0) -> None:
        self.experiment.log_metric(run_id, key, value, step)
        from .event import EVENT_RO_METRIC_LOGGED
        self._put(EVENT_RO_METRIC_LOGGED, {"run_id": run_id, "key": key, "value": value})

    def log_params(self, run_id: str, params: Dict) -> None:
        self.experiment.log_params(run_id, params)

    def update_run(self, run) -> None:
        self.experiment.update_run(run)

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        return self.experiment.get_run(run_id)

    def list_runs(self, experiment_id: str) -> List[RunRecord]:
        return self.experiment.list_runs(experiment_id)

    def compare_runs(self, run_ids: List[str], metric_keys: Optional[List[str]] = None) -> List[Dict]:
        return self.experiment.compare_runs(run_ids, metric_keys)

    # ==================================================================
    # Registry API — Dataset / Feature / Strategy / Model
    # ==================================================================

    def register_dataset(self, name: str, **kw) -> DatasetEntry:
        ds = self.registry.register_dataset(name, **kw)
        from .event import EVENT_RO_DS_REGISTERED
        self._put(EVENT_RO_DS_REGISTERED, ds); return ds

    def get_dataset(self, dataset_id: str) -> Optional[DatasetEntry]:
        return self.registry.get_dataset(dataset_id)

    def list_datasets(self, **kw) -> List[DatasetEntry]:
        return self.registry.list_datasets(**kw)

    def update_dataset(self, ds: DatasetEntry) -> None:
        self.registry.update_dataset(ds)

    def delete_dataset(self, dataset_id: str) -> None:
        self.registry.delete_dataset(dataset_id)
        from .event import EVENT_RO_DS_DELETED
        self._put(EVENT_RO_DS_DELETED, dataset_id)

    def set_dataset_ready(self, dataset_id: str) -> None:
        self.registry.set_dataset_ready(dataset_id)

    def add_dataset_version(self, dataset_id: str, **kw) -> Optional[DatasetVersion]:
        return self.registry.add_dataset_version(dataset_id, **kw)

    def search_datasets(self, keyword: str) -> List[DatasetEntry]:
        return self.registry.search_datasets(keyword)

    def register_feature(self, name: str, **kw) -> FeatureEntry:
        ft = self.registry.register_feature(name, **kw)
        from .event import EVENT_RO_FT_REGISTERED
        self._put(EVENT_RO_FT_REGISTERED, ft); return ft

    def get_feature(self, feature_id: str) -> Optional[FeatureEntry]:
        return self.registry.get_feature(feature_id)

    def list_features(self, **kw) -> List[FeatureEntry]:
        return self.registry.list_features(**kw)

    def update_feature(self, ft: FeatureEntry) -> None:
        self.registry.update_feature(ft)

    def delete_feature(self, feature_id: str) -> None:
        self.registry.delete_feature(feature_id)

    def update_ic_metrics(self, feature_id: str, **kw) -> Optional[ICRecord]:
        return self.registry.update_ic_metrics(feature_id, **kw)

    def set_feature_status(self, feature_id: str, status: FeatureStatus) -> None:
        self.registry.set_feature_status(feature_id, status)

    def search_features(self, keyword: str) -> List[FeatureEntry]:
        return self.registry.search_features(keyword)

    def top_features_by_ic(self, n: int = 10) -> List[FeatureEntry]:
        return self.registry.top_by_ic(n)

    def register_strategy(self, name: str, **kw) -> StrategyEntry:
        st = self.registry.register_strategy(name, **kw)
        from .event import EVENT_RO_ST_REGISTERED
        self._put(EVENT_RO_ST_REGISTERED, st); return st

    def get_strategy(self, strategy_id: str) -> Optional[StrategyEntry]:
        return self.registry.get_strategy(strategy_id)

    def list_strategies(self, **kw) -> List[StrategyEntry]:
        return self.registry.list_strategies(**kw)

    def update_strategy(self, st: StrategyEntry) -> None:
        self.registry.update_strategy(st)

    def delete_strategy(self, strategy_id: str) -> None:
        self.registry.delete_strategy(strategy_id)

    def set_strategy_status(self, strategy_id: str, status: StrategyStatus) -> None:
        self.registry.set_strategy_status(strategy_id, status)
        from .event import EVENT_RO_ST_STATUS
        self._put(EVENT_RO_ST_STATUS, {"id": strategy_id, "status": status.value})

    def add_strategy_version(self, strategy_id: str, **kw) -> Optional[StrategyVersion]:
        return self.registry.add_strategy_version(strategy_id, **kw)

    def update_strategy_perf(self, strategy_id: str, **kw) -> None:
        self.registry.update_strategy_perf(strategy_id, **kw)

    def search_strategies(self, keyword: str) -> List[StrategyEntry]:
        return self.registry.search_strategies(keyword)

    def top_strategies_by_sharpe(self, n: int = 10) -> List[StrategyEntry]:
        return self.registry.top_by_sharpe(n)

    def register_model(self, name: str, **kw) -> ModelEntry:
        ml = self.registry.register_model(name, **kw)
        from .event import EVENT_RO_ML_REGISTERED
        self._put(EVENT_RO_ML_REGISTERED, ml); return ml

    def get_model(self, model_id: str) -> Optional[ModelEntry]:
        return self.registry.get_model(model_id)

    def list_models(self, **kw) -> List[ModelEntry]:
        return self.registry.list_models(**kw)

    def update_model(self, ml: ModelEntry) -> None:
        self.registry.update_model(ml)

    def delete_model(self, model_id: str) -> None:
        self.registry.delete_model(model_id)

    def add_training_run(self, model_id: str, **kw) -> Optional[TrainingRun]:
        return self.registry.add_training_run(model_id, **kw)

    def deploy_model(self, model_id: str, **kw) -> None:
        self.registry.deploy_model(model_id, **kw)
        from .event import EVENT_RO_ML_DEPLOYED
        self._put(EVENT_RO_ML_DEPLOYED, model_id)

    def set_model_status(self, model_id: str, status: ModelStatus) -> None:
        self.registry.set_model_status(model_id, status)

    def search_models(self, keyword: str) -> List[ModelEntry]:
        return self.registry.search_models(keyword)

    def top_models_by_auc(self, n: int = 10) -> List[ModelEntry]:
        return self.registry.top_by_auc(n)

    def get_lineage(self, node_id: str) -> Dict:
        lin = self.registry.lineage.full_lineage(node_id)
        return {k: list(v) for k, v in lin.items()}


    # ==================================================================
    # Pipeline API
    # ==================================================================

    def create_pipeline(self, name: str, **kw) -> PipelineRecord:
        pl = self.pipeline.create_pipeline(name, **kw)
        from .event import EVENT_RO_PL_CREATED
        self._put(EVENT_RO_PL_CREATED, pl); return pl

    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineRecord]:
        return self.pipeline.get_pipeline(pipeline_id)

    def list_pipelines(self, **kw) -> List[PipelineRecord]:
        return self.pipeline.list_pipelines(**kw)

    def delete_pipeline(self, pipeline_id: str) -> None:
        self.pipeline.delete_pipeline(pipeline_id)
        from .event import EVENT_RO_PL_DELETED
        self._put(EVENT_RO_PL_DELETED, pipeline_id)

    def add_pipeline_node(self, pipeline_id: str, name: str, **kw) -> Optional[DAGNode]:
        return self.pipeline.add_node(pipeline_id, name, **kw)

    def remove_pipeline_node(self, pipeline_id: str, node_id: str) -> None:
        self.pipeline.remove_node(pipeline_id, node_id)

    def start_pipeline(self, pipeline_id: str, **kw) -> Optional[PipelineRunRecord]:
        run = self.pipeline.start_pipeline(pipeline_id, **kw)
        if run:
            from .event import EVENT_RO_PL_STARTED
            self._put(EVENT_RO_PL_STARTED, run)
        return run

    def complete_pipeline(self, pipeline_id: str, **kw) -> None:
        self.pipeline.complete_pipeline(pipeline_id, **kw)
        from .event import EVENT_RO_PL_COMPLETED
        self._put(EVENT_RO_PL_COMPLETED, pipeline_id)

    def fail_pipeline(self, pipeline_id: str, **kw) -> None:
        self.pipeline.fail_pipeline(pipeline_id, **kw)
        from .event import EVENT_RO_PL_FAILED
        self._put(EVENT_RO_PL_FAILED, pipeline_id)

    def reset_pipeline(self, pipeline_id: str) -> None:
        self.pipeline.reset_pipeline(pipeline_id)

    def search_pipelines(self, keyword: str) -> List[PipelineRecord]:
        return self.pipeline.search_pipelines(keyword)

    def get_pipeline_execution_order(self, pipeline_id: str) -> List[str]:
        return self.pipeline.get_execution_order(pipeline_id)

    # ==================================================================
    # Report API
    # ==================================================================

    def create_report(self, title: str, **kw) -> ReportRecord:
        rpt = self.report.create_report(title, **kw)
        from .event import EVENT_RO_RPT_CREATED
        self._put(EVENT_RO_RPT_CREATED, rpt); return rpt

    def get_report(self, report_id: str) -> Optional[ReportRecord]:
        return self.report.get_report(report_id)

    def list_reports(self, **kw) -> List[ReportRecord]:
        return self.report.list_reports(**kw)

    def update_report(self, rpt: ReportRecord) -> None:
        self.report.update_report(rpt)
        from .event import EVENT_RO_RPT_UPDATED
        self._put(EVENT_RO_RPT_UPDATED, rpt)

    def delete_report(self, report_id: str) -> None:
        self.report.delete_report(report_id)
        from .event import EVENT_RO_RPT_DELETED
        self._put(EVENT_RO_RPT_DELETED, report_id)

    def publish_report(self, report_id: str) -> None:
        self.report.publish_report(report_id)
        from .event import EVENT_RO_RPT_PUBLISHED
        self._put(EVENT_RO_RPT_PUBLISHED, report_id)

    def add_report_section(self, report_id: str, title: str, **kw) -> Optional[ReportSection]:
        return self.report.add_section(report_id, title, **kw)

    def render_report_markdown(self, report_id: str) -> str:
        return self.report.render_markdown(report_id)

    def search_reports(self, keyword: str) -> List[ReportRecord]:
        return self.report.search_reports(keyword)

    # ==================================================================
    # Knowledge API
    # ==================================================================

    def create_note(self, title: str, **kw) -> KnowledgeNote:
        note = self.knowledge.create_note(title, **kw)
        from .event import EVENT_RO_KB_CREATED
        self._put(EVENT_RO_KB_CREATED, note); return note

    def get_note(self, note_id: str) -> Optional[KnowledgeNote]:
        return self.knowledge.get_note(note_id)

    def list_notes(self, **kw) -> List[KnowledgeNote]:
        return self.knowledge.list_notes(**kw)

    def update_note(self, note: KnowledgeNote) -> None:
        self.knowledge.update_note(note)
        from .event import EVENT_RO_KB_UPDATED
        self._put(EVENT_RO_KB_UPDATED, note)

    def delete_note(self, note_id: str) -> None:
        self.knowledge.delete_note(note_id)
        from .event import EVENT_RO_KB_DELETED
        self._put(EVENT_RO_KB_DELETED, note_id)

    def create_experience_card(self, title: str, **kw) -> ExperienceCard:
        return self.knowledge.create_card(title, **kw)

    def list_experience_cards(self, **kw) -> List[ExperienceCard]:
        return self.knowledge.list_cards(**kw)

    def create_failure_case(self, title: str, **kw) -> FailureCaseRecord:
        return self.knowledge.create_failure_case(title, **kw)

    def list_failure_cases(self, **kw) -> List[FailureCaseRecord]:
        return self.knowledge.list_failure_cases(**kw)

    def search_knowledge(self, keyword: str) -> Dict:
        return self.knowledge.search_all(keyword)

    # ==================================================================
    # Governance API
    # ==================================================================

    def submit_approval(self, title: str, **kw) -> ApprovalRequest:
        req = self.governance.submit_request(title, **kw)
        from .event import EVENT_RO_GOV_SUBMITTED
        self._put(EVENT_RO_GOV_SUBMITTED, req); return req

    def approve_request(self, request_id: str, approver: str, comment: str = "") -> None:
        self.governance.approve(request_id, approver, comment)
        from .event import EVENT_RO_GOV_APPROVED
        self._put(EVENT_RO_GOV_APPROVED, request_id)

    def reject_request(self, request_id: str, approver: str, comment: str = "") -> None:
        self.governance.reject(request_id, approver, comment)
        from .event import EVENT_RO_GOV_REJECTED
        self._put(EVENT_RO_GOV_REJECTED, request_id)

    def freeze_asset(self, **kw) -> FreezeRecord:
        rec = self.governance.freeze(**kw)
        from .event import EVENT_RO_GOV_FROZEN
        self._put(EVENT_RO_GOV_FROZEN, rec); return rec

    def unfreeze_asset(self, freeze_id: str, released_by: str = "") -> None:
        self.governance.unfreeze(freeze_id, released_by)
        from .event import EVENT_RO_GOV_RELEASED
        self._put(EVENT_RO_GOV_RELEASED, freeze_id)

    def is_asset_frozen(self, target_id: str) -> bool:
        return self.governance.is_frozen(target_id)

    def list_pending_approvals(self) -> List[ApprovalRequest]:
        return self.governance.pending_requests()

    def list_audit_logs(self, **kw) -> List[AuditLog]:
        return self.governance.list_audit_logs(**kw)

    def log_audit(self, actor: str, action: AuditAction, **kw) -> AuditLog:
        return self.governance.log_action(actor, action, **kw)


    # ==================================================================
    # Per-subsystem stats() — called by each Tab's _refresh_stats()
    # ==================================================================

    def stats(self) -> dict:
        """默认 stats：返回 experiment 子引擎统计（ExperimentTab 使用）。"""
        return self.experiment.stats()

    def workspace_stats(self) -> dict:
        return self.workspace.stats()

    def experiment_stats(self) -> dict:
        return self.experiment.stats()

    def registry_stats(self) -> dict:
        return self.registry.stats()

    def pipeline_stats(self) -> dict:
        return self.pipeline.stats()

    def report_stats(self) -> dict:
        return self.report.stats()

    def knowledge_stats(self) -> dict:
        return self.knowledge.stats()

    def governance_stats(self) -> dict:
        return self.governance.stats()

    # ==================================================================
    # 全平台统计
    # ==================================================================

    def get_platform_stats(self) -> Dict[str, Any]:
        return {
            "workspace":  self.workspace.stats(),
            "experiment": self.experiment.stats(),
            "registry":   self.registry.stats(),
            "pipeline":   self.pipeline.stats(),
            "report":     self.report.stats(),
            "knowledge":  self.knowledge.stats(),
            "governance": self.governance.stats(),
        }

    # ------------------------------------------------------------------
    # BaseEngine 接口
    # ------------------------------------------------------------------

    def close(self) -> None:
        pass

    # ==================================================================
    # 补充代理 — Knowledge
    # ==================================================================

    def archive_note(self, note_id: str) -> None:
        self.knowledge.archive_note(note_id)

    def create_card(self, title: str, **kw):
        return self.knowledge.create_card(title, **kw)

    def get_card(self, card_id: str):
        return self.knowledge.get_card(card_id)

    def list_cards(self, **kw):
        return self.knowledge.list_cards(**kw)

    def update_card(self, card) -> None:
        self.knowledge.update_card(card)

    def delete_card(self, card_id: str) -> None:
        self.knowledge.delete_card(card_id)

    def get_failure_case(self, case_id: str):
        return self.knowledge.get_failure_case(case_id)

    def update_failure_case(self, case) -> None:
        self.knowledge.update_failure_case(case)

    def delete_failure_case(self, case_id: str) -> None:
        self.knowledge.delete_failure_case(case_id)

    def resolve_case(self, case_id: str, **kw) -> None:
        self.knowledge.resolve_case(case_id, **kw)

    def search_all(self, keyword: str) -> dict:
        return self.knowledge.search_all(keyword)

    # ==================================================================
    # 补充代理 — Governance
    # ==================================================================

    def get_request(self, request_id: str):
        return self.governance.get_request(request_id)

    def list_requests(self, **kw):
        return self.governance.list_requests(**kw)

    def submit_request(self, title: str, **kw):
        return self.governance.submit_request(title, **kw)

    def list_freezes(self, **kw):
        return self.governance.list_freezes(**kw)

    # ==================================================================
    # 补充代理 — Pipeline
    # ==================================================================

    def add_node(self, pipeline_id: str, name: str, **kw):
        return self.pipeline.add_node(pipeline_id, name, **kw)

    def pause_pipeline(self, pipeline_id: str) -> None:
        self.pipeline.pause_pipeline(pipeline_id)

    # ==================================================================
    # 补充代理 — Report
    # ==================================================================

    def add_section(self, report_id: str, title: str, **kw):
        return self.report.add_section(report_id, title, **kw)

    def remove_section(self, report_id: str, section_id: str) -> None:
        self.report.remove_section(report_id, section_id)

    def update_section(self, report_id: str, section) -> None:
        self.report.update_section(report_id, section)

    def render_markdown(self, report_id: str) -> str:
        return self.report.render_markdown(report_id)

    def unpublish_report(self, report_id: str) -> None:
        self.report.unpublish_report(report_id)

    def create_template(self, name: str, **kw):
        return self.report.create_template(name, **kw)

    def get_template(self, template_id: str):
        return self.report.get_template(template_id)

    def list_templates(self, **kw):
        return self.report.list_templates(**kw)

    def apply_template(self, report_id: str, template_id: str) -> None:
        self.report.apply_template(report_id, template_id)

    # ==================================================================
    # 补充代理 — Governance 短名别名（Tab 用短名调用）
    # ==================================================================

    def approve(self, request_id: str, approver: str = "", comment: str = "") -> None:
        self.governance.approve(request_id, approver, comment)

    def reject(self, request_id: str, approver: str = "", comment: str = "") -> None:
        self.governance.reject(request_id, approver, comment)

    def freeze(self, **kw):
        return self.governance.freeze(**kw)

    def unfreeze(self, freeze_id: str, released_by: str = "") -> None:
        self.governance.unfreeze(freeze_id, released_by)

