"""
capital_allocation_ai/model/allocation_model.py  (Phase 3)

CapitalAllocation + CapitalFlowSignal — 资金分配数据模型。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import AllocationStatus, CapitalFlowDirection


@dataclass
class CapitalAllocation:
    """单个 Alpha 的资金分配记录（Phase 3 完善）。"""
    alpha_id:        str
    total_capital:   float = 0.0
    allocated:       float = 0.0     # 本期分配金额
    ratio:           float = 0.0     # 本期分配比例 [0,1]
    prev_allocated:  float = 0.0     # 上期分配金额
    prev_ratio:      float = 0.0     # 上期分配比例
    delta_ratio:     float = 0.0     # 比例变化
    flow_direction:  CapitalFlowDirection = CapitalFlowDirection.HOLD
    capital_score:   float = 0.0     # 来源评分
    status:          AllocationStatus     = AllocationStatus.PENDING
    allocated_at:    datetime = field(default_factory=datetime.now)
    meta:            dict     = field(default_factory=dict)

    @property
    def flow_amount(self) -> float:
        return round(self.allocated - self.prev_allocated, 2)

    def to_dict(self) -> dict:
        return {
            "alpha_id":       self.alpha_id,
            "total_capital":  round(self.total_capital,  2),
            "allocated":      round(self.allocated,      2),
            "ratio":          round(self.ratio,          6),
            "prev_ratio":     round(self.prev_ratio,     6),
            "delta_ratio":    round(self.delta_ratio,    6),
            "flow_direction": self.flow_direction.value,
            "flow_amount":    self.flow_amount,
            "capital_score":  round(self.capital_score,  4),
            "status":         self.status.value,
            "allocated_at":   str(self.allocated_at)[:19],
        }


@dataclass
class CapitalFlowSignal:
    """
    资金流动信号（Phase 3）。

    Capital Allocation 系统唯一的输出：说明资金应如何流动。
    下游（Strategy / Portfolio）消费此信号，但 CA 系统不执行交易。
    """
    signal_id:      str
    alpha_id:       str
    direction:      CapitalFlowDirection = CapitalFlowDirection.HOLD
    target_ratio:   float = 0.0          # 目标资金比例
    target_amount:  float = 0.0          # 目标金额
    delta_amount:   float = 0.0          # 变化金额（正=增配，负=减配）
    urgency:        str   = "normal"     # "low" | "normal" | "high"
    reason:         str   = ""
    created_at:     datetime = field(default_factory=datetime.now)
    meta:           dict     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "signal_id":     self.signal_id,
            "alpha_id":      self.alpha_id,
            "direction":     self.direction.value,
            "target_ratio":  round(self.target_ratio,  6),
            "target_amount": round(self.target_amount, 2),
            "delta_amount":  round(self.delta_amount,  2),
            "urgency":       self.urgency,
            "reason":        self.reason,
            "created_at":    str(self.created_at)[:19],
        }


@dataclass
class AllocationSnapshot:
    """全局资金分配快照（一次 calculate_allocation 的完整结果）。"""
    snapshot_id:    str
    total_capital:  float
    allocations:    dict[str, CapitalAllocation] = field(default_factory=dict)
    signals:        list[CapitalFlowSignal]      = field(default_factory=list)
    concentration:  float = 0.0
    effective_n:    float = 0.0
    turnover:       float = 0.0
    created_at:     datetime = field(default_factory=datetime.now)

    @property
    def n_active(self) -> int:
        return sum(1 for a in self.allocations.values() if a.ratio > 1e-8)

    def to_dict(self) -> dict:
        return {
            "snapshot_id":   self.snapshot_id,
            "total_capital": round(self.total_capital, 2),
            "n_active":      self.n_active,
            "concentration": round(self.concentration, 6),
            "effective_n":   round(self.effective_n,   2),
            "turnover":      round(self.turnover,       6),
            "created_at":    str(self.created_at)[:19],
        }
