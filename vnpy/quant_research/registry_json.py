"""
registry_json.py - 改进版

基于JSON文件的持久化Registry实现，正确处理枚举类型
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from .model.experiment_model import ExperimentRecord
from .model.dataset_model import DatasetRecord
from .registry.experiment_registry import ExperimentRegistry
from .registry.dataset_registry import DatasetRegistry


# JSON文件保存路径
DEFAULT_DATA_DIR = Path.home() / ".vnpy" / "quant_research"
DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)


def serialize_record(record: Any) -> dict:
    """将Record对象序列化为字典，正确处理枚举和datetime"""
    data = {}
    for key, value in record.__dict__.items():
        if value is None:
            data[key] = None
        elif isinstance(value, Enum):
            # 枚举类型：保存值而不是对象
            data[key] = value.value
        elif isinstance(value, datetime):
            # datetime：转为ISO格式字符串
            data[key] = value.isoformat()
        elif isinstance(value, (list, dict, str, int, float, bool)):
            # 基本类型：直接保存
            data[key] = value
        else:
            # 其他类型：转为字符串
            data[key] = str(value)
    return data


class ExperimentRegistryJSON(ExperimentRegistry):
    """基于JSON文件的实验Registry"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        super().__init__()
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.data_file = self.data_dir / "experiments.json"
        self._load_from_file()
    
    def _load_from_file(self):
        """从JSON文件加载数据"""
        if not self.data_file.exists():
            return
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 恢复数据到内存
            from .constant import ExperimentStatus
            
            for exp_data in data:
                # 恢复datetime对象
                if 'created_at' in exp_data and exp_data['created_at']:
                    exp_data['created_at'] = datetime.fromisoformat(exp_data['created_at'])
                if 'updated_at' in exp_data and exp_data['updated_at']:
                    exp_data['updated_at'] = datetime.fromisoformat(exp_data['updated_at'])
                if 'started_at' in exp_data and exp_data['started_at']:
                    exp_data['started_at'] = datetime.fromisoformat(exp_data['started_at'])
                if 'completed_at' in exp_data and exp_data['completed_at']:
                    exp_data['completed_at'] = datetime.fromisoformat(exp_data['completed_at'])
                
                # 恢复枚举对象
                if 'status' in exp_data and isinstance(exp_data['status'], str):
                    try:
                        exp_data['status'] = ExperimentStatus(exp_data['status'])
                    except:
                        exp_data['status'] = ExperimentStatus.DRAFT
                
                # 创建Record对象
                record = ExperimentRecord(**exp_data)
                self._records[record.experiment_id] = record
            
            print(f"[JSON] 加载了 {len(self._records)} 个实验")
        except Exception as e:
            print(f"[JSON] 加载实验失败: {e}")
            # 备份损坏的文件
            if self.data_file.exists():
                backup_file = self.data_file.with_suffix('.json.backup')
                import shutil
                shutil.copy(self.data_file, backup_file)
                print(f"[JSON] 已备份损坏的文件到: {backup_file}")
    
    def _save_to_file(self):
        """保存数据到JSON文件"""
        try:
            # 序列化所有记录
            data = [serialize_record(exp) for exp in self._records.values()]
            
            # 写入文件
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"[JSON] 保存实验失败: {e}")
            import traceback
            traceback.print_exc()
    
    def create(self, record: ExperimentRecord) -> ExperimentRecord:
        """创建实验记录"""
        result = super().create(record)
        self._save_to_file()
        return result
    
    def update(self, record: ExperimentRecord) -> None:
        """更新实验记录"""
        super().update(record)
        self._save_to_file()
    
    def delete(self, experiment_id: str) -> None:
        """删除实验记录"""
        super().delete(experiment_id)
        self._save_to_file()
    
    def clear(self) -> None:
        """清空所有记录"""
        super().clear()
        self._save_to_file()


class DatasetRegistryJSON(DatasetRegistry):
    """基于JSON文件的数据集Registry"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        super().__init__()
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.data_file = self.data_dir / "datasets.json"
        self._load_from_file()
    
    def _load_from_file(self):
        """从JSON文件加载数据"""
        if not self.data_file.exists():
            return
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 恢复数据到内存
            from .constant import DatasetStatus
            
            for ds_data in data:
                # 恢复datetime对象
                if 'created_at' in ds_data and ds_data['created_at']:
                    ds_data['created_at'] = datetime.fromisoformat(ds_data['created_at'])
                if 'updated_at' in ds_data and ds_data['updated_at']:
                    ds_data['updated_at'] = datetime.fromisoformat(ds_data['updated_at'])
                
                # 恢复枚举对象
                if 'status' in ds_data and isinstance(ds_data['status'], str):
                    try:
                        ds_data['status'] = DatasetStatus(ds_data['status'])
                    except:
                        ds_data['status'] = DatasetStatus.DRAFT
                
                # 创建Record对象
                record = DatasetRecord(**ds_data)
                self._records[record.dataset_id] = record
            
            print(f"[JSON] 加载了 {len(self._records)} 个数据集")
        except Exception as e:
            print(f"[JSON] 加载数据集失败: {e}")
            # 备份损坏的文件
            if self.data_file.exists():
                backup_file = self.data_file.with_suffix('.json.backup')
                import shutil
                shutil.copy(self.data_file, backup_file)
                print(f"[JSON] 已备份损坏的文件到: {backup_file}")
    
    def _save_to_file(self):
        """保存数据到JSON文件"""
        try:
            # 序列化所有记录
            data = [serialize_record(ds) for ds in self._records.values()]
            
            # 写入文件
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"[JSON] 保存数据集失败: {e}")
            import traceback
            traceback.print_exc()
    
    def create(self, record: DatasetRecord) -> DatasetRecord:
        """创建数据集记录"""
        result = super().create(record)
        self._save_to_file()
        return result
    
    def update(self, record: DatasetRecord) -> None:
        """更新数据集记录"""
        super().update(record)
        self._save_to_file()
    
    def delete(self, dataset_id: str) -> None:
        """删除数据集记录"""
        super().delete(dataset_id)
        self._save_to_file()
    
    def clear(self) -> None:
        """清空所有记录"""
        super().clear()
        self._save_to_file()
