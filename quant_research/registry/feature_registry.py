"""
quant_research/registry/feature_registry.py

FeatureRegistry — Phase 4 完整实现。
"""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from ..model.feature_model import FeatureRecord, ICRecord
from ..constant import FeatureStatus


class FeatureRegistry:
    def __init__(self) -> None:
        self._records: Dict[str, FeatureRecord] = {}
        self._eval_counter: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create(self, record: FeatureRecord) -> FeatureRecord:
        self._records[record.feature_id] = record
        return record

    def get(self, feature_id: str) -> Optional[FeatureRecord]:
        return self._records.get(feature_id)

    def list(self) -> List[FeatureRecord]:
        return list(self._records.values())

    def update(self, record: FeatureRecord) -> None:
        self._records[record.feature_id] = record

    def delete(self, feature_id: str) -> None:
        self._records.pop(feature_id, None)

    def clear(self) -> None:
        self._records.clear()
        self._eval_counter.clear()

    # ------------------------------------------------------------------
    # 过滤 / 搜索
    # ------------------------------------------------------------------

    def filter(
        self,
        status:   Optional[FeatureStatus] = None,
        category: Optional[str]           = None,
        tag:      Optional[str]           = None,
        author:   Optional[str]           = None,
        active_only: bool                 = False,
    ) -> List[FeatureRecord]:
        result = list(self._records.values())
        if status is not None:
            result = [r for r in result if r.status == status]
        if category is not None:
            result = [r for r in result
                      if category.lower() in r.category.lower()]
        if tag is not None:
            result = [r for r in result if tag in r.tags]
        if author is not None:
            result = [r for r in result
                      if author.lower() in r.author.lower()]
        if active_only:
            result = [r for r in result
                      if r.deprecated_at is None]
        return result

    def search(self, keyword: str) -> List[FeatureRecord]:
        kw = keyword.lower()
        return [
            r for r in self._records.values()
            if kw in r.name.lower()
            or kw in r.description.lower()
            or kw in r.category.lower()
            or kw in r.formula.lower()
            or kw in r.author.lower()
            or any(kw in t.lower() for t in r.tags)
        ]

    # ------------------------------------------------------------------
    # IC 指标更新
    # ------------------------------------------------------------------

    def update_ic_metrics(
        self,
        feature_id: str,
        ic:         float,
        rank_ic:    float,
        ir:         float,
        icir:       float,
        coverage:   float,
        period:     str = "",
        dataset_id: str = "",
    ) -> Optional[ICRecord]:
        record = self._records.get(feature_id)
        if record is None:
            return None

        count = self._eval_counter.get(feature_id, 0) + 1
        self._eval_counter[feature_id] = count

        eval_rec = ICRecord(
            eval_id    = f"IC-{feature_id}-{count:03d}",
            ic         = ic,
            rank_ic    = rank_ic,
            ir         = ir,
            icir       = icir,
            coverage   = coverage,
            period     = period,
            dataset_id = dataset_id,
            evaluated_at = datetime.now(),
        )
        record.ic_history.append(eval_rec)

        # 更新最新指标（用最近一次评估）
        record.ic       = ic
        record.rank_ic  = rank_ic
        record.ir       = ir
        record.icir     = icir
        record.coverage = coverage
        record.updated_at = datetime.now()
        return eval_rec

    def get_ic_history(self, feature_id: str) -> List[ICRecord]:
        record = self._records.get(feature_id)
        return list(record.ic_history) if record else []

    # ------------------------------------------------------------------
    # 废弃
    # ------------------------------------------------------------------

    def deprecate(self, feature_id: str, reason: str = "") -> None:
        record = self._records.get(feature_id)
        if record:
            record.status          = FeatureStatus.DEPRECATED
            record.deprecated_at   = datetime.now()
            record.deprecated_reason = reason
            record.updated_at      = datetime.now()

    def restore(self, feature_id: str) -> None:
        """从废弃状态恢复为 EXPERIMENTAL。"""
        record = self._records.get(feature_id)
        if record and record.status == FeatureStatus.DEPRECATED:
            record.status           = FeatureStatus.EXPERIMENTAL
            record.deprecated_at    = None
            record.deprecated_reason = ""
            record.updated_at       = datetime.now()

    # ------------------------------------------------------------------
    # 依赖关系
    # ------------------------------------------------------------------

    def add_dependency(self, feature_id: str, dep_id: str) -> None:
        record = self._records.get(feature_id)
        if record and dep_id not in record.dependencies:
            record.dependencies.append(dep_id)
            record.updated_at = datetime.now()

    def remove_dependency(self, feature_id: str, dep_id: str) -> None:
        record = self._records.get(feature_id)
        if record and dep_id in record.dependencies:
            record.dependencies.remove(dep_id)
            record.updated_at = datetime.now()

    def add_dataset(self, feature_id: str, dataset_id: str) -> None:
        record = self._records.get(feature_id)
        if record and dataset_id not in record.dataset_ids:
            record.dataset_ids.append(dataset_id)
            record.updated_at = datetime.now()

    def get_dependents(self, feature_id: str) -> List[str]:
        """返回直接依赖本因子的下游因子 ID。"""
        return [
            r.feature_id
            for r in self._records.values()
            if feature_id in r.dependencies
        ]

    # ------------------------------------------------------------------
    # 统计辅助
    # ------------------------------------------------------------------

    def top_by_ic(self, n: int = 10) -> List[FeatureRecord]:
        active = [r for r in self._records.values()
                  if r.deprecated_at is None]
        return sorted(active, key=lambda r: abs(r.ic), reverse=True)[:n]

    def top_by_icir(self, n: int = 10) -> List[FeatureRecord]:
        active = [r for r in self._records.values()
                  if r.deprecated_at is None]
        return sorted(active, key=lambda r: abs(r.icir), reverse=True)[:n]
