"""
research_ops/engine/pipeline_engine.py  — Phase 1 骨架
负责：DAG 流水线定义 / 节点编排 / 执行调度 / 失败重试 / 执行日志。
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..constant import PipelineStatus, NodeStatus, NodeType, TriggerType
from ..model.pipeline_model import PipelineRecord, DAGNode, PipelineRunRecord
from ..repository.memory import InMemoryRepository
from ..utils.id_gen import gen_pipeline_id, gen_node_id, gen_pl_run_id
from ..utils.lineage import LineageGraph


class PipelineEngine:
    def __init__(self) -> None:
        self._pl_repo:  InMemoryRepository = InMemoryRepository()
        self._node_counter: Dict[str, int] = {}
        self._run_counter:  Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Pipeline CRUD
    # ------------------------------------------------------------------

    def create_pipeline(
        self,
        name:        str,
        project_id:  str = "",
        description: str = "",
        schedule:    str = "",
        author:      str = "",
        tags:        Optional[List[str]] = None,
        created_by:  str = "",
    ) -> PipelineRecord:
        now = datetime.now()
        pl  = PipelineRecord(
            pipeline_id = gen_pipeline_id(),
            project_id  = project_id,
            name        = name,
            description = description,
            schedule    = schedule,
            author      = author,
            tags        = tags or [],
            created_by  = created_by,
            created_at  = now,
            updated_at  = now,
        )
        self._pl_repo.save(pl)
        return pl

    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineRecord]:
        return self._pl_repo.get(pipeline_id)

    def list_pipelines(
        self, project_id: Optional[str] = None,
        status: Optional[PipelineStatus] = None,
    ) -> List[PipelineRecord]:
        filters: Dict[str, Any] = {}
        if project_id: filters["project_id"] = project_id
        if status:     filters["status"]      = status
        return self._pl_repo.query(**filters) if filters else self._pl_repo.list()

    def update_pipeline(self, pl: PipelineRecord) -> None:
        pl.updated_at = datetime.now()
        self._pl_repo.save(pl)

    def delete_pipeline(self, pipeline_id: str) -> None:
        self._pl_repo.delete(pipeline_id)

    # ------------------------------------------------------------------
    # Node (DAG) 管理
    # ------------------------------------------------------------------

    def add_node(
        self,
        pipeline_id: str,
        name:        str,
        node_type:   NodeType = NodeType.CUSTOM,
        depends_on:  Optional[List[str]] = None,
        params:      Optional[Dict[str, Any]] = None,
        timeout_sec: int = 3600,
        max_retries: int = 3,
    ) -> Optional[DAGNode]:
        pl = self._pl_repo.get(pipeline_id)
        if not pl:
            return None
        count = self._node_counter.get(pipeline_id, 0) + 1
        self._node_counter[pipeline_id] = count
        node = DAGNode(
            node_id     = f"NOD-{pipeline_id[-8:]}-{count:03d}",
            pipeline_id = pipeline_id,
            name        = name,
            node_type   = node_type,
            depends_on  = depends_on or [],
            params      = params or {},
            timeout_sec = timeout_sec,
            max_retries = max_retries,
            order       = count,
        )
        pl.nodes.append(node)
        pl.updated_at = datetime.now()
        self._pl_repo.save(pl)
        return node

    def remove_node(self, pipeline_id: str, node_id: str) -> None:
        pl = self._pl_repo.get(pipeline_id)
        if pl:
            pl.nodes = [n for n in pl.nodes if n.node_id != node_id]
            pl.updated_at = datetime.now()
            self._pl_repo.save(pl)

    def get_execution_order(self, pipeline_id: str) -> List[str]:
        """拓扑排序节点 ID，决定执行顺序。"""
        pl = self._pl_repo.get(pipeline_id)
        if not pl:
            return []
        g = LineageGraph()
        for node in pl.nodes:
            g.add_node(node.node_id, label=node.name)
        for node in pl.nodes:
            for dep in node.depends_on:
                if g.get_node(dep):
                    g.add_edge(dep, node.node_id)
        try:
            return g.topological_sort()
        except ValueError:
            return [n.node_id for n in pl.nodes]

    # ------------------------------------------------------------------
    # 执行状态流转
    # ------------------------------------------------------------------

    def start_pipeline(
        self,
        pipeline_id: str,
        trigger:     TriggerType = TriggerType.MANUAL,
        triggered_by: str = "",
    ) -> Optional[PipelineRunRecord]:
        pl = self._pl_repo.get(pipeline_id)
        if not pl:
            return None
        count = self._run_counter.get(pipeline_id, 0) + 1
        self._run_counter[pipeline_id] = count
        now = datetime.now()
        run = PipelineRunRecord(
            run_id       = f"PLR-{pipeline_id[-8:]}-{count:03d}",
            pipeline_id  = pipeline_id,
            trigger      = trigger,
            status       = "running",
            triggered_by = triggered_by,
            started_at   = now,
        )
        pl.runs.append(run)
        pl.status       = PipelineStatus.RUNNING
        pl.run_count   += 1
        pl.last_run_at  = now
        pl.updated_at   = now
        for node in pl.nodes:
            node.status = NodeStatus.PENDING
            node.log    = ""
            node.error_msg = ""
        self._pl_repo.save(pl)
        return run

    def complete_pipeline(
        self,
        pipeline_id:  str,
        duration_sec: float = 0.0,
        node_logs:    Optional[Dict[str, str]] = None,
    ) -> None:
        pl = self._pl_repo.get(pipeline_id)
        if not pl:
            return
        now = datetime.now()
        pl.status        = PipelineStatus.COMPLETED
        pl.success_count += 1
        pl.updated_at    = now
        if pl.runs:
            run = pl.runs[-1]
            run.status       = "completed"
            run.finished_at  = now
            run.duration_sec = duration_sec
            run.node_logs    = node_logs or {}
        for node in pl.nodes:
            node.status = NodeStatus.COMPLETED
        self._pl_repo.save(pl)

    def fail_pipeline(
        self, pipeline_id: str,
        error_msg: str = "", failed_node_id: str = "",
    ) -> None:
        pl = self._pl_repo.get(pipeline_id)
        if not pl:
            return
        now = datetime.now()
        pl.status     = PipelineStatus.FAILED
        pl.fail_count += 1
        pl.updated_at = now
        if pl.runs:
            run = pl.runs[-1]
            run.status      = "failed"
            run.finished_at = now
            run.error_msg   = error_msg
        if failed_node_id:
            for node in pl.nodes:
                if node.node_id == failed_node_id:
                    node.status    = NodeStatus.FAILED
                    node.error_msg = error_msg
        self._pl_repo.save(pl)

    def pause_pipeline(self, pipeline_id: str) -> None:
        pl = self._pl_repo.get(pipeline_id)
        if pl:
            pl.status = PipelineStatus.PAUSED
            pl.updated_at = datetime.now()
            self._pl_repo.save(pl)

    def reset_pipeline(self, pipeline_id: str) -> None:
        pl = self._pl_repo.get(pipeline_id)
        if pl:
            pl.status = PipelineStatus.IDLE
            pl.updated_at = datetime.now()
            for node in pl.nodes:
                node.status = NodeStatus.IDLE
                node.log = ""
                node.error_msg = ""
                node.retries = 0
            self._pl_repo.save(pl)

    def complete_node(
        self, pipeline_id: str, node_id: str, log: str = ""
    ) -> None:
        pl = self._pl_repo.get(pipeline_id)
        if not pl:
            return
        for node in pl.nodes:
            if node.node_id == node_id:
                node.status      = NodeStatus.COMPLETED
                node.log         = log
                node.finished_at = datetime.now()
        self._pl_repo.save(pl)

    def fail_node(
        self,
        pipeline_id: str, node_id: str,
        error_msg: str = "", retry: bool = False,
    ) -> None:
        pl = self._pl_repo.get(pipeline_id)
        if not pl:
            return
        for node in pl.nodes:
            if node.node_id == node_id:
                if retry and node.retries < node.max_retries:
                    node.retries  += 1
                    node.status    = NodeStatus.PENDING
                    node.error_msg = f"retry {node.retries}: {error_msg}"
                else:
                    node.status    = NodeStatus.FAILED
                    node.error_msg = error_msg
        self._pl_repo.save(pl)

    def search_pipelines(self, keyword: str) -> List[PipelineRecord]:
        return self._pl_repo.search(keyword, fields=["name", "description", "tags"])

    def stats(self) -> dict:
        pls = self._pl_repo.list()
        return {
            "pipelines":    len(pls),
            "running":      sum(1 for p in pls if p.status == PipelineStatus.RUNNING),
            "completed":    sum(1 for p in pls if p.status == PipelineStatus.COMPLETED),
            "failed":       sum(1 for p in pls if p.status == PipelineStatus.FAILED),
            "paused":       sum(1 for p in pls if p.status == PipelineStatus.PAUSED),
            "total_runs":   sum(p.run_count for p in pls),
            "total_nodes":  sum(len(p.nodes) for p in pls),
        }
