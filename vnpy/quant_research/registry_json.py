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


# ─────────────────────────────────────────────────────────────────────
# ReportRegistryJSON — 报告持久化
# ─────────────────────────────────────────────────────────────────────

class ReportRegistryJSON:
    """基于JSON文件的报告Registry"""

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.data_file = self.data_dir / "reports.json"
        self._records = {}
        self._sec_counter = {}
        self._load_from_file()

    def _load_from_file(self):
        if not self.data_file.exists():
            return
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            from .model.report_model import ReportRecord, ReportSection
            from .constant import ReportFormat
            for r_data in data:
                # 恢复 datetime
                for dt_field in ('created_at', 'updated_at', 'published_at'):
                    if dt_field in r_data and r_data[dt_field]:
                        r_data[dt_field] = datetime.fromisoformat(r_data[dt_field])
                    elif dt_field in r_data:
                        r_data[dt_field] = None
                # 恢复枚举
                if 'report_format' in r_data and isinstance(r_data['report_format'], str):
                    try:
                        r_data['report_format'] = ReportFormat(r_data['report_format'])
                    except:
                        r_data['report_format'] = ReportFormat.MARKDOWN
                # 恢复章节列表
                if 'sections' in r_data and isinstance(r_data['sections'], list):
                    sections = []
                    for s in r_data['sections']:
                        if isinstance(s, dict):
                            sections.append(ReportSection(**s))
                        else:
                            sections.append(s)
                    r_data['sections'] = sections
                else:
                    r_data['sections'] = []
                record = ReportRecord(**r_data)
                self._records[record.report_id] = record
            print(f"[JSON] 加载了 {len(self._records)} 个报告")
        except Exception as e:
            print(f"[JSON] 加载报告失败: {e}")
            import traceback
            traceback.print_exc()

    def _save_to_file(self):
        try:
            data = []
            for rec in self._records.values():
                d = serialize_record(rec)
                # 特殊处理 sections 列表
                if hasattr(rec, 'sections') and rec.sections:
                    d['sections'] = [serialize_record(s) for s in rec.sections]
                else:
                    d['sections'] = []
                data.append(d)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[JSON] 保存报告失败: {e}")
            import traceback
            traceback.print_exc()

    def create(self, record):
        self._records[record.report_id] = record
        self._save_to_file()
        return record

    def get(self, report_id):
        return self._records.get(report_id)

    def list(self):
        return list(self._records.values())

    def update(self, record):
        self._records[record.report_id] = record
        self._save_to_file()

    def delete(self, report_id):
        self._records.pop(report_id, None)
        self._save_to_file()

    def clear(self):
        self._records.clear()
        self._sec_counter.clear()
        self._save_to_file()

    def filter(self, report_type=None, report_format=None, author=None, tag=None, published=None):
        result = list(self._records.values())
        if report_type is not None:
            result = [r for r in result if r.report_type == report_type]
        if report_format is not None:
            result = [r for r in result if r.report_format == report_format]
        if author is not None:
            result = [r for r in result if author.lower() in r.author.lower()]
        if tag is not None:
            result = [r for r in result if tag in r.tags]
        if published is not None:
            result = [r for r in result if r.is_published == published]
        return result

    def search(self, keyword):
        kw = keyword.lower()
        return [
            r for r in self._records.values()
            if kw in r.title.lower()
            or kw in r.description.lower()
            or kw in r.summary.lower()
            or kw in r.author.lower()
            or kw in r.report_type.lower()
            or any(kw in t.lower() for t in r.tags)
        ]

    # 章节管理
    def add_section(self, report_id, title, content="", order=0):
        rec = self._records.get(report_id)
        if rec:
            from .model.report_model import ReportSection
            sec_id = f"{report_id}-SEC{len(rec.sections)+1:03d}"
            section = ReportSection(
                section_id=sec_id,
                title=title,
                content=content,
                order=order,
            )
            rec.sections.append(section)
            self._save_to_file()
            return section
        return None

    def update_section(self, report_id, section_id, title="", content=""):
        rec = self._records.get(report_id)
        if rec:
            for s in rec.sections:
                if s.section_id == section_id:
                    if title:
                        s.title = title
                    if content:
                        s.content = content
                    break
            self._save_to_file()

    def remove_section(self, report_id, section_id):
        rec = self._records.get(report_id)
        if rec:
            rec.sections = [s for s in rec.sections if s.section_id != section_id]
            self._save_to_file()

    def publish(self, report_id):
        rec = self._records.get(report_id)
        if rec:
            rec.is_published = True
            rec.published_at = datetime.now()
            rec.updated_at = datetime.now()
            self._save_to_file()

    def unpublish(self, report_id):
        rec = self._records.get(report_id)
        if rec:
            rec.is_published = False
            rec.published_at = None
            rec.updated_at = datetime.now()
            self._save_to_file()


class StrategyRegistryJSON:
    """基于JSON文件的策略Registry"""
    
    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.data_file = self.data_dir / "strategies.json"
        self._records = {}
        self._load_from_file()
    
    def _load_from_file(self):
        if not self.data_file.exists():
            return
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            from .model.strategy_model import StrategyRecord
            from .constant import StrategyStatus
            for s_data in data:
                if 'created_at' in s_data and s_data['created_at']:
                    s_data['created_at'] = datetime.fromisoformat(s_data['created_at'])
                if 'updated_at' in s_data and s_data['updated_at']:
                    s_data['updated_at'] = datetime.fromisoformat(s_data['updated_at'])
                if 'status' in s_data and isinstance(s_data['status'], str):
                    try:
                        s_data['status'] = StrategyStatus(s_data['status'])
                    except:
                        s_data['status'] = StrategyStatus.DRAFT
                record = StrategyRecord(**s_data)
                self._records[record.strategy_id] = record
            print(f"[JSON] 加载了 {len(self._records)} 个策略")
        except Exception as e:
            print(f"[JSON] 加载策略失败: {e}")
    
    def _save_to_file(self):
        try:
            data = [serialize_record(s) for s in self._records.values()]
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[JSON] 保存策略失败: {e}")
    
    def create(self, record):
        if record.strategy_id in self._records:
            raise ValueError(
                f"Strategy ID '{record.strategy_id}' already exists "
                f"(existing: '{self._records[record.strategy_id].name}'). "
                f"Use update() to modify existing records."
            )
        self._records[record.strategy_id] = record
        self._save_to_file()
        return record
    
    def get(self, strategy_id):
        return self._records.get(strategy_id)
    
    def list(self):
        return list(self._records.values())
    
    def update(self, record):
        self._records[record.strategy_id] = record
        self._save_to_file()
    
    def delete(self, strategy_id):
        self._records.pop(strategy_id, None)
        self._save_to_file()
    
    def clear(self):
        self._records.clear()
        self._save_to_file()
    
    def filter(self, status=None, strategy_type=None, tag=None, author=None):
        result = list(self._records.values())
        if status:
            result = [r for r in result if r.status == status]
        if strategy_type:
            result = [r for r in result if r.strategy_type == strategy_type]
        if tag:
            result = [r for r in result if tag in r.tags]
        if author:
            result = [r for r in result if author.lower() in r.author.lower()]
        return result
    
    def search(self, keyword):
        keyword = keyword.lower()
        return [r for r in self._records.values()
                if keyword in r.name.lower()
                or keyword in r.description.lower()
                or any(keyword in t.lower() for t in r.tags)]
    
    def update_performance(self, strategy_id, annual_return=0, max_drawdown=0,
                          sharpe=0, sortino=0, calmar=0, win_rate=0, turnover=0, profit_factor=0):
        s = self.get(strategy_id)
        if s:
            s.annual_return = annual_return
            s.max_drawdown = max_drawdown
            s.sharpe = sharpe
            s.sortino = sortino
            s.calmar = calmar
            s.win_rate = win_rate
            s.turnover = turnover
            s.profit_factor = profit_factor
            self.update(s)
    
    def publish(self, strategy_id):
        from .constant import StrategyStatus
        s = self.get(strategy_id)
        if s:
            s.status = StrategyStatus.PUBLISHED
            self.update(s)
    
    def retire(self, strategy_id):
        from .constant import StrategyStatus
        s = self.get(strategy_id)
        if s:
            s.status = StrategyStatus.RETIRED
            self.update(s)
    
    def set_testing(self, strategy_id):
        from .constant import StrategyStatus
        s = self.get(strategy_id)
        if s:
            s.status = StrategyStatus.TESTING
            self.update(s)
    
    def add_version(self, strategy_id, note="", created_by=""):
        s = self.get(strategy_id)
        if s:
            from .model.strategy_model import StrategyVersion
            ver = StrategyVersion(
                version_id=f"{strategy_id}-V{len(s.versions)+1}",
                version_num=f"v{len(s.versions)+1}.0",
                note=note,
                created_by=created_by,
                created_at=datetime.now()
            )
            s.versions.append(ver)
            self.update(s)
            return ver
        return None
    
    def get_versions(self, strategy_id):
        s = self.get(strategy_id)
        return s.versions if s else []
    
    def link_feature(self, strategy_id, feature_id):
        s = self.get(strategy_id)
        if s and feature_id not in s.feature_ids:
            s.feature_ids.append(feature_id)
            self.update(s)
    
    def unlink_feature(self, strategy_id, feature_id):
        s = self.get(strategy_id)
        if s and feature_id in s.feature_ids:
            s.feature_ids.remove(feature_id)
            self.update(s)
    
    def link_backtest(self, strategy_id, backtest_id):
        s = self.get(strategy_id)
        if s and backtest_id not in s.backtest_ids:
            s.backtest_ids.append(backtest_id)
            self.update(s)
    
    def top_by_sharpe(self, n=10):
        all_s = sorted(self._records.values(), key=lambda x: x.sharpe, reverse=True)
        return all_s[:n]
    
    def top_by_return(self, n=10):
        all_s = sorted(self._records.values(), key=lambda x: x.annual_return, reverse=True)
        return all_s[:n]


class ModelRegistryJSON:
    """基于JSON文件的模型Registry"""
    
    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.data_file = self.data_dir / "models.json"
        self._records = {}
        self._load_from_file()
    
    def _load_from_file(self):
        if not self.data_file.exists():
            return
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            from .model.model_model import MLModelRecord
            from .constant import ModelStatus
            for m_data in data:
                if 'created_at' in m_data and m_data['created_at']:
                    m_data['created_at'] = datetime.fromisoformat(m_data['created_at'])
                if 'updated_at' in m_data and m_data['updated_at']:
                    m_data['updated_at'] = datetime.fromisoformat(m_data['updated_at'])
                if 'status' in m_data and isinstance(m_data['status'], str):
                    try:
                        m_data['status'] = ModelStatus(m_data['status'])
                    except:
                        m_data['status'] = ModelStatus.TRAINING
                record = MLModelRecord(**m_data)
                self._records[record.model_id] = record
            print(f"[JSON] 加载了 {len(self._records)} 个模型")
        except Exception as e:
            print(f"[JSON] 加载模型失败: {e}")
    
    def _save_to_file(self):
        try:
            data = [serialize_record(m) for m in self._records.values()]
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[JSON] 保存模型失败: {e}")
    
    def create(self, record):
        if record.model_id in self._records:
            raise ValueError(
                f"Model ID '{record.model_id}' already exists "
                f"(existing: '{self._records[record.model_id].name}'). "
                f"Use update() to modify existing records."
            )
        self._records[record.model_id] = record
        self._save_to_file()
        return record
    
    def get(self, model_id):
        return self._records.get(model_id)
    
    def list(self):
        return list(self._records.values())
    
    def update(self, record):
        self._records[record.model_id] = record
        self._save_to_file()
    
    def delete(self, model_id):
        self._records.pop(model_id, None)
        self._save_to_file()
    
    def clear(self):
        self._records.clear()
        self._save_to_file()
    
    def filter(self, status=None, model_type=None, tag=None, author=None):
        result = list(self._records.values())
        if status:
            result = [r for r in result if r.status == status]
        if model_type:
            result = [r for r in result if r.model_type == model_type]
        if tag:
            result = [r for r in result if tag in r.tags]
        if author:
            result = [r for r in result if author.lower() in r.author.lower()]
        return result
    
    def search(self, keyword):
        keyword = keyword.lower()
        return [r for r in self._records.values()
                if keyword in r.name.lower()
                or keyword in r.description.lower()
                or any(keyword in t.lower() for t in r.tags)]
    
    def update_eval_metrics(self, model_id, accuracy=0, auc=0, rmse=0, mae=0, f1=0, custom_metrics=None):
        m = self.get(model_id)
        if m:
            m.accuracy = accuracy
            m.auc = auc
            m.rmse = rmse
            m.mae = mae
            m.f1 = f1
            if custom_metrics:
                m.custom_metrics.update(custom_metrics)
            self.update(m)
    
    def add_training_run(self, model_id, run_note="", hyperparams=None, metrics=None,
                        dataset_id="", duration_sec=0, created_by=""):
        m = self.get(model_id)
        if m:
            from .model.model_model import TrainingRun
            run = TrainingRun(
                run_id=f"{model_id}-RUN{len(m.training_runs)+1}",
                run_note=run_note,
                hyperparams=hyperparams or {},
                metrics=metrics or {},
                dataset_id=dataset_id,
                duration_sec=duration_sec,
                created_by=created_by,
                created_at=datetime.now()
            )
            m.training_runs.append(run)
            self.update(m)
            return run
        return None
    
    def get_training_runs(self, model_id):
        m = self.get(model_id)
        return m.training_runs if m else []
    
    def deploy(self, model_id, env="", endpoint=""):
        from .constant import ModelStatus
        m = self.get(model_id)
        if m:
            m.status = ModelStatus.DEPLOYED
            m.deploy_env = env
            m.deploy_endpoint = endpoint
            self.update(m)
    
    def retire(self, model_id):
        from .constant import ModelStatus
        m = self.get(model_id)
        if m:
            m.status = ModelStatus.RETIRED
            self.update(m)
    
    def set_evaluated(self, model_id):
        from .constant import ModelStatus
        m = self.get(model_id)
        if m:
            m.status = ModelStatus.EVALUATED
            self.update(m)
    
    def link_feature(self, model_id, feature_id):
        m = self.get(model_id)
        if m and feature_id not in m.feature_ids:
            m.feature_ids.append(feature_id)
            self.update(m)
    
    def unlink_feature(self, model_id, feature_id):
        m = self.get(model_id)
        if m and feature_id in m.feature_ids:
            m.feature_ids.remove(feature_id)
            self.update(m)
    
    def link_dataset(self, model_id, dataset_id):
        m = self.get(model_id)
        if m and dataset_id not in m.dataset_ids:
            m.dataset_ids.append(dataset_id)
            self.update(m)
    
    def link_strategy(self, model_id, strategy_id):
        m = self.get(model_id)
        if m and strategy_id not in m.strategy_ids:
            m.strategy_ids.append(strategy_id)
            self.update(m)
    
    def link_experiment(self, model_id, experiment_id):
        m = self.get(model_id)
        if m and experiment_id not in m.experiment_ids:
            m.experiment_ids.append(experiment_id)
            self.update(m)
    
    def top_by_auc(self, n=10):
        all_m = sorted(self._records.values(), key=lambda x: x.auc, reverse=True)
        return all_m[:n]
    
    def top_by_accuracy(self, n=10):
        all_m = sorted(self._records.values(), key=lambda x: x.accuracy, reverse=True)
        return all_m[:n]


class BacktestRegistryJSON:
    """基于JSON文件的回测Registry"""
    
    def __init__(self, data_dir=None):
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.data_file = self.data_dir / "backtests.json"
        self._records = {}
        self._load_from_file()
    
    def _load_from_file(self):
        if not self.data_file.exists():
            return
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            from .model.backtest_model import BacktestRecord
            from .constant import BacktestStatus
            for b_data in data:
                if 'created_at' in b_data and b_data['created_at']:
                    b_data['created_at'] = datetime.fromisoformat(b_data['created_at'])
                if 'updated_at' in b_data and b_data['updated_at']:
                    b_data['updated_at'] = datetime.fromisoformat(b_data['updated_at'])
                if 'completed_at' in b_data and b_data['completed_at']:
                    b_data['completed_at'] = datetime.fromisoformat(b_data['completed_at'])
                if 'status' in b_data and isinstance(b_data['status'], str):
                    try:
                        b_data['status'] = BacktestStatus(b_data['status'])
                    except:
                        b_data['status'] = BacktestStatus.PENDING
                record = BacktestRecord(**b_data)
                self._records[record.backtest_id] = record
            print(f"[JSON] 加载了 {len(self._records)} 个回测")
        except Exception as e:
            print(f"[JSON] 加载回测失败: {e}")
    
    def _save_to_file(self):
        try:
            data = [serialize_record(b) for b in self._records.values()]
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[JSON] 保存回测失败: {e}")
    
    def create(self, record):
        if record.backtest_id in self._records:
            raise ValueError(
                f"Backtest ID '{record.backtest_id}' already exists "
                f"(existing: '{self._records[record.backtest_id].name}'). "
                f"Use update() to modify existing records."
            )
        self._records[record.backtest_id] = record
        self._save_to_file()
        return record
    
    def get(self, backtest_id):
        return self._records.get(backtest_id)
    
    def list(self):
        return list(self._records.values())
    
    def update(self, record):
        self._records[record.backtest_id] = record
        self._save_to_file()
    
    def delete(self, backtest_id):
        self._records.pop(backtest_id, None)
        self._save_to_file()
    
    def clear(self):
        self._records.clear()
        self._save_to_file()
    
    def filter(self, status=None, strategy_id=None, tag=None):
        result = list(self._records.values())
        if status:
            result = [r for r in result if r.status == status]
        if strategy_id:
            result = [r for r in result if r.strategy_id == strategy_id]
        if tag:
            result = [r for r in result if tag in r.tags]
        return result
    
    def search(self, keyword):
        keyword = keyword.lower()
        return [r for r in self._records.values()
                if keyword in r.name.lower()
                or keyword in (r.strategy_name or "").lower()
                or keyword in r.universe.lower()]
    
    def submit(self, backtest_id):
        from .constant import BacktestStatus
        b = self.get(backtest_id)
        if b:
            b.status = BacktestStatus.RUNNING
            self.update(b)
    
    def complete(self, backtest_id, annual_return=0, max_drawdown=0, sharpe=0,
                sortino=0, calmar=0, win_rate=0, turnover=0, profit_factor=0,
                total_return=0, alpha=0, beta=0, information_ratio=0,
                total_trades=0, avg_holding_days=0, max_position_conc=0,
                equity_curve=None, monthly_returns=None):
        from .constant import BacktestStatus
        b = self.get(backtest_id)
        if b:
            b.status = BacktestStatus.COMPLETED
            b.annual_return = annual_return
            b.max_drawdown = max_drawdown
            b.sharpe = sharpe
            b.sortino = sortino
            b.calmar = calmar
            b.win_rate = win_rate
            b.turnover = turnover
            b.profit_factor = profit_factor
            b.total_return = total_return
            b.alpha = alpha
            b.beta = beta
            b.information_ratio = information_ratio
            b.total_trades = total_trades
            b.avg_holding_days = avg_holding_days
            b.max_position_conc = max_position_conc
            if equity_curve:
                b.equity_curve = equity_curve
            if monthly_returns:
                b.monthly_returns = monthly_returns
            b.completed_at = datetime.now()
            self.update(b)
    
    def fail(self, backtest_id, error_msg=""):
        from .constant import BacktestStatus
        b = self.get(backtest_id)
        if b:
            b.status = BacktestStatus.FAILED
            b.error_msg = error_msg
            self.update(b)
    
    def compare(self, backtest_ids):
        return [self.get(bid) for bid in backtest_ids if self.get(bid)]
    
    def link_model(self, backtest_id, model_id):
        b = self.get(backtest_id)
        if b and model_id not in b.model_ids:
            b.model_ids.append(model_id)
            self.update(b)
    
    def unlink_model(self, backtest_id, model_id):
        b = self.get(backtest_id)
        if b and model_id in b.model_ids:
            b.model_ids.remove(model_id)
            self.update(b)
    
    def link_feature(self, backtest_id, feature_id):
        b = self.get(backtest_id)
        if b and feature_id not in b.feature_ids:
            b.feature_ids.append(feature_id)
            self.update(b)
    
    def link_dataset(self, backtest_id, dataset_id):
        b = self.get(backtest_id)
        if b and dataset_id not in b.dataset_ids:
            b.dataset_ids.append(dataset_id)
            self.update(b)
    
    def top_by_sharpe(self, n=10):
        all_b = sorted(self._records.values(), key=lambda x: x.sharpe, reverse=True)
        return all_b[:n]
    
    def top_by_return(self, n=10):
        all_b = sorted(self._records.values(), key=lambda x: x.annual_return, reverse=True)
        return all_b[:n]


class FeatureRegistryJSON:
    """基于JSON文件的特征Registry - 简化版"""
    
    def __init__(self, data_dir = None):
        from pathlib import Path
        self.data_dir = data_dir or DEFAULT_DATA_DIR
        self.data_file = self.data_dir / "features.json"
        self._records = {}
        self._eval_counter = {}
        self._load_from_file()
    
    def _load_from_file(self):
        """从JSON文件加载数据"""
        if not self.data_file.exists():
            return
        
        try:
            import json
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            from .model.feature_model import FeatureRecord
            from .constant import FeatureStatus
            
            for feat_data in data:
                if 'created_at' in feat_data and feat_data['created_at']:
                    feat_data['created_at'] = datetime.fromisoformat(feat_data['created_at'])
                if 'updated_at' in feat_data and feat_data['updated_at']:
                    feat_data['updated_at'] = datetime.fromisoformat(feat_data['updated_at'])
                
                if 'status' in feat_data and isinstance(feat_data['status'], str):
                    try:
                        feat_data['status'] = FeatureStatus(feat_data['status'])
                    except:
                        feat_data['status'] = FeatureStatus.EXPERIMENTAL
                
                record = FeatureRecord(**feat_data)
                self._records[record.feature_id] = record
            
            print(f"[JSON] 加载了 {len(self._records)} 个特征")
        except Exception as e:
            print(f"[JSON] 加载特征失败: {e}")
    
    def _save_to_file(self):
        """保存数据到JSON文件"""
        try:
            import json
            data = [serialize_record(feat) for feat in self._records.values()]
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[JSON] 保存特征失败: {e}")
    
    def create(self, record):
        if record.feature_id in self._records:
            raise ValueError(
                f"Feature ID '{record.feature_id}' already exists "
                f"(existing: '{self._records[record.feature_id].name}'). "
                f"Use update() to modify existing records."
            )
        self._records[record.feature_id] = record
        self._save_to_file()
        return record
    
    def get(self, feature_id):
        return self._records.get(feature_id)
    
    def list(self):
        return list(self._records.values())
    
    def update(self, record):
        self._records[record.feature_id] = record
        self._save_to_file()
    
    def delete(self, feature_id):
        self._records.pop(feature_id, None)
        self._save_to_file()
    
    def clear(self):
        self._records.clear()
        self._save_to_file()
    
    def filter(self, status=None, category=None, tag=None, author=None, active_only=False):
        result = list(self._records.values())
        if status is not None:
            result = [r for r in result if r.status == status]
        if category:
            result = [r for r in result if r.category == category]
        if tag:
            result = [r for r in result if tag in r.tags]
        if author:
            result = [r for r in result if author.lower() in r.author.lower()]
        if active_only:
            pass  # 简化实现：不过滤
        return result
    
    def search(self, keyword):
        keyword = keyword.lower()
        return [r for r in self._records.values()
                if keyword in r.name.lower()
                or keyword in r.description.lower()
                or any(keyword in t.lower() for t in r.tags)]

    def top_by_ic(self, n=10):
        """返回IC值最高的前N个特征"""
        # 简化实现：返回前N个特征
        all_features = list(self._records.values())
        return all_features[:n]
    
    def evaluate_ic(self, feature_id, target='return'):
        """评估特征IC值"""
        # 简化实现
        return None
    
    def get_dependencies(self, feature_id):
        """获取特征依赖"""
        feature = self.get(feature_id)
        if feature:
            return getattr(feature, 'dependencies', None) or []
        return []
    
    def get_dependents(self, feature_id):
        """获取依赖此特征的其他特征"""
        result = []
        for feat in self._records.values():
            deps = getattr(feat, 'dependencies', None) or []
            if feature_id in deps:
                result.append(feat.feature_id)
        return result



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
