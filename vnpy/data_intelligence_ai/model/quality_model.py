"""
data_intelligence_ai/model/quality_model.py  (Phase 3)

QualityIssue     — 单条质量问题记录
QualityReport    — 单次质量检查报告（含所有问题）
DriftReport      — 数据漂移检测报告
QualityState     — 数据质量系统当前状态快照
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import QualityStatus


@dataclass
class QualityIssue:
    """单条质量问题。"""
    issue_id:    str           = ""
    status:      QualityStatus = QualityStatus.UNKNOWN
    field:       str           = ""       # 出现问题的字段名
    description: str           = ""
    severity:    float         = 0.0      # [0,1]
    value:       float         = 0.0      # 触发问题的实际值
    threshold:   float         = 0.0      # 阈值

    def to_dict(self) -> dict:
        return {
            "issue_id":    self.issue_id,
            "status":      self.status.value,
            "field":       self.field,
            "description": self.description,
            "severity":    round(self.severity,  4),
            "value":       round(self.value,     6),
            "threshold":   round(self.threshold, 6),
        }


@dataclass
class QualityReport:
    """单次质量检查报告（Phase 3 完整版）。"""
    report_id:     str           = ""
    symbol:        str           = ""
    feature_name:  str           = ""
    status:        QualityStatus = QualityStatus.CLEAN
    score:         float         = 100.0    # [0, 100]
    issues:        list[QualityIssue] = field(default_factory=list)
    n_issues:      int           = 0
    has_blocker:   bool          = False    # severity >= 0.9 的阻断性问题
    checked_at:    datetime      = field(default_factory=datetime.now)

    def add_issue(self, issue: QualityIssue) -> None:
        self.issues.append(issue)
        self.n_issues = len(self.issues)
        if issue.severity >= 0.9:
            self.has_blocker = True

    def to_dict(self) -> dict:
        return {
            "report_id":    self.report_id,
            "symbol":       self.symbol,
            "feature_name": self.feature_name,
            "status":       self.status.value,
            "score":        round(self.score, 2),
            "n_issues":     self.n_issues,
            "has_blocker":  self.has_blocker,
            "issues":       [i.to_dict() for i in self.issues],
            "checked_at":   str(self.checked_at)[:19],
        }


@dataclass
class DriftReport:
    """数据漂移检测报告。"""
    report_id:       str   = ""
    feature_name:    str   = ""
    symbol:          str   = ""

    # 统计对比
    hist_mean:       float = 0.0
    hist_std:        float = 0.0
    curr_mean:       float = 0.0
    curr_std:        float = 0.0

    # 漂移指标
    mean_drift:      float = 0.0     # |curr_mean - hist_mean| / hist_std
    std_ratio:       float = 1.0     # curr_std / hist_std
    ks_statistic:    float = 0.0     # 近似 KS 统计量 [0,1]
    drift_score:     float = 0.0     # 综合漂移得分 [0,1]
    is_drifted:      bool  = False   # drift_score > threshold

    drift_threshold: float = 0.3
    checked_at:      datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "report_id":      self.report_id,
            "feature_name":   self.feature_name,
            "symbol":         self.symbol,
            "hist_mean":      round(self.hist_mean,    6),
            "hist_std":       round(self.hist_std,     6),
            "curr_mean":      round(self.curr_mean,    6),
            "curr_std":       round(self.curr_std,     6),
            "mean_drift":     round(self.mean_drift,   4),
            "std_ratio":      round(self.std_ratio,    4),
            "ks_statistic":   round(self.ks_statistic, 4),
            "drift_score":    round(self.drift_score,  4),
            "is_drifted":     self.is_drifted,
            "checked_at":     str(self.checked_at)[:19],
        }


@dataclass
class QualityState:
    """数据质量系统当前状态快照（Phase 3）。"""
    total_checked:    int   = 0
    total_issues:     int   = 0
    total_drifted:    int   = 0
    clean_count:      int   = 0

    clean_pct:        float = 100.0
    avg_score:        float = 100.0
    blocker_count:    int   = 0

    status_counts:    dict  = field(default_factory=dict)
    drift_features:   list[str] = field(default_factory=list)

    updated_at:       datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "total_checked":  self.total_checked,
            "total_issues":   self.total_issues,
            "total_drifted":  self.total_drifted,
            "clean_count":    self.clean_count,
            "clean_pct":      round(self.clean_pct,  2),
            "avg_score":      round(self.avg_score,  2),
            "blocker_count":  self.blocker_count,
            "status_counts":  self.status_counts,
            "drift_features": self.drift_features,
            "updated_at":     str(self.updated_at)[:19],
        }
