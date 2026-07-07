"""
quant_research/registry/dataset_registry.py

DatasetRegistry — Phase 3 完整实现。
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from ..model.dataset_model import DatasetRecord, DatasetSnapshot
from ..constant import DatasetStatus


class DatasetRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, DatasetRecord] = {}
        self._snap_counter: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, record: DatasetRecord) -> DatasetRecord:
        self._records[record.dataset_id] = record
        return record

    def get(self, dataset_id: str) -> Optional[DatasetRecord]:
        return self._records.get(dataset_id)

    def list(self) -> List[DatasetRecord]:
        return list(self._records.values())

    def update(self, record: DatasetRecord) -> None:
        self._records[record.dataset_id] = record

    def delete(self, dataset_id: str) -> None:
        self._records.pop(dataset_id, None)

    def clear(self) -> None:
        self._records.clear()
        self._snap_counter.clear()

    # ------------------------------------------------------------------
    # 过滤 / 搜索
    # ------------------------------------------------------------------

    def filter(
        self,
        status: Optional[DatasetStatus] = None,
        source: Optional[str] = None,
        tag:    Optional[str] = None,
    ) -> List[DatasetRecord]:
        result = list(self._records.values())
        if status is not None:
            result = [r for r in result if r.status == status]
        if source is not None:
            result = [r for r in result if source.lower() in r.source.lower()]
        if tag is not None:
            result = [r for r in result if tag in r.tags]
        return result

    def search(self, keyword: str) -> List[DatasetRecord]:
        kw = keyword.lower()
        return [
            r for r in self._records.values()
            if kw in r.name.lower()
            or kw in r.description.lower()
            or kw in r.source.lower()
            or any(kw in t.lower() for t in r.tags)
            or any(kw in s.lower() for s in r.symbols)
            or any(kw in f.lower() for f in r.fields)
        ]

    # ------------------------------------------------------------------
    # 快照
    # ------------------------------------------------------------------

    def take_snapshot(self, dataset_id: str) -> Optional[DatasetSnapshot]:
        record = self._records.get(dataset_id)
        if record is None:
            return None
        count = self._snap_counter.get(dataset_id, 0) + 1
        self._snap_counter[dataset_id] = count
        snap = DatasetSnapshot(
            snapshot_id   = f"SNAP-{dataset_id}-{count:03d}",
            dataset_id    = dataset_id,
            version       = record.version,
            row_count     = record.row_count,
            size_mb       = record.size_mb,
            fields        = list(record.fields),
            quality_score = record.quality_score,
            quality_metrics = dict(record.quality_metrics),
            taken_at      = datetime.now(),
        )
        record.snapshots.append(snap)
        record.updated_at = datetime.now()
        return snap

    def get_snapshots(self, dataset_id: str) -> List[DatasetSnapshot]:
        record = self._records.get(dataset_id)
        if record is None:
            return []
        return list(record.snapshots)

    # ------------------------------------------------------------------
    # 依赖 / 血缘
    # ------------------------------------------------------------------

    def add_dependency(self, dataset_id: str, dep_id: str) -> None:
        record = self._records.get(dataset_id)
        if record and dep_id not in record.dependencies:
            record.dependencies.append(dep_id)
            record.updated_at = datetime.now()

    def remove_dependency(self, dataset_id: str, dep_id: str) -> None:
        record = self._records.get(dataset_id)
        if record and dep_id in record.dependencies:
            record.dependencies.remove(dep_id)
            record.updated_at = datetime.now()

    def get_lineage(
        self,
        dataset_id: str,
        visited: Optional[set] = None,
    ) -> List[str]:
        """递归向上追溯所有上游依赖，返回有序列表（最远祖先在前）。"""
        if visited is None:
            visited = set()
        if dataset_id in visited:
            return []
        visited.add(dataset_id)

        record = self._records.get(dataset_id)
        if record is None:
            return []

        result: List[str] = []
        for dep_id in record.dependencies:
            result.extend(self.get_lineage(dep_id, visited))
            if dep_id not in result:
                result.append(dep_id)
        return result

    def get_dependents(self, dataset_id: str) -> List[str]:
        """返回直接依赖本数据集的下游数据集 ID 列表。"""
        return [
            r.dataset_id
            for r in self._records.values()
            if dataset_id in r.dependencies
        ]

    # ------------------------------------------------------------------
    # 质量
    # ------------------------------------------------------------------

    def update_quality(
        self,
        dataset_id: str,
        quality_score: float,
        metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        record = self._records.get(dataset_id)
        if record:
            record.quality_score   = max(0.0, min(1.0, quality_score))
            record.quality_metrics = metrics or {}
            record.updated_at      = datetime.now()
