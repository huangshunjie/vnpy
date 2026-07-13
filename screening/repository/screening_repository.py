"""
screening/repository/screening_repository.py

选股平台持久化（Phase 2：实现 Universe Config 存取）。
"""

from __future__ import annotations
import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..model.universe import UniverseConfig
from ..model.condition import ConditionTree
from ..model.factor_score import FactorRankConfig
from ..model.screening_result import ScreeningResult
from ..model.template import ScreeningTemplate


class ScreeningRepository(ABC):
    @abstractmethod
    def save_universe_config(self, config: UniverseConfig) -> None: ...
    @abstractmethod
    def load_universe_config(self, name: str) -> Optional[UniverseConfig]: ...
    @abstractmethod
    def list_universe_configs(self) -> List[str]: ...
    @abstractmethod
    def delete_universe_config(self, name: str) -> None: ...

    @abstractmethod
    def save_condition_tree(self, tree: ConditionTree) -> None: ...
    @abstractmethod
    def load_condition_tree(self, name: str) -> Optional[ConditionTree]: ...
    @abstractmethod
    def list_condition_trees(self) -> List[str]: ...
    @abstractmethod
    def delete_condition_tree(self, name: str) -> None: ...

    @abstractmethod
    def save_factor_config(self, config: FactorRankConfig) -> None: ...
    @abstractmethod
    def load_factor_config(self, name: str) -> Optional[FactorRankConfig]: ...
    @abstractmethod
    def list_factor_configs(self) -> List[str]: ...

    @abstractmethod
    def save_screening_result(self, result: ScreeningResult) -> None: ...
    @abstractmethod
    def load_screening_result(self, run_id: str) -> Optional[ScreeningResult]: ...
    @abstractmethod
    def list_screening_results(self, limit: int = 50) -> List[str]: ...

    @abstractmethod
    def save_template(self, template: ScreeningTemplate) -> None: ...
    @abstractmethod
    def load_template(self, template_id: str) -> Optional[ScreeningTemplate]: ...
    @abstractmethod
    def list_templates(self) -> List[ScreeningTemplate]: ...
    @abstractmethod
    def delete_template(self, template_id: str) -> None: ...


class SqliteScreeningRepository(ScreeningRepository):
    """
    SQLite 持久化实现。
    Phase 2：实现 Universe Config 存取。
    其余方法 Phase 3+ 按需填充。
    """

    def __init__(self, db_path: Optional[str] = None) -> None:
        if db_path:
            self._db_path = Path(db_path)
        else:
            self._db_path = Path.home() / ".vntrader" / "screening.db"
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(
                str(self._db_path), check_same_thread=False
            )
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS universe_config (
                name        TEXT PRIMARY KEY,
                data_json   TEXT NOT NULL,
                updated_at  TEXT
            );
            CREATE TABLE IF NOT EXISTS condition_tree (
                name        TEXT PRIMARY KEY,
                data_json   TEXT NOT NULL,
                updated_at  TEXT
            );
            CREATE TABLE IF NOT EXISTS factor_config (
                name        TEXT PRIMARY KEY,
                data_json   TEXT NOT NULL,
                updated_at  TEXT
            );
            CREATE TABLE IF NOT EXISTS screening_result (
                run_id       TEXT PRIMARY KEY,
                data_json    TEXT NOT NULL,
                generated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS template (
                template_id TEXT PRIMARY KEY,
                name        TEXT,
                category    TEXT,
                data_json   TEXT NOT NULL,
                updated_at  TEXT
            );
        """)
        conn.commit()

    # ── Universe Config（Phase 2 实现）────────────────────────────────

    def save_universe_config(self, config: UniverseConfig) -> None:
        conn = self._get_conn()
        now = str(datetime.now())[:19]
        conn.execute(
            "INSERT OR REPLACE INTO universe_config(name, data_json, updated_at)"
            " VALUES (?, ?, ?)",
            (config.name, json.dumps(config.to_dict(), ensure_ascii=False), now),
        )
        conn.commit()

    def load_universe_config(self, name: str) -> Optional[UniverseConfig]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data_json FROM universe_config WHERE name=?", (name,)
        ).fetchone()
        if row:
            try:
                return UniverseConfig.from_dict(json.loads(row[0]))
            except Exception:
                return None
        return None

    def list_universe_configs(self) -> List[str]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT name FROM universe_config ORDER BY updated_at DESC"
        ).fetchall()
        return [r[0] for r in rows]

    def delete_universe_config(self, name: str) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM universe_config WHERE name=?", (name,))
        conn.commit()

    # ── Condition Tree（Phase 3 实现）────────────────────────────────

    def save_condition_tree(self, tree: ConditionTree) -> None:
        conn = self._get_conn()
        now = str(datetime.now())[:19]
        conn.execute(
            "INSERT OR REPLACE INTO condition_tree(name, data_json, updated_at)"
            " VALUES (?, ?, ?)",
            (tree.name, json.dumps(tree.to_dict(), ensure_ascii=False), now),
        )
        conn.commit()

    def load_condition_tree(self, name: str) -> Optional[ConditionTree]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data_json FROM condition_tree WHERE name=?", (name,)
        ).fetchone()
        if row:
            try:
                return ConditionTree.from_dict(json.loads(row[0]))
            except Exception:
                return None
        return None

    def list_condition_trees(self) -> List[str]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT name FROM condition_tree ORDER BY updated_at DESC"
        ).fetchall()
        return [r[0] for r in rows]

    def delete_condition_tree(self, name: str) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM condition_tree WHERE name=?", (name,))
        conn.commit()

    # ── Factor Config（Phase 4 实现）──────────────────────────────────

    def save_factor_config(self, config: FactorRankConfig) -> None:
        conn = self._get_conn()
        now = str(datetime.now())[:19]
        conn.execute(
            "INSERT OR REPLACE INTO factor_config(name, data_json, updated_at)"
            " VALUES (?, ?, ?)",
            (config.name, json.dumps(config.to_dict(), ensure_ascii=False), now),
        )
        conn.commit()

    def load_factor_config(self, name: str) -> Optional[FactorRankConfig]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data_json FROM factor_config WHERE name=?", (name,)
        ).fetchone()
        if row:
            try:
                return FactorRankConfig.from_dict(json.loads(row[0]))
            except Exception:
                return None
        return None

    def list_factor_configs(self) -> List[str]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT name FROM factor_config ORDER BY updated_at DESC"
        ).fetchall()
        return [r[0] for r in rows]

    # ── Screening Result（Phase 5 实现）──────────────────────────────

    def save_screening_result(self, result: ScreeningResult) -> None:
        pass

    def load_screening_result(self, run_id: str) -> Optional[ScreeningResult]:
        return None

    def list_screening_results(self, limit: int = 50) -> List[str]:
        return []

    # ── Template（Phase 8 完整实现）─────────────────────────────────

    def save_template(self, template: ScreeningTemplate) -> None:
        conn = self._get_conn()
        now = str(datetime.now())[:19]
        conn.execute(
            "INSERT OR REPLACE INTO template"
            "(template_id, name, category, data_json, updated_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (template.template_id, template.name,
             template.category.value,
             json.dumps(template.to_dict(), ensure_ascii=False), now),
        )
        conn.commit()

    def load_template(self, template_id: str) -> Optional[ScreeningTemplate]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data_json FROM template WHERE template_id=?", (template_id,)
        ).fetchone()
        if row:
            try:
                return ScreeningTemplate.from_dict(json.loads(row[0]))
            except Exception:
                return None
        return None

    def load_template_by_name(self, name: str) -> Optional[ScreeningTemplate]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT data_json FROM template WHERE name=? ORDER BY updated_at DESC LIMIT 1",
            (name,)
        ).fetchone()
        if row:
            try:
                return ScreeningTemplate.from_dict(json.loads(row[0]))
            except Exception:
                return None
        return None

    def list_templates(self) -> List[ScreeningTemplate]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT data_json FROM template ORDER BY updated_at DESC"
        ).fetchall()
        result = []
        for row in rows:
            try:
                result.append(ScreeningTemplate.from_dict(json.loads(row[0])))
            except Exception:
                pass
        return result

    def delete_template(self, template_id: str) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM template WHERE template_id=?", (template_id,))
        conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
