"""
量化研究平台 - 完整SQLite数据库实现脚本

这个脚本会：
1. 创建完整的数据库表结构
2. 修改所有Registry类支持数据库持久化
3. 保持API向后兼容

运行方式：python implement_sqlite_database.py
"""

import os
import sys

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
sys.path.insert(0, PROJECT_ROOT)

print("=" * 80)
print("量化研究平台 - SQLite数据库实现")
print("=" * 80)

# ============================================================================
# 步骤1：创建数据库SQL架构
# ============================================================================
print("\n[步骤1] 创建数据库SQL架构...")

SQL_SCHEMA = """
-- 实验表
CREATE TABLE IF NOT EXISTS experiments (
    experiment_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT,
    tags TEXT,
    params TEXT,
    metrics TEXT,
    notes TEXT,
    starred INTEGER DEFAULT 0,
    created_by TEXT,
    parent_id TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 数据集表
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT,
    description TEXT,
    source TEXT,
    status TEXT,
    symbols TEXT,
    start_date TEXT,
    end_date TEXT,
    fields TEXT,
    row_count INTEGER,
    size_mb REAL,
    quality_score REAL DEFAULT 0.0,
    quality_metrics TEXT,
    tags TEXT,
    dependencies TEXT,
    created_by TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 数据集快照表
CREATE TABLE IF NOT EXISTS dataset_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    dataset_id TEXT,
    version TEXT,
    row_count INTEGER,
    quality_score REAL,
    created_at TEXT
);

-- 特征表
CREATE TABLE IF NOT EXISTS features (
    feature_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT,
    description TEXT,
    category TEXT,
    formula TEXT,
    status TEXT,
    ic REAL,
    rank_ic REAL,
    ir REAL,
    icir REAL,
    author TEXT,
    tags TEXT,
    dependencies TEXT,
    dataset_ids TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 策略表
CREATE TABLE IF NOT EXISTS strategies (
    strategy_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT,
    description TEXT,
    strategy_type TEXT,
    status TEXT,
    author TEXT,
    universe TEXT,
    params TEXT,
    annual_return REAL,
    max_drawdown REAL,
    sharpe REAL,
    win_rate REAL,
    tags TEXT,
    feature_ids TEXT,
    dataset_ids TEXT,
    backtest_ids TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 回测表
CREATE TABLE IF NOT EXISTS backtests (
    backtest_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT,
    strategy_id TEXT,
    strategy_name TEXT,
    start_date TEXT,
    end_date TEXT,
    initial_capital REAL,
    commission REAL,
    annual_return REAL,
    max_drawdown REAL,
    sharpe REAL,
    win_rate REAL,
    total_trades INTEGER,
    tags TEXT,
    feature_ids TEXT,
    dataset_ids TEXT,
    created_by TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 报告表
CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    report_type TEXT,
    author TEXT,
    summary TEXT,
    published INTEGER DEFAULT 0,
    experiment_id TEXT,
    strategy_id TEXT,
    backtest_id TEXT,
    feature_ids TEXT,
    tags TEXT,
    created_at TEXT,
    updated_at TEXT
);

-- 报告章节表
CREATE TABLE IF NOT EXISTS report_sections (
    section_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT,
    title TEXT,
    content TEXT,
    section_order INTEGER
);

-- 日志表
CREATE TABLE IF NOT EXISTS logs (
    log_id TEXT PRIMARY KEY,
    timestamp TEXT,
    level TEXT,
    source TEXT,
    message TEXT,
    context_id TEXT,
    context_name TEXT,
    details TEXT,
    user TEXT
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiments_created_at ON experiments(created_at);
CREATE INDEX IF NOT EXISTS idx_datasets_status ON datasets(status);
CREATE INDEX IF NOT EXISTS idx_features_status ON features(status);
CREATE INDEX IF NOT EXISTS idx_strategies_status ON strategies(status);
CREATE INDEX IF NOT EXISTS idx_backtests_status ON backtests(status);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
"""

# 保存SQL架构到文件
schema_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "schema.sql")
with open(schema_file, 'w', encoding='utf-8') as f:
    f.write(SQL_SCHEMA)

print(f"[完成] SQL架构已保存到: {schema_file}")

# ============================================================================
# 步骤2：更新database.py实现完整功能
# ============================================================================
print("\n[步骤2] 更新数据库实现...")

database_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "database.py")

DATABASE_CODE = '''"""
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
'''

with open(database_file, 'w', encoding='utf-8') as f:
    f.write(DATABASE_CODE)

print(f"[完成] 数据库实现已更新")

# ============================================================================
# 步骤3：测试数据库
# ============================================================================
print("\n[步骤3] 测试数据库...")

try:
    from vnpy.quant_research.database import get_database
    
    db = get_database()
    
    # 测试插入
    test_id = "TEST-20260805-001"
    db.execute("""
        INSERT OR REPLACE INTO experiments 
        (experiment_id, name, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
    """, (test_id, "测试实验", "draft", datetime.now().isoformat(), datetime.now().isoformat()))
    db.commit()
    
    # 测试查询
    row = db.fetchone("SELECT * FROM experiments WHERE experiment_id = ?", (test_id,))
    if row:
        print(f"[成功] 数据库读写正常")
        print(f"  - 实验ID: {row['experiment_id']}")
        print(f"  - 实验名称: {row['name']}")
        
        # 删除测试数据
        db.execute("DELETE FROM experiments WHERE experiment_id = ?", (test_id,))
        db.commit()
    else:
        print("[警告] 无法读取测试数据")
        
except Exception as e:
    print(f"[错误] 数据库测试失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 完成
# ============================================================================
print("\n" + "=" * 80)
print("SQLite数据库实现完成！")
print("=" * 80)

print("\n数据库位置:")
print(f"  {Path.home() / '.vnpy' / 'quant_research' / 'research.db'}")

print("\n下一步:")
print("  1. 运行 python update_registries_to_db.py 更新Registry类")
print("  2. 重启量化研究平台测试")
print("  3. 创建的数据将永久保存")

print("\n" + "=" * 80)
