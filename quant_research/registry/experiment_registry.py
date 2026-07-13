"""
quant_research/registry/experiment_registry.py

ExperimentRegistry — Phase 2 完整实现。
"""
from __future__ import annotations
from typing import Dict, List, Optional
from ..model.experiment_model import ExperimentRecord
from ..constant import ExperimentStatus


class ExperimentRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, ExperimentRecord] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, record: ExperimentRecord) -> ExperimentRecord:
        self._records[record.experiment_id] = record
        return record

    def get(self, experiment_id: str) -> Optional[ExperimentRecord]:
        return self._records.get(experiment_id)

    def list(self) -> List[ExperimentRecord]:
        return list(self._records.values())

    def update(self, record: ExperimentRecord) -> None:
        self._records[record.experiment_id] = record

    def delete(self, experiment_id: str) -> None:
        self._records.pop(experiment_id, None)

    def clear(self) -> None:
        self._records.clear()

    # ------------------------------------------------------------------
    # 过滤 / 搜索
    # ------------------------------------------------------------------

    def filter(
        self,
        status: Optional[ExperimentStatus] = None,
        tag:    Optional[str]              = None,
        starred: Optional[bool]            = None,
    ) -> List[ExperimentRecord]:
        result = list(self._records.values())
        if status is not None:
            result = [r for r in result if r.status == status]
        if tag is not None:
            result = [r for r in result if tag in r.tags]
        if starred is not None:
            result = [r for r in result if r.starred == starred]
        return result

    def search(self, keyword: str) -> List[ExperimentRecord]:
        kw = keyword.lower()
        return [
            r for r in self._records.values()
            if kw in r.name.lower()
            or kw in r.description.lower()
            or any(kw in t.lower() for t in r.tags)
        ]
