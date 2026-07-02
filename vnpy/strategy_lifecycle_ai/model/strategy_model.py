"""
strategy_lifecycle_ai/model/strategy_model.py  (Phase 1 Stub)

StrategyState + StrategyLifecycle — 策略状态数据模型。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import StrategyPhase, PerformanceRating


@dataclass
class StrategyState:
    """策略当前状态快照（Phase 1: 字段定义，Phase 2+ 填充逻辑）。"""
    strategy_id:   str   = ""
    strategy_name: str   = ""
    phase:         StrategyPhase    = StrategyPhase.REGISTERED
    rating:        PerformanceRating = PerformanceRating.UNKNOWN
    sharpe:        float = 0.0
    max_drawdown:  float = 0.0
    win_rate:      float = 0.0
    live_days:     int   = 0
    registered_at: datetime = field(default_factory=datetime.now)
    updated_at:    datetime = field(default_factory=datetime.now)
    meta:          dict     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "strategy_id":   self.strategy_id,
            "strategy_name": self.strategy_name,
            "phase":         self.phase.value,
            "rating":        self.rating.value,
            "sharpe":        round(self.sharpe,       4),
            "max_drawdown":  round(self.max_drawdown, 4),
            "win_rate":      round(self.win_rate,     4),
            "live_days":     self.live_days,
            "registered_at": str(self.registered_at)[:19],
            "updated_at":    str(self.updated_at)[:19],
        }


@dataclass
class StrategyLifecycle:
    """策略完整生命周期记录。"""
    strategy_id:  str
    history:      list[dict] = field(default_factory=list)
    created_at:   datetime   = field(default_factory=datetime.now)

    def add_event(self, event_type: str, data: dict) -> None:
        self.history.append({
            "event_type": event_type,
            "data":       data,
            "ts":         str(datetime.now())[:19],
        })

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "event_count": len(self.history),
            "created_at":  str(self.created_at)[:19],
        }
