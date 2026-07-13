"""
research_ops/repository/memory.py

InMemoryRepository — 基于字典的内存实现，开发/测试默认使用。
线程不安全（单线程 UI 场景足够），后续可加锁。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, TypeVar
from .base import AbstractRepository

T = TypeVar("T")

# 用于获取实体 ID 的属性名映射（各实体的主键字段名）
_ID_FIELDS = {
    "WorkspaceRecord":    "workspace_id",
    "ProjectRecord":      "project_id",
    "FolderRecord":       "folder_id",
    "ExperimentRecord":   "experiment_id",
    "RunRecord":          "run_id",
    "DatasetEntry":       "dataset_id",
    "FeatureEntry":       "feature_id",
    "StrategyEntry":      "strategy_id",
    "ModelEntry":         "model_id",
    "PipelineRecord":     "pipeline_id",
    "ReportRecord":       "report_id",
    "ReportTemplate":     "template_id",
    "KnowledgeNote":      "note_id",
    "ExperienceCard":     "card_id",
    "FailureCaseRecord":  "case_id",
    "ApprovalRequest":    "request_id",
    "FreezeRecord":       "freeze_id",
    "AuditLog":           "log_id",
}

_DEFAULT_SEARCH_FIELDS = ["name", "title", "description"]


def _get_id(entity: Any) -> str:
    """从实体对象中提取主键值。"""
    cls_name = type(entity).__name__
    id_field = _ID_FIELDS.get(cls_name)
    if id_field:
        return getattr(entity, id_field, "")
    # 兜底：尝试常见属性名
    for attr in ("id", "entity_id", "record_id"):
        val = getattr(entity, attr, None)
        if val is not None:
            return str(val)
    raise AttributeError(
        f"Cannot determine ID field for {cls_name}. "
        f"Register it in _ID_FIELDS."
    )


class InMemoryRepository(AbstractRepository[T]):
    """
    纯内存字典实现。
    泛型 T 在实例化时通过 Python duck-typing 自动适配，
    无需显式指定类型参数。
    """

    def __init__(self) -> None:
        self._store: Dict[str, T] = {}

    # ------------------------------------------------------------------
    # 基础 CRUD
    # ------------------------------------------------------------------

    def save(self, entity: T) -> T:
        eid = _get_id(entity)
        self._store[eid] = entity
        return entity

    def get(self, entity_id: str) -> Optional[T]:
        return self._store.get(entity_id)

    def list(self) -> List[T]:
        return list(self._store.values())

    def delete(self, entity_id: str) -> bool:
        if entity_id in self._store:
            del self._store[entity_id]
            return True
        return False

    def exists(self, entity_id: str) -> bool:
        return entity_id in self._store

    def count(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        self._store.clear()

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def query(self, **filters: Any) -> List[T]:
        """
        等值过滤。支持：
        - 普通属性：status="active"
        - Enum 属性：status=ExperimentStatus.RUNNING（与 .value 同时匹配）
        """
        result = list(self._store.values())
        for key, expected in filters.items():
            if expected is None:
                continue
            filtered = []
            for entity in result:
                val = getattr(entity, key, None)
                if val is None:
                    continue
                # 支持 Enum 与其 .value 的比较
                val_cmp   = val.value   if hasattr(val,   "value") else val
                exp_cmp   = expected.value if hasattr(expected, "value") else expected
                if val_cmp == exp_cmp or val == expected:
                    filtered.append(entity)
            result = filtered
        return result

    def search(self, keyword: str, fields: Optional[List[str]] = None) -> List[T]:
        """大小写不敏感的关键字搜索。"""
        kw = keyword.lower()
        search_fields = fields or _DEFAULT_SEARCH_FIELDS
        result = []
        for entity in self._store.values():
            for f in search_fields:
                val = getattr(entity, f, None)
                if val is None:
                    continue
                if isinstance(val, str) and kw in val.lower():
                    result.append(entity)
                    break
                if isinstance(val, list):
                    if any(kw in str(item).lower() for item in val):
                        result.append(entity)
                        break
        return result

    # ------------------------------------------------------------------
    # 额外便利方法
    # ------------------------------------------------------------------

    def all_ids(self) -> List[str]:
        return list(self._store.keys())

    def get_batch(self, entity_ids: List[str]) -> List[T]:
        return [self._store[eid] for eid in entity_ids if eid in self._store]
