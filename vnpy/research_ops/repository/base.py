"""
research_ops/repository/base.py

AbstractRepository — 泛型存储接口。
所有子引擎通过此接口访问存储，禁止直接实例化具体实现。
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Iterator, List, Optional, TypeVar

T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    """泛型 Repository 接口。"""

    # ------------------------------------------------------------------
    # 基础 CRUD
    # ------------------------------------------------------------------

    @abstractmethod
    def save(self, entity: T) -> T:
        """新建或覆盖保存。"""

    @abstractmethod
    def get(self, entity_id: str) -> Optional[T]:
        """按 ID 查询，不存在返回 None。"""

    @abstractmethod
    def list(self) -> List[T]:
        """返回全部实体列表。"""

    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """删除，返回是否存在过。"""

    @abstractmethod
    def exists(self, entity_id: str) -> bool:
        """判断 ID 是否存在。"""

    @abstractmethod
    def count(self) -> int:
        """返回实体总数。"""

    @abstractmethod
    def clear(self) -> None:
        """清空所有数据（测试/重置用）。"""

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    @abstractmethod
    def query(self, **filters: Any) -> List[T]:
        """
        简单等值过滤查询。
        filters 中的 key 为实体属性名，value 为期望值。
        例如: repo.query(status="active", author="alice")
        """

    @abstractmethod
    def search(self, keyword: str, fields: Optional[List[str]] = None) -> List[T]:
        """
        全文关键字搜索，在 fields 指定的字段中查找（默认 name/description）。
        """

    # ------------------------------------------------------------------
    # 批量操作
    # ------------------------------------------------------------------

    def save_batch(self, entities: List[T]) -> List[T]:
        """批量保存，默认逐条调用 save()，子类可覆盖优化。"""
        return [self.save(e) for e in entities]

    def delete_batch(self, entity_ids: List[str]) -> int:
        """批量删除，返回实际删除数量。"""
        return sum(1 for eid in entity_ids if self.delete(eid))

    # ------------------------------------------------------------------
    # 迭代
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator[T]:
        return iter(self.list())

    def __len__(self) -> int:
        return self.count()
