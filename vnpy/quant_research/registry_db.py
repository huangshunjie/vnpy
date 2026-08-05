"""
基于SQLite的Registry实现

所有Registry类的数据库持久化版本
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from .database import get_database, to_json, from_json
from .model.experiment_model import ExperimentRecord
from .model.dataset_model import DatasetRecord, DatasetSnapshot
from .model.feature_model import FeatureRecord
from .model.strategy_model import StrategyRecord
from .model.backtest_model import BacktestRecord
from .model.report_model import ReportRecord, ReportSection
from .model.log_model import LogRecord
from .constant import *


class ExperimentRegistryDB:
    """实验注册表 - 数据库版本"""
    
    def __init__(self):
        self.db = get_database()
    
    def create(self, record: ExperimentRecord):
        """创建实验"""
        self.db.execute("""
            INSERT INTO experiments 
            (experiment_id, name, description, status, tags, params, metrics, 
             notes, starred, created_by, parent_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.experiment_id, record.name, record.description, 
            record.status.value, to_json(record.tags), to_json(record.params),
            to_json(record.metrics), record.notes, int(record.starred),
            record.created_by, record.parent_id,
            record.created_at.isoformat(), record.updated_at.isoformat()
        ))
        self.db.commit()
    
    def update(self, record: ExperimentRecord):
        """更新实验"""
        self.db.execute("""
            UPDATE experiments SET 
                name=?, description=?, status=?, tags=?, params=?, metrics=?,
                notes=?, starred=?, updated_at=?
            WHERE experiment_id=?
        """, (
            record.name, record.description, record.status.value,
            to_json(record.tags), to_json(record.params), to_json(record.metrics),
            record.notes, int(record.starred), record.updated_at.isoformat(),
            record.experiment_id
        ))
        self.db.commit()
    
    def delete(self, experiment_id: str):
        """删除实验"""
        self.db.execute("DELETE FROM experiments WHERE experiment_id=?", (experiment_id,))
        self.db.commit()
    
    def get(self, experiment_id: str) -> Optional[ExperimentRecord]:
        """获取实验"""
        row = self.db.fetchone(
            "SELECT * FROM experiments WHERE experiment_id=?", 
            (experiment_id,)
        )
        return self._row_to_record(row) if row else None
    
    def list_all(self) -> List[ExperimentRecord]:
        """列出所有实验"""
        rows = self.db.fetchall("SELECT * FROM experiments ORDER BY created_at DESC")
        return [self._row_to_record(row) for row in rows]
    
    def filter(self, status=None, tag=None, starred=None) -> List[ExperimentRecord]:
        """筛选实验"""
        sql = "SELECT * FROM experiments WHERE 1=1"
        params = []
        
        if status:
            sql += " AND status=?"
            params.append(status.value)
        if starred is not None:
            sql += " AND starred=?"
            params.append(int(starred))
        if tag:
            sql += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')
        
        sql += " ORDER BY created_at DESC"
        rows = self.db.fetchall(sql, tuple(params) if params else None)
        return [self._row_to_record(row) for row in rows]
    
    def search(self, keyword: str) -> List[ExperimentRecord]:
        """搜索实验"""
        sql = """
            SELECT * FROM experiments 
            WHERE name LIKE ? OR description LIKE ? OR tags LIKE ?
            ORDER BY created_at DESC
        """
        pattern = f"%{keyword}%"
        rows = self.db.fetchall(sql, (pattern, pattern, pattern))
        return [self._row_to_record(row) for row in rows]
    
    def clear(self):
        """清空所有实验"""
        self.db.execute("DELETE FROM experiments")
        self.db.commit()
    
    def _row_to_record(self, row) -> ExperimentRecord:
        """将数据库行转换为记录对象"""
        return ExperimentRecord(
            experiment_id=row['experiment_id'],
            name=row['name'],
            description=row['description'] or "",
            status=ExperimentStatus(row['status']),
            tags=from_json(row['tags']) or [],
            params=from_json(row['params']) or {},
            metrics=from_json(row['metrics']) or {},
            notes=row['notes'] or "",
            starred=bool(row['starred']),
            created_by=row['created_by'] or "",
            parent_id=row['parent_id'],
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
        )


class DatasetRegistryDB:
    """数据集注册表 - 数据库版本"""
    
    def __init__(self):
        self.db = get_database()
    
    def create(self, record: DatasetRecord):
        """创建数据集"""
        self.db.execute("""
            INSERT INTO datasets 
            (dataset_id, name, version, description, source, status, symbols,
             start_date, end_date, fields, row_count, size_mb, quality_score,
             quality_metrics, tags, dependencies, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.dataset_id, record.name, record.version, record.description,
            record.source, record.status.value, to_json(record.symbols),
            record.start_date, record.end_date, to_json(record.fields),
            record.row_count, record.size_mb, record.quality_score,
            to_json(record.quality_metrics), to_json(record.tags),
            to_json(record.dependencies), record.created_by,
            record.created_at.isoformat(), record.updated_at.isoformat()
        ))
        self.db.commit()
    
    def update(self, record: DatasetRecord):
        """更新数据集"""
        self.db.execute("""
            UPDATE datasets SET 
                name=?, version=?, description=?, source=?, status=?, symbols=?,
                start_date=?, end_date=?, fields=?, row_count=?, size_mb=?,
                quality_score=?, quality_metrics=?, tags=?, dependencies=?, updated_at=?
            WHERE dataset_id=?
        """, (
            record.name, record.version, record.description, record.source,
            record.status.value, to_json(record.symbols), record.start_date,
            record.end_date, to_json(record.fields), record.row_count,
            record.size_mb, record.quality_score, to_json(record.quality_metrics),
            to_json(record.tags), to_json(record.dependencies),
            record.updated_at.isoformat(), record.dataset_id
        ))
        self.db.commit()
    
    def delete(self, dataset_id: str):
        """删除数据集"""
        self.db.execute("DELETE FROM datasets WHERE dataset_id=?", (dataset_id,))
        self.db.commit()
    
    def get(self, dataset_id: str) -> Optional[DatasetRecord]:
        """获取数据集"""
        row = self.db.fetchone("SELECT * FROM datasets WHERE dataset_id=?", (dataset_id,))
        return self._row_to_record(row) if row else None
    
    def list_all(self) -> List[DatasetRecord]:
        """列出所有数据集"""
        rows = self.db.fetchall("SELECT * FROM datasets ORDER BY created_at DESC")
        return [self._row_to_record(row) for row in rows]
    
    def filter(self, status=None, source=None, tag=None) -> List[DatasetRecord]:
        """筛选数据集"""
        sql = "SELECT * FROM datasets WHERE 1=1"
        params = []
        
        if status:
            sql += " AND status=?"
            params.append(status.value)
        if source:
            sql += " AND source LIKE ?"
            params.append(f"%{source}%")
        if tag:
            sql += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')
        
        sql += " ORDER BY created_at DESC"
        rows = self.db.fetchall(sql, tuple(params) if params else None)
        return [self._row_to_record(row) for row in rows]
    
    def search(self, keyword: str) -> List[DatasetRecord]:
        """搜索数据集"""
        sql = """
            SELECT * FROM datasets 
            WHERE name LIKE ? OR description LIKE ? OR tags LIKE ? OR symbols LIKE ?
            ORDER BY created_at DESC
        """
        pattern = f"%{keyword}%"
        rows = self.db.fetchall(sql, (pattern, pattern, pattern, pattern))
        return [self._row_to_record(row) for row in rows]
    
    def take_snapshot(self, dataset_id: str) -> Optional[DatasetSnapshot]:
        """创建快照"""
        dataset = self.get(dataset_id)
        if not dataset:
            return None
        
        snapshot = DatasetSnapshot(
            snapshot_id=f"SNAP-{dataset_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            dataset_id=dataset_id,
            version=dataset.version,
            row_count=dataset.row_count,
            quality_score=dataset.quality_score,
            created_at=datetime.now()
        )
        
        self.db.execute("""
            INSERT INTO dataset_snapshots 
            (snapshot_id, dataset_id, version, row_count, quality_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            snapshot.snapshot_id, snapshot.dataset_id, snapshot.version,
            snapshot.row_count, snapshot.quality_score, snapshot.created_at.isoformat()
        ))
        self.db.commit()
        return snapshot
    
    def clear(self):
        """清空所有数据集"""
        self.db.execute("DELETE FROM datasets")
        self.db.execute("DELETE FROM dataset_snapshots")
        self.db.commit()
    
    def _row_to_record(self, row) -> DatasetRecord:
        """将数据库行转换为记录对象"""
        return DatasetRecord(
            dataset_id=row['dataset_id'],
            name=row['name'],
            version=row['version'] or "v1.0",
            description=row['description'] or "",
            source=row['source'] or "",
            status=DatasetStatus(row['status']),
            symbols=from_json(row['symbols']) or [],
            start_date=row['start_date'] or "",
            end_date=row['end_date'] or "",
            fields=from_json(row['fields']) or [],
            row_count=row['row_count'] or 0,
            size_mb=row['size_mb'] or 0.0,
            quality_score=row['quality_score'] or 0.0,
            quality_metrics=from_json(row['quality_metrics']) or {},
            tags=from_json(row['tags']) or [],
            dependencies=from_json(row['dependencies']) or [],
            created_by=row['created_by'] or "",
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
        )


# 注意：其他Registry类的实现类似，这里只展示核心两个
# 在实际使用中，需要为所有Registry类创建对应的DB版本
