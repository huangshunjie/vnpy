"""
temporal_intelligence_ai/model/validation_model.py

时间验证数据模型。

ValidationRecord    — 单条预测记录（预测值 + 实际值 + 时间戳）
ValidationResult    — 单次验证计算结果
ValidationMetrics   — 综合验证指标集合
ValidationState     — 完整验证快照（由 ValidationEngine 输出）
ValidationHistory   — 历史验证快照序列
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class ValidationRecord:
    """
    单条预测记录。

    存储某时刻的预测值与后续实现的实际值，
    用于事后验证（避免任何前瞻偏差）。
    """
    record_id:    str      = ""
    signal_type:  str      = ""      # 来源信号类型标签
    predicted_at: datetime = field(default_factory=datetime.now)
    realized_at:  Optional[datetime] = None
    predicted:    float    = 0.0     # 预测值（方向 / 幅度 / 强度）
    realized:     Optional[float] = None   # 实际实现值（None = 尚未到期）
    horizon_bars: int      = 1       # 预测时间跨度（bars）
    is_realized:  bool     = False


@dataclass
class ValidationResult:
    """单条记录的验证结果。"""
    record_id:    str   = ""
    error:        float = 0.0    # realized - predicted
    abs_error:    float = 0.0    # |error|
    sq_error:     float = 0.0    # error²
    pct_error:    float = 0.0    # error / |predicted|（若 predicted≠0）
    direction_hit: bool = False  # sign(predicted) == sign(realized)


@dataclass
class ValidationMetrics:
    """
    综合验证指标集合。

    覆盖：误差统计 / 方向准确率 / 衰减验证 / 时间依赖验证。
    """
    n_records:    int   = 0
    n_realized:   int   = 0

    mae:          float = 0.0    # Mean Absolute Error
    rmse:         float = 0.0    # Root Mean Squared Error
    mape:         float = 0.0    # Mean Absolute Percentage Error
    bias:         float = 0.0    # Mean Error（系统性偏差）
    direction_acc: float = 0.0   # 方向准确率 [0, 1]

    # 衰减验证：验证 Alpha 强度与实际表现的对齐程度
    decay_alignment:   float = 0.0   # [0, 1]，1=完美对齐
    decay_lead_time:   float = 0.0   # 衰减信号领先实际到期的 bar 数均值

    # 时间依赖验证：验证 ACF 结构预测的信号持续性
    memory_validity:   float = 0.0   # [0, 1]
    horizon_accuracy:  Dict[str, float] = field(default_factory=dict)

    # 综合评分
    temporal_health:   float = 0.0   # [0, 100]

    def to_dict(self) -> dict:
        return {
            "n_records":      self.n_records,
            "n_realized":     self.n_realized,
            "mae":            round(self.mae, 6),
            "rmse":           round(self.rmse, 6),
            "mape":           round(self.mape, 4),
            "bias":           round(self.bias, 6),
            "direction_acc":  round(self.direction_acc, 4),
            "decay_alignment": round(self.decay_alignment, 4),
            "decay_lead_time": round(self.decay_lead_time, 2),
            "memory_validity": round(self.memory_validity, 4),
            "temporal_health": round(self.temporal_health, 2),
        }


@dataclass
class ValidationState:
    """
    完整时间验证快照。

    由 ValidationEngine.validate() 生成，
    通过 EVENT_VALIDATION_UPDATED 派发。
    """
    timestamp:  datetime          = field(default_factory=datetime.now)
    metrics:    ValidationMetrics = field(default_factory=ValidationMetrics)
    results:    List[ValidationResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "metrics":   self.metrics.to_dict(),
        }


@dataclass
class ValidationHistory:
    """历史验证快照序列。"""
    max_size: int                     = 200
    records:  List[ValidationRecord]  = field(default_factory=list)
    snapshots: List[ValidationState]  = field(default_factory=list)

    def append_record(self, rec: ValidationRecord) -> None:
        self.records.append(rec)
        if len(self.records) > 2000:
            self.records = self.records[-2000:]

    def append_snapshot(self, state: ValidationState) -> None:
        self.snapshots.append(state)
        if len(self.snapshots) > self.max_size:
            self.snapshots = self.snapshots[-self.max_size:]

    def last(self) -> Optional[ValidationState]:
        return self.snapshots[-1] if self.snapshots else None

    def health_scores(self) -> List[float]:
        return [s.metrics.temporal_health for s in self.snapshots]
