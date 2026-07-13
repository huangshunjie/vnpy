"""
adaptive_learning_ai/model/adaptation_model.py  (Phase 4)

AdaptationProposal  — 单条参数自适应建议
AdaptationRecord    — 已应用的自适应记录（含前/后对比）
AdaptationState     — 自适应引擎当前状态快照
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import AdaptationTarget, UpdateStrategy, FeedbackType


@dataclass
class AdaptationProposal:
    """
    单条参数自适应建议。
    来源：LearningPattern → AdaptationEngine 生成。
    """
    proposal_id:    str              = ""
    target:         AdaptationTarget = AdaptationTarget.EXECUTION_PARAMS
    update_strategy:UpdateStrategy   = UpdateStrategy.BLEND
    source_pattern: str              = ""    # pattern_id

    # 目标实体
    entity_id:      str   = ""
    dimension:      str   = ""   # weight / threshold / param name

    # 更新建议
    current_value:  float = 0.0
    proposed_value: float = 0.0
    delta:          float = 0.0
    delta_pct:      float = 0.0

    # 质量
    confidence:     float = 0.0
    urgency:        float = 0.0
    priority:       int   = 2        # 1=高 2=中 3=低

    # 自适应规则标注
    rule:           str   = ""       # performance_driven / regime_aware / decay_triggered
    feedback_type:  FeedbackType = FeedbackType.EXECUTION_SLIPPAGE
    approved:       bool  = False    # 是否已批准执行

    created_at:     datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "proposal_id":    self.proposal_id,
            "target":         self.target.value,
            "update_strategy":self.update_strategy.value,
            "source_pattern": self.source_pattern,
            "entity_id":      self.entity_id,
            "dimension":      self.dimension,
            "current_value":  round(self.current_value,  6),
            "proposed_value": round(self.proposed_value, 6),
            "delta":          round(self.delta,          6),
            "delta_pct":      round(self.delta_pct,      4),
            "confidence":     round(self.confidence,     4),
            "urgency":        round(self.urgency,        4),
            "priority":       self.priority,
            "rule":           self.rule,
            "feedback_type":  self.feedback_type.value,
            "approved":       self.approved,
            "created_at":     str(self.created_at)[:19],
        }


@dataclass
class AdaptationRecord:
    """已应用的自适应记录（含 before/after 对比）。"""
    record_id:      str              = ""
    proposal_id:    str              = ""
    target:         AdaptationTarget = AdaptationTarget.EXECUTION_PARAMS
    entity_id:      str              = ""
    dimension:      str              = ""

    value_before:   float = 0.0
    value_after:    float = 0.0
    actual_delta:   float = 0.0

    update_strategy:UpdateStrategy = UpdateStrategy.BLEND
    success:        bool  = True
    error_msg:      str   = ""
    applied_at:     datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "record_id":      self.record_id,
            "proposal_id":    self.proposal_id,
            "target":         self.target.value,
            "entity_id":      self.entity_id,
            "dimension":      self.dimension,
            "value_before":   round(self.value_before,  6),
            "value_after":    round(self.value_after,   6),
            "actual_delta":   round(self.actual_delta,  6),
            "update_strategy":self.update_strategy.value,
            "success":        self.success,
            "error_msg":      self.error_msg,
            "applied_at":     str(self.applied_at)[:19],
        }


@dataclass
class AdaptationState:
    """自适应引擎当前状态快照。"""
    total_proposals:    int   = 0
    total_applied:      int   = 0
    total_failed:       int   = 0
    pending_proposals:  int   = 0

    # 按目标统计
    target_counts:      dict  = field(default_factory=dict)

    # 质量
    avg_confidence:     float = 0.0
    avg_delta_pct:      float = 0.0
    high_priority_count:int   = 0

    # 最近记录摘要
    recent_records:     list[dict] = field(default_factory=list)

    updated_at:         datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "total_proposals":    self.total_proposals,
            "total_applied":      self.total_applied,
            "total_failed":       self.total_failed,
            "pending_proposals":  self.pending_proposals,
            "target_counts":      self.target_counts,
            "avg_confidence":     round(self.avg_confidence, 4),
            "avg_delta_pct":      round(self.avg_delta_pct,  4),
            "high_priority_count":self.high_priority_count,
            "recent_records":     self.recent_records[:5],
            "updated_at":         str(self.updated_at)[:19],
        }
