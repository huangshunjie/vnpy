"""
quant_os/model/module_model.py

ModuleInfo — 子模块元数据模型（Phase 2）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..constant import ModuleType, ModuleState


@dataclass
class ModuleInfo:
    """已注册子模块的完整元数据。"""

    name:         str         = ""
    module_type:  ModuleType  = ModuleType.FACTOR
    state:        ModuleState = ModuleState.INIT

    # 时间戳
    registered_at: datetime   = field(default_factory=datetime.now)
    started_at:    datetime | None = None
    stopped_at:    datetime | None = None

    # 可选元数据（供 Phase 3+ 生命周期使用）
    description:  str         = ""
    version:      str         = "1.0"
    tags:         list[str]   = field(default_factory=list)

    # 运行统计（Phase 3+ 填充）
    event_count:  int         = 0
    error_count:  int         = 0
    last_error:   str         = ""

    @property
    def is_running(self) -> bool:
        return self.state == ModuleState.RUNNING

    @property
    def is_error(self) -> bool:
        return self.state == ModuleState.ERROR

    @property
    def uptime_seconds(self) -> float:
        """运行时长（秒），未启动时返回 0.0。"""
        if self.started_at is None:
            return 0.0
        end = self.stopped_at or datetime.now()
        return (end - self.started_at).total_seconds()

    def to_dict(self) -> dict:
        return {
            "name":          self.name,
            "type":          self.module_type.value,
            "state":         self.state.value,
            "registered_at": str(self.registered_at)[:19],
            "started_at":    str(self.started_at)[:19] if self.started_at else "—",
            "event_count":   self.event_count,
            "error_count":   self.error_count,
            "description":   self.description,
        }
