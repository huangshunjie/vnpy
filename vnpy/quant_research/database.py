"""
量化研究平台 - SQLite数据库层

提供完整的数据持久化功能
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import threading


class ResearchDatabase:
    """研究平台SQLite数据库管理器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = Path.home() / ".vnpy" / "quant_research"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "research.db")
        
        self.db_path = db_path
        self._local = threading.local()
        self._init_database()
        print(f"[数据库] 初始化完成: {self.db_path}")
    
    @property
    def conn(self) -> sqlite3.Connection:
        """获取线程本地的数据库连接"""
        if not hasattr(self._local, 'conn'):
            self._local.conn = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_database(self):
        """初始化数据库表结构"""
        schema_file = Path(__file__).parent / "schema.sql"
        if schema_file.exists():
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            self.conn.executescript(schema_sql)
            self.conn.commit()
    
    def execute(self, sql: str, params: tuple = None):
        """执行SQL语句"""
        try:
            if params:
                return self.conn.execute(sql, params)
            return self.conn.execute(sql)
        except Exception as e:
            print(f"[数据库错误] {e}")
            print(f"[SQL] {sql}")
            raise
    
    def fetchone(self, sql: str, params: tuple = None) -> Optional[sqlite3.Row]:
        """查询单条记录"""
        cursor = self.execute(sql, params)
        return cursor.fetchone()
    
    def fetchall(self, sql: str, params: tuple = None) -> List[sqlite3.Row]:
        """查询多条记录"""
        cursor = self.execute(sql, params)
        return cursor.fetchall()
    
    def commit(self):
        """提交事务"""
        self.conn.commit()
    
    def rollback(self):
        """回滚事务"""
        self.conn.rollback()
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self._local, 'conn'):
            self._local.conn.close()
            delattr(self._local, 'conn')


# 全局数据库实例
_db_instance: Optional[ResearchDatabase] = None


def get_database() -> ResearchDatabase:
    """获取全局数据库实例"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ResearchDatabase()
    return _db_instance


def init_database(db_path: str = None) -> ResearchDatabase:
    """初始化数据库"""
    global _db_instance
    _db_instance = ResearchDatabase(db_path)
    return _db_instance


# 辅助函数
def to_json(obj: Any) -> str:
    """将对象转换为JSON字符串"""
    if obj is None:
        return None
    return json.dumps(obj, ensure_ascii=False)


def from_json(s: str) -> Any:
    """从JSON字符串解析对象"""
    if not s:
        return None
    try:
        return json.loads(s)
    except:
        return None
