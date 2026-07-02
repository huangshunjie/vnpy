"""
capital_allocation_ai/model/risk_budget_model.py  (Phase 4)

RiskBudget + RiskBreach + RiskAdjustSignal — 风险预算数据模型。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import RiskBudgetType, AllocationStatus


@dataclass
class RiskBudget:
    """单个 Alpha 的风险预算分配（Phase 4）。"""
    alpha_id:         str
    budget_type:      RiskBudgetType = RiskBudgetType.VOLATILITY
    budget_limit:     float = 0.0    # 预算上限（如 vol ≤ 0.20）
    current_value:    float = 0.0    # 当前风险指标值
    utilization:      float = 0.0    # 使用率 = current / limit [0, +∞]
    weight:           float = 0.0    # 该 Alpha 在组合中的权重
    is_breached:      bool  = False
    status:           AllocationStatus = AllocationStatus.ACTIVE
    updated_at:       datetime = field(default_factory=datetime.now)

    @property
    def headroom(self) -> float:
        """剩余风险空间（limit - current，正值表示安全）。"""
        return round(self.budget_limit - self.current_value, 6)

    def to_dict(self) -> dict:
        return {
            "alpha_id":      self.alpha_id,
            "budget_type":   self.budget_type.value,
            "budget_limit":  round(self.budget_limit,  4),
            "current_value": round(self.current_value, 4),
            "utilization":   round(self.utilization,   4),
            "headroom":      round(self.headroom,       4),
            "weight":        round(self.weight,         6),
            "is_breached":   self.is_breached,
            "status":        self.status.value,
            "updated_at":    str(self.updated_at)[:19],
        }


@dataclass
class RiskBreach:
    """风险预算违规记录（Phase 4）。"""
    breach_id:      str
    alpha_id:       str
    budget_type:    RiskBudgetType
    limit:          float
    actual:         float
    excess:         float = 0.0     # actual - limit
    severity:       str   = "warn"  # "warn" | "critical"
    action_taken:   str   = ""      # 已采取动作描述
    detected_at:    datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "breach_id":   self.breach_id,
            "alpha_id":    self.alpha_id,
            "budget_type": self.budget_type.value,
            "limit":       round(self.limit,    4),
            "actual":      round(self.actual,   4),
            "excess":      round(self.excess,   4),
            "severity":    self.severity,
            "action_taken": self.action_taken,
            "detected_at": str(self.detected_at)[:19],
        }


@dataclass
class RiskAdjustSignal:
    """
    风险触发的资金调整信号（Phase 4）。

    当某 Alpha 风险超限时，CA 系统发出减仓信号；
    下游策略消费此信号，CA 系统不执行实际交易。
    """
    signal_id:      str
    alpha_id:       str
    breach:         RiskBreach
    suggested_ratio: float = 0.0   # 建议目标比例（0 = 暂停）
    current_ratio:   float = 0.0
    delta_ratio:     float = 0.0   # suggested - current（负 = 减仓）
    urgency:         str   = "high"
    reason:          str   = ""
    created_at:      datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "signal_id":       self.signal_id,
            "alpha_id":        self.alpha_id,
            "breach_type":     self.breach.budget_type.value,
            "suggested_ratio": round(self.suggested_ratio, 6),
            "current_ratio":   round(self.current_ratio,   6),
            "delta_ratio":     round(self.delta_ratio,      6),
            "urgency":         self.urgency,
            "reason":          self.reason,
            "created_at":      str(self.created_at)[:19],
        }


@dataclass
class RiskSnapshot:
    """全局风险预算快照（Phase 4）。"""
    snapshot_id:      str
    budgets:          dict[str, list[RiskBudget]] = field(default_factory=dict)
    breaches:         list[RiskBreach]            = field(default_factory=list)
    adjust_signals:   list[RiskAdjustSignal]      = field(default_factory=list)
    portfolio_var:    float = 0.0
    portfolio_dd:     float = 0.0
    portfolio_beta:   float = 0.0
    n_breached:       int   = 0
    created_at:       datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "snapshot_id":    self.snapshot_id,
            "n_alphas":       len(self.budgets),
            "n_breached":     self.n_breached,
            "n_signals":      len(self.adjust_signals),
            "portfolio_var":  round(self.portfolio_var,  6),
            "portfolio_dd":   round(self.portfolio_dd,   6),
            "portfolio_beta": round(self.portfolio_beta, 6),
            "created_at":     str(self.created_at)[:19],
        }
