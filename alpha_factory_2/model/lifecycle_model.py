"""
alpha_factory_2/model/lifecycle_model.py

AlphaLifecycle — Alpha 生命周期记录（Phase 1 Stub）。
Phase 5 实现状态迁移规则。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import AlphaStatus


@dataclass
class LifecycleEvent:
    """单次状态迁移记录。"""
    from_status: AlphaStatus
    to_status:   AlphaStatus
    reason:      str     = ""
    ts:          datetime = field(default_factory=datetime.now)

    def to_line(self) -> str:
        return (
            f"[{str(self.ts)[:19]}] "
            f"{self.from_status.value} -> {self.to_status.value}  {self.reason}"
        )


@dataclass
class AlphaLifecycle:
    """Alpha 生命周期完整记录（stub）。"""
    alpha_id:    str
    status:      AlphaStatus          = AlphaStatus.GENERATED
    events:      list[LifecycleEvent] = field(default_factory=list)
    created_at:  datetime             = field(default_factory=datetime.now)
    retired_at:  datetime | None      = None

    def to_dict(self) -> dict:
        return {
            "alpha_id":   self.alpha_id,
            "status":     self.status.value,
            "created_at": str(self.created_at)[:19],
            "retired_at": str(self.retired_at)[:19] if self.retired_at else "---",
            "events":     len(self.events),
        }
