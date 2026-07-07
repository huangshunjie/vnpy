"""
quant_research/model/pipeline_model.py  — Phase 9 扩展版
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import PipelineStatus

STEP_TYPES = [
    "data_load",    # 数据加载
    "feature_calc", # 因子计算
    "model_train",  # 模型训练
    "model_eval",   # 模型评估
    "backtest",     # 回测
    "report",       # 报告生成
    "notify",       # 通知
    "custom",       # 自定义
]


@dataclass
class PipelineRun:
    """单次流水线执行记录。"""
    run_id:       str              = ""
    pipeline_id:  str              = ""
    status:       str              = "running"   # running/completed/failed
    trigger:      str              = "manual"    # manual/schedule
    started_at:   datetime         = field(default_factory=datetime.now)
    finished_at:  Optional[datetime] = None
    duration_sec: float            = 0.0
    error_msg:    str              = ""
    step_logs:    Dict[str, str]   = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id":       self.run_id,
            "status":       self.status,
            "trigger":      self.trigger,
            "started_at":   self.started_at.isoformat(),
            "duration_sec": round(self.duration_sec, 2),
        }


@dataclass
class PipelineStepRecord:
    step_id:    str             = ""
    name:       str             = ""
    step_type:  str             = "custom"
    params:     Dict[str, Any]  = field(default_factory=dict)
    depends_on: List[str]       = field(default_factory=list)
    status:     str             = "idle"
    log:        str             = ""
    order:      int             = 0
    timeout_sec: int            = 3600

    def to_dict(self) -> dict:
        return {
            "step_id":   self.step_id,
            "name":      self.name,
            "step_type": self.step_type,
            "status":    self.status,
            "order":     self.order,
        }


@dataclass
class PipelineRecord:
    pipeline_id:  str              = ""
    name:         str              = ""
    description:  str              = ""
    status:       PipelineStatus   = PipelineStatus.IDLE
    steps:        List[PipelineStepRecord] = field(default_factory=list)
    runs:         List[PipelineRun]        = field(default_factory=list)
    schedule:     str              = ""
    author:       str              = ""

    # 关联
    experiment_id: Optional[str]   = None
    strategy_id:   Optional[str]   = None
    dataset_ids:   List[str]       = field(default_factory=list)
    feature_ids:   List[str]       = field(default_factory=list)

    tags:         List[str]        = field(default_factory=list)
    last_run_at:  Optional[datetime] = None
    next_run_at:  Optional[datetime] = None
    run_count:    int              = 0
    success_count: int             = 0
    fail_count:   int              = 0

    created_at:   datetime         = field(default_factory=datetime.now)
    updated_at:   datetime         = field(default_factory=datetime.now)
    created_by:   str              = ""

    def to_dict(self) -> dict:
        return {
            "pipeline_id": self.pipeline_id,
            "name":        self.name,
            "status":      self.status.value,
            "step_count":  len(self.steps),
            "run_count":   self.run_count,
            "schedule":    self.schedule,
            "created_at":  self.created_at.isoformat(),
        }
