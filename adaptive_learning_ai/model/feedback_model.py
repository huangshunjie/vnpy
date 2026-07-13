"""
adaptive_learning_ai/model/feedback_model.py  (Phase 2)

FeedbackRecord   — 单条反馈记录
FeedbackBatch    — 一批反馈记录（一个学习周期的输入）
FeedbackState    — 反馈采集系统当前状态快照
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import FeedbackType


@dataclass
class FeedbackRecord:
    """
    单条反馈记录。

    结构：decision → result → deviation → reason
    """
    record_id:      str          = ""
    feedback_type:  FeedbackType = FeedbackType.EXECUTION_SLIPPAGE
    source_module:  str          = ""        # 来源模块

    # decision → result
    decision_value: float = 0.0             # 决策时的预期值
    actual_value:   float = 0.0             # 实际结果值
    deviation:      float = 0.0             # 偏差 = actual - decision
    deviation_pct:  float = 0.0             # 偏差百分比

    # 诊断
    reason:         str   = ""              # 偏差原因描述
    severity:       float = 0.0            # 严重程度 [0,1]
    signal_strength:float = 0.0            # 学习信号强度 [0,1]

    # 附加元数据
    symbol:         str   = ""
    strategy_id:    str   = ""
    metadata:       dict  = field(default_factory=dict)

    created_at:     datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "record_id":      self.record_id,
            "feedback_type":  self.feedback_type.value,
            "source_module":  self.source_module,
            "decision_value": round(self.decision_value, 6),
            "actual_value":   round(self.actual_value,   6),
            "deviation":      round(self.deviation,      6),
            "deviation_pct":  round(self.deviation_pct,  4),
            "reason":         self.reason,
            "severity":       round(self.severity,       4),
            "signal_strength":round(self.signal_strength,4),
            "symbol":         self.symbol,
            "strategy_id":    self.strategy_id,
            "created_at":     str(self.created_at)[:19],
        }


@dataclass
class FeedbackBatch:
    """一个学习周期的反馈批次。"""
    batch_id:       str                  = ""
    records:        list[FeedbackRecord] = field(default_factory=list)
    cycle:          int                  = 0
    created_at:     datetime             = field(default_factory=datetime.now)

    # 批次统计
    n_records:      int   = 0
    avg_severity:   float = 0.0
    avg_signal:     float = 0.0
    type_counts:    dict  = field(default_factory=dict)   # {FeedbackType.value: count}

    def add(self, record: FeedbackRecord) -> None:
        self.records.append(record)
        self.n_records = len(self.records)

    def compute_stats(self) -> None:
        if not self.records:
            return
        self.avg_severity = round(
            sum(r.severity for r in self.records) / len(self.records), 4)
        self.avg_signal   = round(
            sum(r.signal_strength for r in self.records) / len(self.records), 4)
        counts: dict[str, int] = {}
        for r in self.records:
            counts[r.feedback_type.value] = counts.get(r.feedback_type.value, 0) + 1
        self.type_counts = counts

    def to_dict(self) -> dict:
        self.compute_stats()
        return {
            "batch_id":    self.batch_id,
            "cycle":       self.cycle,
            "n_records":   self.n_records,
            "avg_severity":self.avg_severity,
            "avg_signal":  self.avg_signal,
            "type_counts": self.type_counts,
            "created_at":  str(self.created_at)[:19],
        }


@dataclass
class FeedbackState:
    """反馈采集系统当前状态快照。"""
    total_records:    int   = 0
    total_batches:    int   = 0
    current_cycle:    int   = 0

    # 按类型统计
    type_counts:      dict  = field(default_factory=dict)

    # 质量指标
    avg_severity:     float = 0.0
    avg_signal:       float = 0.0
    high_severity_pct:float = 0.0    # 严重程度 > 0.7 的比例

    # 最近批次摘要
    latest_batch:     dict  = field(default_factory=dict)

    updated_at:       datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "total_records":    self.total_records,
            "total_batches":    self.total_batches,
            "current_cycle":    self.current_cycle,
            "type_counts":      self.type_counts,
            "avg_severity":     round(self.avg_severity,     4),
            "avg_signal":       round(self.avg_signal,       4),
            "high_severity_pct":round(self.high_severity_pct,4),
            "latest_batch":     self.latest_batch,
            "updated_at":       str(self.updated_at)[:19],
        }
