"""
global_portfolio_intelligence/model/performance_model.py  (Phase 4)

CapitalFlowState — 资金流当前状态快照
FlowRecord       — 单次资金流调度记录
CapitalBudget    — 策略/Alpha 资金预算
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import AllocationMode


@dataclass
class CapitalBudget:
    """单个策略/Alpha 的资金预算。"""
    entity_id:        str   = ""
    entity_type:      str   = "strategy"   # "strategy" | "alpha"
    allocated_capital:float = 0.0          # 分配资金量
    allocation_ratio: float = 0.0          # 占总资金比例 [0,1]
    performance_score:float = 50.0         # 历史绩效分 [0,100]
    regime_weight:    float = 1.0          # 市场状态调节系数
    risk_budget:      float = 0.0          # 风险预算（波动率上限）
    is_active:        bool  = True

    def to_dict(self) -> dict:
        return {
            "entity_id":         self.entity_id,
            "entity_type":       self.entity_type,
            "allocated_capital": round(self.allocated_capital, 2),
            "allocation_ratio":  round(self.allocation_ratio,  6),
            "performance_score": round(self.performance_score, 2),
            "regime_weight":     round(self.regime_weight,     4),
            "risk_budget":       round(self.risk_budget,       4),
            "is_active":         self.is_active,
        }


@dataclass
class FlowRecord:
    """单次资金流调度记录。"""
    flow_id:        str  = ""
    flow_type:      str  = "allocation"   # "inflow"|"outflow"|"rebalance"|"allocation"
    entity_id:      str  = ""
    entity_type:    str  = "strategy"
    amount:         float = 0.0
    ratio:          float = 0.0
    mode:           AllocationMode = AllocationMode.PERFORMANCE
    reason:         str  = ""
    created_at:     datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "flow_id":    self.flow_id,
            "flow_type":  self.flow_type,
            "entity_id":  self.entity_id,
            "amount":     round(self.amount, 2),
            "ratio":      round(self.ratio,  6),
            "mode":       self.mode.value,
            "reason":     self.reason,
            "created_at": str(self.created_at)[:19],
        }


@dataclass
class CapitalFlowState:
    """资金流当前状态快照。"""
    total_capital:       float = 0.0
    deployed_capital:    float = 0.0
    idle_capital:        float = 0.0
    deployment_ratio:    float = 0.0     # deployed / total [0,1]

    # 各实体预算
    strategy_budgets:    list[CapitalBudget] = field(default_factory=list)
    alpha_budgets:       list[CapitalBudget] = field(default_factory=list)

    # 聚合指标
    n_active_strategies: int   = 0
    n_active_alphas:     int   = 0
    concentration_score: float = 0.0    # 集中度评分 [0,100]，越高越分散
    efficiency_score:    float = 0.0    # 资金效率评分 [0,100]

    mode:                AllocationMode = AllocationMode.PERFORMANCE
    updated_at:          datetime = field(default_factory=datetime.now)
    flow_count:          int      = 0

    def to_dict(self) -> dict:
        return {
            "total_capital":       round(self.total_capital,    2),
            "deployed_capital":    round(self.deployed_capital, 2),
            "idle_capital":        round(self.idle_capital,     2),
            "deployment_ratio":    round(self.deployment_ratio, 4),
            "n_active_strategies": self.n_active_strategies,
            "n_active_alphas":     self.n_active_alphas,
            "concentration_score": round(self.concentration_score, 2),
            "efficiency_score":    round(self.efficiency_score,    2),
            "mode":                self.mode.value,
            "updated_at":          str(self.updated_at)[:19],
            "flow_count":          self.flow_count,
            "strategy_budgets":    [b.to_dict() for b in self.strategy_budgets],
            "alpha_budgets":       [b.to_dict() for b in self.alpha_budgets],
        }
