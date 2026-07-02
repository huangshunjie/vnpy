"""
live_production/model/system_state_model.py

TradingStateRecord — 交易状态记录（Phase 2 完整版）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..constant import TradingState, FailoverMode
from ..engine.state_manager import StateTransition


@dataclass
class TradingStateRecord:
    """实盘交易状态完整记录（Phase 2）。"""
    state:         TradingState  = TradingState.INIT
    failover_mode: FailoverMode  = FailoverMode.FULL
    started_at:    datetime | None = None
    updated_at:    datetime        = field(default_factory=datetime.now)
    reason:        str             = ""
    transition_count: int          = 0

    def update(self, new_state: TradingState, reason: str = "") -> None:
        self.state        = new_state
        self.reason       = reason
        self.updated_at   = datetime.now()
        self.transition_count += 1
        if new_state == TradingState.RUNNING and self.started_at is None:
            self.started_at = self.updated_at

    def to_dict(self) -> dict:
        return {
            "state":            self.state.value,
            "failover_mode":    self.failover_mode.value,
            "started_at":       str(self.started_at)[:19] if self.started_at else "—",
            "updated_at":       str(self.updated_at)[:19],
            "reason":           self.reason,
            "transition_count": self.transition_count,
        }
