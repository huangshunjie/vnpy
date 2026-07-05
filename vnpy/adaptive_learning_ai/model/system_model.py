"""
adaptive_learning_ai/model/system_model.py  (Phase 5)

ModelVersion     — 模型版本记录
SystemUpdateRecord — 单次系统级更新记录
SystemLearningState — 整体自适应学习系统状态快照
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import UpdateStrategy, AdaptationTarget


@dataclass
class ModelVersion:
    """模型版本记录。"""
    version_id:     str   = ""
    version:        int   = 1
    target:         str   = ""          # AdaptationTarget.value
    entity_id:      str   = ""
    value:          float = 0.0
    previous_value: float = 0.0
    delta:          float = 0.0
    source:         str   = ""          # proposal_id / "rollback" / "regime"
    created_at:     datetime = field(default_factory=datetime.now)
    is_active:      bool  = True

    def to_dict(self) -> dict:
        return {
            "version_id":     self.version_id,
            "version":        self.version,
            "target":         self.target,
            "entity_id":      self.entity_id,
            "value":          round(self.value,          6),
            "previous_value": round(self.previous_value, 6),
            "delta":          round(self.delta,          6),
            "source":         self.source,
            "created_at":     str(self.created_at)[:19],
            "is_active":      self.is_active,
        }


@dataclass
class SystemUpdateRecord:
    """单次系统级更新记录（包含所有维度的变更）。"""
    update_id:      str   = ""
    cycle:          int   = 0
    trigger:        str   = ""    # "adaptation" / "rollback" / "regime" / "manual"

    # 变更摘要
    n_params_updated:  int   = 0
    n_rollbacks:       int   = 0
    targets_affected:  list[str] = field(default_factory=list)
    entities_updated:  list[str] = field(default_factory=list)

    # 质量指标
    avg_improvement:   float = 0.0     # 正 → 改善；负 → 劣化
    confidence:        float = 0.0
    success:           bool  = True
    error_msg:         str   = ""

    versions:          list[ModelVersion] = field(default_factory=list)
    created_at:        datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "update_id":       self.update_id,
            "cycle":           self.cycle,
            "trigger":         self.trigger,
            "n_params_updated":self.n_params_updated,
            "n_rollbacks":     self.n_rollbacks,
            "targets_affected":self.targets_affected,
            "entities_updated":self.entities_updated,
            "avg_improvement": round(self.avg_improvement, 4),
            "confidence":      round(self.confidence,      4),
            "success":         self.success,
            "error_msg":       self.error_msg,
            "created_at":      str(self.created_at)[:19],
        }


@dataclass
class SystemLearningState:
    """整体自适应学习系统状态快照（五个 Phase 汇总）。"""
    cycle:              int   = 0
    phase:              int   = 5

    # 闭环指标
    total_feedback:     int   = 0
    total_signals:      int   = 0
    total_patterns:     int   = 0
    total_proposals:    int   = 0
    total_applied:      int   = 0
    total_updates:      int   = 0
    total_rollbacks:    int   = 0

    # 演化质量
    system_health:      float = 100.0  # [0,100]
    learning_velocity:  float = 0.5
    adaptation_rate:    float = 0.0    # applied / proposals [0,1]
    avg_improvement:    float = 0.0

    # 活跃目标
    active_targets:     list[str] = field(default_factory=list)

    # 各子系统摘要
    feedback_summary:   dict = field(default_factory=dict)
    learning_summary:   dict = field(default_factory=dict)
    adaptation_summary: dict = field(default_factory=dict)
    update_summary:     dict = field(default_factory=dict)

    updated_at:         datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "cycle":              self.cycle,
            "phase":              self.phase,
            "total_feedback":     self.total_feedback,
            "total_signals":      self.total_signals,
            "total_patterns":     self.total_patterns,
            "total_proposals":    self.total_proposals,
            "total_applied":      self.total_applied,
            "total_updates":      self.total_updates,
            "total_rollbacks":    self.total_rollbacks,
            "system_health":      round(self.system_health,     2),
            "learning_velocity":  round(self.learning_velocity, 4),
            "adaptation_rate":    round(self.adaptation_rate,   4),
            "avg_improvement":    round(self.avg_improvement,   4),
            "active_targets":     self.active_targets,
            "feedback_summary":   self.feedback_summary,
            "learning_summary":   self.learning_summary,
            "adaptation_summary": self.adaptation_summary,
            "update_summary":     self.update_summary,
            "updated_at":         str(self.updated_at)[:19],
        }
