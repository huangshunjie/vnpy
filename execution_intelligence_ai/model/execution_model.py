"""
execution_intelligence_ai/model/execution_model.py  (Phase 1 stub)

ExecutionState — 执行任务顶层状态。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import ExecutionStrategy, ExecutionPhase


@dataclass
class ExecutionState:
    """单次执行任务的完整状态。"""
    execution_id:    str               = ""
    parent_order_id: str               = ""
    symbol:          str               = ""
    exchange:        str               = ""
    direction:       str               = ""           # "long" / "short"
    total_volume:    float             = 0.0
    filled_volume:   float             = 0.0
    avg_price:       float             = 0.0
    strategy:        ExecutionStrategy = ExecutionStrategy.TWAP
    phase:           ExecutionPhase    = ExecutionPhase.IDLE
    created_at:      datetime          = field(default_factory=datetime.now)
    updated_at:      datetime          = field(default_factory=datetime.now)
    meta:            dict              = field(default_factory=dict)

    @property
    def fill_rate(self) -> float:
        if self.total_volume <= 0:
            return 0.0
        return round(self.filled_volume / self.total_volume, 6)

    def to_dict(self) -> dict:
        return {
            "execution_id":    self.execution_id,
            "parent_order_id": self.parent_order_id,
            "symbol":          self.symbol,
            "exchange":        self.exchange,
            "direction":       self.direction,
            "total_volume":    self.total_volume,
            "filled_volume":   self.filled_volume,
            "avg_price":       round(self.avg_price, 4),
            "fill_rate":       self.fill_rate,
            "strategy":        self.strategy.value,
            "phase":           self.phase.value,
            "created_at":      str(self.created_at)[:19],
            "updated_at":      str(self.updated_at)[:19],
        }
