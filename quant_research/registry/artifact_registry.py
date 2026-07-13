"""
quant_research/registry/artifact_registry.py  — Phase 10 完整实现
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from ..model.artifact_model import ArtifactRecord
from ..constant import ArtifactType


class ArtifactRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, ArtifactRecord] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, record: ArtifactRecord) -> ArtifactRecord:
        self._records[record.artifact_id] = record
        return record

    def get(self, artifact_id: str) -> Optional[ArtifactRecord]:
        return self._records.get(artifact_id)

    def list(self) -> List[ArtifactRecord]:
        return list(self._records.values())

    def update(self, record: ArtifactRecord) -> None:
        self._records[record.artifact_id] = record

    def delete(self, artifact_id: str) -> None:
        self._records.pop(artifact_id, None)

    def clear(self) -> None:
        self._records.clear()

    # ------------------------------------------------------------------
    # 过滤 / 搜索
    # ------------------------------------------------------------------

    def filter(
        self,
        artifact_type: Optional[ArtifactType] = None,
        tag:           Optional[str]           = None,
        author:        Optional[str]           = None,
        archived:      Optional[bool]          = None,
        experiment_id: Optional[str]           = None,
        pipeline_id:   Optional[str]           = None,
    ) -> List[ArtifactRecord]:
        result = list(self._records.values())
        if artifact_type is not None:
            result = [r for r in result if r.artifact_type == artifact_type]
        if tag is not None:
            result = [r for r in result if tag in r.tags]
        if author is not None:
            result = [r for r in result
                      if author.lower() in r.author.lower()]
        if archived is not None:
            result = [r for r in result if r.is_archived == archived]
        if experiment_id is not None:
            result = [r for r in result if r.experiment_id == experiment_id]
        if pipeline_id is not None:
            result = [r for r in result if r.pipeline_id == pipeline_id]
        return result

    def search(self, keyword: str) -> List[ArtifactRecord]:
        kw = keyword.lower()
        return [
            r for r in self._records.values()
            if kw in r.name.lower()
            or kw in r.description.lower()
            or kw in r.author.lower()
            or kw in r.artifact_type.value.lower()
            or kw in r.file_path.lower()
            or any(kw in t.lower() for t in r.tags)
        ]

    # ------------------------------------------------------------------
    # 归档 / 下载统计
    # ------------------------------------------------------------------

    def archive(self, artifact_id: str) -> None:
        r = self._records.get(artifact_id)
        if r:
            r.is_archived = True
            r.updated_at  = datetime.now()

    def unarchive(self, artifact_id: str) -> None:
        r = self._records.get(artifact_id)
        if r:
            r.is_archived = False
            r.updated_at  = datetime.now()

    def increment_download(self, artifact_id: str) -> None:
        r = self._records.get(artifact_id)
        if r:
            r.download_count += 1

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def total_size_kb(self) -> float:
        return sum(r.file_size_kb for r in self._records.values()
                   if not r.is_archived)

    def type_counts(self) -> Dict[ArtifactType, int]:
        counts: Dict[ArtifactType, int] = {t: 0 for t in ArtifactType}
        for r in self._records.values():
            counts[r.artifact_type] = counts.get(r.artifact_type, 0) + 1
        return counts
