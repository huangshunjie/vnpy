"""
adaptive_learning_ai/model/learning_model.py  (Phase 3)

LearningSignal   — 从反馈中提取的单条调整信号
LearningPattern  — 同类信号聚合后的模式
LearningState    — 学习引擎当前状态快照
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import FeedbackType, AdaptationTarget


@dataclass
class LearningSignal:
    """
    从反馈记录中提取的单条调整信号。

    结构：Feedback → Pattern Extraction → Adjustment Signal
    """
    signal_id:         str              = ""
    source_feedback_id:str              = ""
    feedback_type:     FeedbackType     = FeedbackType.EXECUTION_SLIPPAGE
    target:            AdaptationTarget = AdaptationTarget.EXECUTION_PARAMS

    # 信号值
    adjustment_value:  float = 0.0      # 建议调整量（有符号）
    adjustment_pct:    float = 0.0      # 建议调整百分比
    confidence:        float = 0.0      # 置信度 [0, 1]
    urgency:           float = 0.0      # 紧迫度 [0, 1]  — 影响更新优先级

    # 归因
    entity_id:         str   = ""       # 策略/Alpha/资产 ID
    dimension:         str   = ""       # 调整维度（weight/threshold/param）
    direction:         int   = 0        # +1 上调  -1 下调  0 中性
    reason:            str   = ""

    created_at:        datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "signal_id":          self.signal_id,
            "source_feedback_id": self.source_feedback_id,
            "feedback_type":      self.feedback_type.value,
            "target":             self.target.value,
            "adjustment_value":   round(self.adjustment_value, 6),
            "adjustment_pct":     round(self.adjustment_pct,   6),
            "confidence":         round(self.confidence,       4),
            "urgency":            round(self.urgency,          4),
            "entity_id":          self.entity_id,
            "dimension":          self.dimension,
            "direction":          self.direction,
            "reason":             self.reason,
            "created_at":         str(self.created_at)[:19],
        }


@dataclass
class LearningPattern:
    """
    同类信号聚合后的学习模式。

    当某类反馈的信号在短期内一致出现，形成可信模式。
    """
    pattern_id:        str              = ""
    feedback_type:     FeedbackType     = FeedbackType.EXECUTION_SLIPPAGE
    target:            AdaptationTarget = AdaptationTarget.EXECUTION_PARAMS

    # 模式统计
    n_signals:         int   = 0
    avg_adjustment:    float = 0.0
    avg_confidence:    float = 0.0
    avg_urgency:       float = 0.0
    consistency:       float = 0.0      # 同向信号比例 [0, 1]
    pattern_strength:  float = 0.0      # 综合模式强度 [0, 1]

    # 代表性调整建议
    recommended_delta: float = 0.0      # 最终建议调整量
    entity_ids:        list[str] = field(default_factory=list)

    detected_at:       datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "pattern_id":       self.pattern_id,
            "feedback_type":    self.feedback_type.value,
            "target":           self.target.value,
            "n_signals":        self.n_signals,
            "avg_adjustment":   round(self.avg_adjustment,   6),
            "avg_confidence":   round(self.avg_confidence,   4),
            "avg_urgency":      round(self.avg_urgency,      4),
            "consistency":      round(self.consistency,      4),
            "pattern_strength": round(self.pattern_strength, 4),
            "recommended_delta":round(self.recommended_delta,6),
            "entity_ids":       self.entity_ids,
            "detected_at":      str(self.detected_at)[:19],
        }


@dataclass
class LearningState:
    """学习引擎当前状态快照。"""
    cycle:              int   = 0
    phase:              int   = 3

    # 信号统计
    total_signals:      int   = 0
    active_patterns:    int   = 0
    high_conf_signals:  int   = 0       # confidence > 0.7

    # 质量指标
    avg_confidence:     float = 0.0
    avg_urgency:        float = 0.0
    learning_velocity:  float = 0.0     # 每周期信号数量趋势 [0, 1]

    # 按目标统计
    target_counts:      dict  = field(default_factory=dict)

    # 最近模式列表（摘要）
    recent_patterns:    list[dict] = field(default_factory=list)

    updated_at:         datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "cycle":             self.cycle,
            "phase":             self.phase,
            "total_signals":     self.total_signals,
            "active_patterns":   self.active_patterns,
            "high_conf_signals": self.high_conf_signals,
            "avg_confidence":    round(self.avg_confidence,   4),
            "avg_urgency":       round(self.avg_urgency,      4),
            "learning_velocity": round(self.learning_velocity,4),
            "target_counts":     self.target_counts,
            "recent_patterns":   self.recent_patterns[:5],
            "updated_at":        str(self.updated_at)[:19],
        }
