"""
global_portfolio_intelligence/model/rebalance_model.py  (Phase 5)

RebalanceTriggerEvent — 触发事件记录
RebalanceAdjustment   — 单项调整建议
RebalanceState        — 再平衡状态快照
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import RebalanceTrigger


@dataclass
class RebalanceTriggerEvent:
    """再平衡触发事件。"""
    trigger_id:   str              = ""
    trigger_type: RebalanceTrigger = RebalanceTrigger.SCHEDULED
    severity:     float            = 0.0    # [0,1] 严重程度
    description:  str              = ""
    metric_name:  str              = ""
    metric_value: float            = 0.0
    threshold:    float            = 0.0
    detected_at:  datetime         = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "trigger_id":   self.trigger_id,
            "trigger_type": self.trigger_type.value,
            "severity":     round(self.severity,     4),
            "description":  self.description,
            "metric_name":  self.metric_name,
            "metric_value": round(self.metric_value, 6),
            "threshold":    round(self.threshold,    6),
            "detected_at":  str(self.detected_at)[:19],
        }


@dataclass
class RebalanceAdjustment:
    """单项再平衡调整建议。"""
    entity_id:     str   = ""
    entity_type:   str   = "strategy"
    dimension:     str   = ""       # "weight"|"capital"|"alpha"|"execution"
    current_value: float = 0.0
    target_value:  float = 0.0
    delta:         float = 0.0
    priority:      int   = 1        # 1=高 2=中 3=低
    reason:        str   = ""

    def to_dict(self) -> dict:
        return {
            "entity_id":     self.entity_id,
            "entity_type":   self.entity_type,
            "dimension":     self.dimension,
            "current_value": round(self.current_value, 6),
            "target_value":  round(self.target_value,  6),
            "delta":         round(self.delta,          6),
            "priority":      self.priority,
            "reason":        self.reason,
        }


@dataclass
class RebalanceState:
    """再平衡系统状态快照。"""
    # 触发事件
    active_triggers:  list[RebalanceTriggerEvent] = field(default_factory=list)
    trigger_count:    int   = 0

    # 调整建议
    adjustments:      list[RebalanceAdjustment]   = field(default_factory=list)
    n_high_priority:  int   = 0
    n_mid_priority:   int   = 0
    n_low_priority:   int   = 0

    # 系统健康度
    system_health:    float = 100.0   # [0,100] 越高越健康
    imbalance_score:  float = 0.0     # [0,100] 越高越失衡

    # 风险漂移
    risk_drift:       float = 0.0
    alpha_decay_rate: float = 0.0
    exec_inefficiency:float = 0.0
    regime_shift_prob:float = 0.0

    updated_at:       datetime = field(default_factory=datetime.now)
    rebalance_count:  int      = 0

    def to_dict(self) -> dict:
        return {
            "trigger_count":    self.trigger_count,
            "n_adjustments":    len(self.adjustments),
            "n_high_priority":  self.n_high_priority,
            "n_mid_priority":   self.n_mid_priority,
            "n_low_priority":   self.n_low_priority,
            "system_health":    round(self.system_health,   2),
            "imbalance_score":  round(self.imbalance_score, 2),
            "risk_drift":       round(self.risk_drift,      6),
            "alpha_decay_rate": round(self.alpha_decay_rate,6),
            "exec_inefficiency":round(self.exec_inefficiency,6),
            "regime_shift_prob":round(self.regime_shift_prob,6),
            "updated_at":       str(self.updated_at)[:19],
            "rebalance_count":  self.rebalance_count,
            "active_triggers":  [t.to_dict() for t in self.active_triggers],
            "adjustments":      [a.to_dict() for a in self.adjustments[:10]],
        }
