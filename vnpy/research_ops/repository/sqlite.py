"""
research_ops/repository/sqlite.py

SQLiteRepository — Stub，Phase 10 完整实现。
现在只继承 InMemoryRepository 保证可导入，
后续替换为真正的 SQLite 持久化实现时 Engine 层零改动。
"""
from __future__ import annotations
from .memory import InMemoryRepository


class SQLiteRepository(InMemoryRepository):
    """
    SQLite 持久化 Repository（Stub）。
    Phase 1 直接使用内存实现，Phase 10 升级为真正的 SQLite 后端。
    """

    def __init__(self, db_path: str = "") -> None:
        super().__init__()
        self._db_path = db_path
        # Phase 10: self._conn = sqlite3.connect(db_path)
        # Phase 10: self._ensure_tables()
