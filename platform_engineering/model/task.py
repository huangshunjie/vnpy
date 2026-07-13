"""
platform_engineering/model/task.py
任务执行模型。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import TaskStatus, TaskType, TaskPriority, WorkerStatus


@dataclass
class TaskRecord:
    task_id:      str          = ""
    name:         str          = ""
    task_type:    TaskType     = TaskType.CUSTOM
    priority:     TaskPriority = TaskPriority.NORMAL
    status:       TaskStatus   = TaskStatus.PENDING
    params:       Dict[str, Any] = field(default_factory=dict)
    result:       Optional[Any]  = None
    error_msg:    str          = ""
    worker_id:    str          = ""
    retries:      int          = 0
    max_retries:  int          = 3
    timeout_secs: int          = 3600
    progress:     float        = 0.0      # 0.0 – 1.0
    log:          str          = ""
    tags:         List[str]    = field(default_factory=list)
    created_by:   str          = ""
    scheduled_at: Optional[datetime] = None
    started_at:   Optional[datetime] = None
    finished_at:  Optional[datetime] = None
    created_at:   datetime     = field(default_factory=datetime.now)
    updated_at:   datetime     = field(default_factory=datetime.now)

    def duration_secs(self) -> Optional[float]:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict:
        return {
            "task_id":   self.task_id,
            "name":      self.name,
            "task_type": self.task_type.value,
            "priority":  self.priority.value,
            "status":    self.status.value,
            "progress":  self.progress,
            "worker_id": self.worker_id,
            "retries":   self.retries,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class WorkerRecord:
    worker_id:    str          = ""
    name:         str          = ""
    status:       WorkerStatus = WorkerStatus.IDLE
    current_task: str          = ""
    task_count:   int          = 0
    error_count:  int          = 0
    cpu_pct:      float        = 0.0
    mem_pct:      float        = 0.0
    registered_at: datetime    = field(default_factory=datetime.now)
    last_heartbeat: datetime   = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "worker_id":  self.worker_id,
            "name":       self.name,
            "status":     self.status.value,
            "task_count": self.task_count,
            "cpu_pct":    self.cpu_pct,
            "mem_pct":    self.mem_pct,
        }
