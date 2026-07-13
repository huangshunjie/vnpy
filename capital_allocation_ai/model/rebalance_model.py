"""
capital_allocation_ai/model/rebalance_model.py  (Phase 5)

RebalancePlan + RebalanceRecord — 再平衡数据模型。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import RebalanceTrigger


@dataclass
class RebalanceTrade:
    """单笔再平衡交易（Phase 5）。"""
    alpha_id:     str
    delta_ratio:  float = 0.0    # 目标比例变化
    delta_amount: float = 0.0    # 交易金额（正=增配，负=减配）
    prev_ratio:   float = 0.0
    target_ratio: float = 0.0

    def to_dict(self) -> dict:
        return {
            "alpha_id":     self.alpha_id,
            "delta_ratio":  round(self.delta_ratio,  6),
            "delta_amount": round(self.delta_amount, 2),
            "prev_ratio":   round(self.prev_ratio,   6),
            "target_ratio": round(self.target_ratio, 6),
        }


@dataclass
class RebalancePlan:
    """
    再平衡执行计划（Phase 5）。

    CA 系统的最终输出：说明应如何调整资金分配。
    下游策略/组合引擎消费此计划，CA 系统不执行交易。
    """
    plan_id:       str
    trigger:       RebalanceTrigger
    trigger_reason: str = ""
    trades:        list[RebalanceTrade]  = field(default_factory=list)
    prev_ratios:   dict[str, float]      = field(default_factory=dict)
    target_ratios: dict[str, float]      = field(default_factory=dict)
    total_capital: float = 0.0
    cost_estimate: dict  = field(default_factory=dict)
    drift_score:   float = 0.0
    is_cost_effective: bool = True
    batches:       list[dict] = field(default_factory=list)   # 分批执行计划
    created_at:    datetime   = field(default_factory=datetime.now)
    meta:          dict       = field(default_factory=dict)

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def total_turnover(self) -> float:
        return round(sum(abs(t.delta_amount) for t in self.trades), 2)

    @property
    def estimated_cost(self) -> float:
        return self.cost_estimate.get("total", 0.0)

    def to_dict(self) -> dict:
        return {
            "plan_id":        self.plan_id,
            "trigger":        self.trigger.value,
            "trigger_reason": self.trigger_reason,
            "n_trades":       self.n_trades,
            "total_capital":  round(self.total_capital,  2),
            "total_turnover": self.total_turnover,
            "estimated_cost": round(self.estimated_cost, 2),
            "drift_score":    round(self.drift_score,    6),
            "is_cost_effective": self.is_cost_effective,
            "n_batches":      len(self.batches),
            "created_at":     str(self.created_at)[:19],
        }


@dataclass
class RebalanceRecord:
    """再平衡历史记录（Phase 5）。"""
    record_id:    str
    plan:         RebalancePlan
    status:       str = "planned"   # "planned" | "approved" | "cancelled"
    approved_at:  datetime | None = None
    cancelled_at: datetime | None = None
    note:         str = ""

    def approve(self) -> None:
        self.status      = "approved"
        self.approved_at = datetime.now()

    def cancel(self, reason: str = "") -> None:
        self.status       = "cancelled"
        self.cancelled_at = datetime.now()
        self.note         = reason

    def to_dict(self) -> dict:
        return {
            "record_id":   self.record_id,
            "plan_id":     self.plan.plan_id,
            "trigger":     self.plan.trigger.value,
            "status":      self.status,
            "n_trades":    self.plan.n_trades,
            "turnover":    self.plan.total_turnover,
            "cost":        self.plan.estimated_cost,
            "created_at":  str(self.plan.created_at)[:19],
            "approved_at": str(self.approved_at)[:19] if self.approved_at else None,
        }
