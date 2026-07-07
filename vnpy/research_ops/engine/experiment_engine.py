"""
research_ops/engine/experiment_engine.py  — Phase 1 骨架
负责：实验追踪 / Run 记录 / 指标日志 / 实验对比。
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..constant import ExperimentStatus, RunStatus
from ..model.experiment_model import ExperimentRecord, RunRecord, MetricPoint, ArtifactRef
from ..repository.memory import InMemoryRepository
from ..utils.id_gen import gen_experiment_id, gen_run_id


class ExperimentEngine:
    def __init__(self) -> None:
        self._exp_repo: InMemoryRepository = InMemoryRepository()
        self._run_repo: InMemoryRepository = InMemoryRepository()

    # ------------------------------------------------------------------
    # Experiment CRUD
    # ------------------------------------------------------------------

    def create_experiment(
        self,
        name:           str,
        project_id:     str              = "",
        workspace_id:   str              = "",
        description:    str              = "",
        hypothesis:     str              = "",
        objective:      str              = "",
        primary_metric: str              = "",
        tags:           Optional[List[str]] = None,
        created_by:     str              = "",
    ) -> ExperimentRecord:
        now = datetime.now()
        exp = ExperimentRecord(
            experiment_id  = gen_experiment_id(),
            project_id     = project_id,
            workspace_id   = workspace_id,
            name           = name,
            description    = description,
            hypothesis     = hypothesis,
            objective      = objective,
            primary_metric = primary_metric,
            tags           = tags or [],
            created_by     = created_by,
            created_at     = now,
            updated_at     = now,
        )
        self._exp_repo.save(exp)
        return exp

    def get_experiment(self, experiment_id: str) -> Optional[ExperimentRecord]:
        return self._exp_repo.get(experiment_id)

    def list_experiments(
        self,
        project_id:   Optional[str]              = None,
        workspace_id: Optional[str]              = None,
        status:       Optional[ExperimentStatus] = None,
    ) -> List[ExperimentRecord]:
        filters: Dict[str, Any] = {}
        if project_id:   filters["project_id"]   = project_id
        if workspace_id: filters["workspace_id"] = workspace_id
        if status:       filters["status"]        = status
        return self._exp_repo.query(**filters) if filters else self._exp_repo.list()

    def update_experiment(self, exp: ExperimentRecord) -> None:
        exp.updated_at = datetime.now()
        self._exp_repo.save(exp)

    def delete_experiment(self, experiment_id: str) -> None:
        exp = self._exp_repo.get(experiment_id)
        if exp:
            for run_id in exp.run_ids:
                self._run_repo.delete(run_id)
        self._exp_repo.delete(experiment_id)

    def set_experiment_status(
        self, experiment_id: str, status: ExperimentStatus
    ) -> None:
        exp = self._exp_repo.get(experiment_id)
        if exp:
            exp.status     = status
            exp.updated_at = datetime.now()
            self._exp_repo.save(exp)

    def search_experiments(self, keyword: str) -> List[ExperimentRecord]:
        return self._exp_repo.search(
            keyword, fields=["name", "description", "hypothesis", "tags"])

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def start_run(
        self,
        experiment_id: str,
        name:          str              = "",
        params:        Optional[Dict[str, Any]] = None,
        tags:          Optional[List[str]]      = None,
        git_commit:    str              = "",
        data_version:  str              = "",
        created_by:    str              = "",
    ) -> RunRecord:
        now = datetime.now()
        run = RunRecord(
            run_id        = gen_run_id(),
            experiment_id = experiment_id,
            name          = name or f"run-{now.strftime('%H%M%S')}",
            status        = RunStatus.RUNNING,
            params        = params or {},
            tags          = tags or [],
            git_commit    = git_commit,
            data_version  = data_version,
            created_by    = created_by,
            started_at    = now,
            created_at    = now,
        )
        self._run_repo.save(run)
        exp = self._exp_repo.get(experiment_id)
        if exp and run.run_id not in exp.run_ids:
            exp.run_ids.append(run.run_id)
            exp.status     = ExperimentStatus.RUNNING
            exp.updated_at = now
            self._exp_repo.save(exp)
        return run

    def complete_run(
        self,
        run_id:  str,
        metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        run = self._run_repo.get(run_id)
        if not run:
            return
        now = datetime.now()
        run.status      = RunStatus.COMPLETED
        run.finished_at = now
        if run.started_at:
            run.duration_sec = (now - run.started_at).total_seconds()
        if metrics:
            run.metrics.update(metrics)
        self._run_repo.save(run)
        self._maybe_update_best_run(run.experiment_id)

    def fail_run(self, run_id: str, error_msg: str = "") -> None:
        run = self._run_repo.get(run_id)
        if run:
            run.status    = RunStatus.FAILED
            run.error_msg = error_msg
            run.finished_at = datetime.now()
            self._run_repo.save(run)

    def kill_run(self, run_id: str) -> None:
        run = self._run_repo.get(run_id)
        if run:
            run.status      = RunStatus.KILLED
            run.finished_at = datetime.now()
            self._run_repo.save(run)

    def log_metric(
        self, run_id: str, key: str, value: float, step: int = 0
    ) -> None:
        run = self._run_repo.get(run_id)
        if run:
            run.metrics[key] = value
            run.metric_history.append(
                MetricPoint(key=key, value=value, step=step))
            self._run_repo.save(run)

    def log_params(self, run_id: str, params: Dict[str, Any]) -> None:
        run = self._run_repo.get(run_id)
        if run:
            run.params.update(params)
            self._run_repo.save(run)

    def add_artifact(self, run_id: str, artifact: ArtifactRef) -> None:
        run = self._run_repo.get(run_id)
        if run:
            run.artifacts.append(artifact)
            self._run_repo.save(run)

    def update_run(self, run: RunRecord) -> None:
        run.updated_at = datetime.now() if hasattr(run, 'updated_at') else None
        self._run_repo.save(run)

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        return self._run_repo.get(run_id)

    def list_runs(self, experiment_id: str) -> List[RunRecord]:
        return self._run_repo.query(experiment_id=experiment_id)

    # ------------------------------------------------------------------
    # 实验对比
    # ------------------------------------------------------------------

    def compare_runs(
        self, run_ids: List[str], metric_keys: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        result = []
        for run_id in run_ids:
            run = self._run_repo.get(run_id)
            if not run:
                continue
            row: Dict[str, Any] = {
                "run_id":  run.run_id,
                "name":    run.name,
                "status":  run.status.value,
                "params":  run.params,
                "metrics": {k: v for k, v in run.metrics.items()
                            if metric_keys is None or k in metric_keys},
            }
            result.append(row)
        return result

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _maybe_update_best_run(self, experiment_id: str) -> None:
        exp = self._exp_repo.get(experiment_id)
        if not exp or not exp.primary_metric:
            return
        best_val  = None
        best_id   = None
        for run_id in exp.run_ids:
            run = self._run_repo.get(run_id)
            if run and run.status == RunStatus.COMPLETED:
                val = run.metrics.get(exp.primary_metric)
                if val is not None and (best_val is None or val > best_val):
                    best_val = val
                    best_id  = run_id
        if best_id:
            exp.best_run_id = best_id
            self._exp_repo.save(exp)

    def stats(self) -> dict:
        from ..constant import RunStatus, ExperimentStatus
        runs = self._run_repo.list()
        exps = self._exp_repo.list()
        return {
            "experiments":    len(exps),
            "runs":           len(runs),
            "running":        sum(1 for r in runs if r.status == RunStatus.RUNNING),
            "completed":      sum(1 for r in runs if r.status == RunStatus.COMPLETED),
            "failed":         sum(1 for r in runs if r.status == RunStatus.FAILED),
            "pending":        sum(1 for r in runs if r.status == RunStatus.PENDING),
            "exp_running":    sum(1 for e in exps if e.status == ExperimentStatus.RUNNING),
            "exp_completed":  sum(1 for e in exps if e.status == ExperimentStatus.COMPLETED),
        }
