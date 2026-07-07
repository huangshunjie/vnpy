"""
quant_research/registry/pipeline_registry.py  — Phase 9 完整实现
"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..model.pipeline_model import PipelineRecord, PipelineStepRecord, PipelineRun
from ..constant import PipelineStatus


class PipelineRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, PipelineRecord] = {}
        self._run_counter: Dict[str, int] = {}
        self._step_counter: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, record: PipelineRecord) -> PipelineRecord:
        self._records[record.pipeline_id] = record
        return record

    def get(self, pipeline_id: str) -> Optional[PipelineRecord]:
        return self._records.get(pipeline_id)

    def list(self) -> List[PipelineRecord]:
        return list(self._records.values())

    def update(self, record: PipelineRecord) -> None:
        self._records[record.pipeline_id] = record

    def delete(self, pipeline_id: str) -> None:
        self._records.pop(pipeline_id, None)

    def clear(self) -> None:
        self._records.clear()
        self._run_counter.clear()
        self._step_counter.clear()

    # ------------------------------------------------------------------
    # 过滤 / 搜索
    # ------------------------------------------------------------------

    def filter(
        self,
        status: Optional[PipelineStatus] = None,
        tag:    Optional[str]            = None,
        author: Optional[str]            = None,
    ) -> List[PipelineRecord]:
        result = list(self._records.values())
        if status is not None:
            result = [r for r in result if r.status == status]
        if tag is not None:
            result = [r for r in result if tag in r.tags]
        if author is not None:
            result = [r for r in result
                      if author.lower() in r.author.lower()]
        return result

    def search(self, keyword: str) -> List[PipelineRecord]:
        kw = keyword.lower()
        return [
            r for r in self._records.values()
            if kw in r.name.lower()
            or kw in r.description.lower()
            or kw in r.author.lower()
            or any(kw in t.lower() for t in r.tags)
        ]

    # ------------------------------------------------------------------
    # 步骤管理
    # ------------------------------------------------------------------

    def add_step(
        self,
        pipeline_id: str,
        name:        str,
        step_type:   str             = "custom",
        params:      Optional[Dict[str, Any]] = None,
        depends_on:  Optional[List[str]]      = None,
        timeout_sec: int             = 3600,
    ) -> Optional[PipelineStepRecord]:
        record = self._records.get(pipeline_id)
        if record is None:
            return None
        count = self._step_counter.get(pipeline_id, 0) + 1
        self._step_counter[pipeline_id] = count
        step = PipelineStepRecord(
            step_id     = f"STEP-{pipeline_id}-{count:03d}",
            name        = name,
            step_type   = step_type,
            params      = params or {},
            depends_on  = depends_on or [],
            order       = count,
            timeout_sec = timeout_sec,
        )
        record.steps.append(step)
        record.updated_at = datetime.now()
        return step

    def remove_step(self, pipeline_id: str, step_id: str) -> None:
        record = self._records.get(pipeline_id)
        if record:
            record.steps = [s for s in record.steps
                           if s.step_id != step_id]
            record.updated_at = datetime.now()

    def reorder_steps(self, pipeline_id: str, step_ids: List[str]) -> None:
        record = self._records.get(pipeline_id)
        if record is None:
            return
        step_map = {s.step_id: s for s in record.steps}
        record.steps = []
        for i, sid in enumerate(step_ids):
            if sid in step_map:
                step_map[sid].order = i + 1
                record.steps.append(step_map[sid])
        record.updated_at = datetime.now()

    # ------------------------------------------------------------------
    # 状态流转
    # ------------------------------------------------------------------

    def start(self, pipeline_id: str, trigger: str = "manual") -> Optional[PipelineRun]:
        record = self._records.get(pipeline_id)
        if record is None:
            return None
        count = self._run_counter.get(pipeline_id, 0) + 1
        self._run_counter[pipeline_id] = count
        now = datetime.now()
        run = PipelineRun(
            run_id      = f"RUN-{pipeline_id}-{count:03d}",
            pipeline_id = pipeline_id,
            status      = "running",
            trigger     = trigger,
            started_at  = now,
        )
        record.runs.append(run)
        record.status      = PipelineStatus.RUNNING
        record.last_run_at = now
        record.run_count  += 1
        record.updated_at  = now
        # 重置所有步骤状态
        for step in record.steps:
            step.status = "running"
            step.log    = ""
        return run

    def complete(
        self,
        pipeline_id:  str,
        duration_sec: float = 0.0,
        step_logs:    Optional[Dict[str, str]] = None,
    ) -> None:
        record = self._records.get(pipeline_id)
        if record is None:
            return
        now = datetime.now()
        record.status        = PipelineStatus.COMPLETED
        record.success_count += 1
        record.updated_at    = now
        if record.runs:
            run = record.runs[-1]
            run.status       = "completed"
            run.finished_at  = now
            run.duration_sec = duration_sec
            run.step_logs    = step_logs or {}
        for step in record.steps:
            step.status = "completed"

    def fail(
        self,
        pipeline_id: str,
        error_msg:   str = "",
        failed_step: str = "",
    ) -> None:
        record = self._records.get(pipeline_id)
        if record is None:
            return
        now = datetime.now()
        record.status     = PipelineStatus.FAILED
        record.fail_count += 1
        record.updated_at = now
        if record.runs:
            run = record.runs[-1]
            run.status      = "failed"
            run.finished_at = now
            run.error_msg   = error_msg
        if failed_step:
            for step in record.steps:
                if step.step_id == failed_step or step.name == failed_step:
                    step.status = "failed"
                    step.log    = error_msg

    def pause(self, pipeline_id: str) -> None:
        record = self._records.get(pipeline_id)
        if record:
            record.status     = PipelineStatus.PAUSED
            record.updated_at = datetime.now()

    def reset(self, pipeline_id: str) -> None:
        record = self._records.get(pipeline_id)
        if record:
            record.status     = PipelineStatus.IDLE
            record.updated_at = datetime.now()
            for step in record.steps:
                step.status = "idle"
                step.log    = ""

    # ------------------------------------------------------------------
    # 历史
    # ------------------------------------------------------------------

    def get_runs(self, pipeline_id: str) -> List[PipelineRun]:
        record = self._records.get(pipeline_id)
        return list(record.runs) if record else []
