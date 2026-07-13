"""
market_reality_ai/model/failure_model.py

Phase 5: Failure Mode Analysis — complete models.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import FailureModeType, FailureSeverity, SimulationStatus


@dataclass
class FailureMode:
    """单个失败模式 (Phase 5 完整)。"""
    failure_id:     str             = ""
    mode_type:      FailureModeType = FailureModeType.STRATEGY_FAILURE
    severity:       FailureSeverity = FailureSeverity.LOW
    condition:      str   = ""
    trigger:        str   = ""
    impact:         str   = ""
    cascade_risk:   float = 0.0
    severity_score: float = 0.0
    trigger_value:  float = 0.0
    detected_at:    datetime = field(default_factory=datetime.now)
    resolved:       bool     = False
    resolved_at:    datetime | None = None
    notes:          str      = ""
    context:        dict     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "failure_id":     self.failure_id,
            "mode_type":      self.mode_type.value,
            "severity":       self.severity.value,
            "severity_name":  self.severity.name,
            "condition":      self.condition,
            "trigger":        self.trigger,
            "impact":         self.impact,
            "cascade_risk":   round(self.cascade_risk,    4),
            "severity_score": round(self.severity_score,  2),
            "trigger_value":  round(self.trigger_value,   4),
            "resolved":       self.resolved,
            "detected_at":    str(self.detected_at)[:19],
            "phase":          5,
        }


@dataclass
class FailureEvent:
    """失败事件记录 (单次触发)。"""
    event_id:    str             = ""
    failure_id:  str             = ""
    mode_type:   FailureModeType = FailureModeType.STRATEGY_FAILURE
    severity:    FailureSeverity = FailureSeverity.LOW
    description: str             = ""
    timestamp:   datetime        = field(default_factory=datetime.now)
    raw_data:    dict            = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id":    self.event_id,
            "failure_id":  self.failure_id,
            "mode_type":   self.mode_type.value,
            "severity":    self.severity.value,
            "description": self.description,
            "timestamp":   str(self.timestamp)[:19],
        }


@dataclass
class FailureState:
    """失败模式分析整体状态 (Phase 5)。"""
    status:          SimulationStatus   = SimulationStatus.IDLE
    active_failures: list[FailureMode]  = field(default_factory=list)
    failure_events:  list[FailureEvent] = field(default_factory=list)
    max_severity:    FailureSeverity    = FailureSeverity.LOW
    cascade_active:  bool   = False
    cascade_depth:   int    = 0
    cascade_risk:    float  = 0.0
    is_fatal:        bool   = False
    system_score:    float  = 0.0
    fatal_combos:    list[str] = field(default_factory=list)
    updated_at:      datetime  = field(default_factory=datetime.now)

    def update(self) -> None:
        from ..utils.failure_utils import (
            cascade_risk_score, cascade_depth as _cascade_depth,
            is_fatal_combination, fatal_combination_names,
            system_failure_score,
        )
        if not self.active_failures:
            self.max_severity   = FailureSeverity.LOW
            self.cascade_risk   = 0.0
            self.cascade_depth  = 0
            self.cascade_active = False
            self.is_fatal       = False
            self.system_score   = 0.0
            self.fatal_combos   = []
            self.updated_at     = datetime.now()
            return

        types   = [f.mode_type.value for f in self.active_failures]
        max_sev = max(f.severity.value for f in self.active_failures)
        self.max_severity = FailureSeverity(max_sev)

        c_risk  = cascade_risk_score(types, max_sev)
        c_depth = _cascade_depth(types, c_risk)
        fatal   = is_fatal_combination(types)

        self.cascade_risk   = c_risk
        self.cascade_depth  = c_depth
        self.cascade_active = c_depth > 0
        self.is_fatal       = fatal
        self.fatal_combos   = fatal_combination_names(types)
        self.system_score   = system_failure_score(
            [f.to_dict() for f in self.active_failures], c_risk, fatal)
        self.updated_at     = datetime.now()

    def to_dict(self) -> dict:
        return {
            "status":            self.status.value,
            "active_count":      len(self.active_failures),
            "event_count":       len(self.failure_events),
            "max_severity":      self.max_severity.value,
            "max_severity_name": self.max_severity.name,
            "cascade_active":    self.cascade_active,
            "cascade_depth":     self.cascade_depth,
            "cascade_risk":      round(self.cascade_risk,  4),
            "is_fatal":          self.is_fatal,
            "system_score":      round(self.system_score,  2),
            "fatal_combos":      self.fatal_combos,
            "phase":             5,
        }


@dataclass
class RealityState:
    """全仿真系统顶层状态 — 聚合所有子状态 (Phase 5 完整)。"""
    phase:             int    = 5
    execution_state:   object = None
    impact_state:      object = None
    stress_state:      object = None
    walkforward_state: object = None
    failure_state:     object = None
    survival_score:    float  = 0.0
    system_healthy:    bool   = True
    updated_at:        datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "phase":           self.phase,
            "survival_score":  round(self.survival_score, 2),
            "system_healthy":  self.system_healthy,
            "has_execution":   self.execution_state   is not None,
            "has_impact":      self.impact_state      is not None,
            "has_stress":      self.stress_state      is not None,
            "has_walkforward": self.walkforward_state is not None,
            "has_failure":     self.failure_state     is not None,
            "updated_at":      str(self.updated_at)[:19],
        }
