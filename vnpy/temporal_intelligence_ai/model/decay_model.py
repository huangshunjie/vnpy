"""
temporal_intelligence_ai/model/decay_model.py

Alpha 衰减数据模型。

DecayMetrics  — 单次衰减计算的量化指标
DecayState    — 单个 Alpha 的完整衰减快照
DecayCurve    — 衰减曲线（时间序列）
DecayHistory  — 历史衰减记录序列
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from ..constant import DecayMode, CyclePhase, RegimeType


@dataclass
class DecayMetrics:
    """
    衰减量化指标集合。

    三种衰减模式的独立计算结果，最终 strength 为加权合并值。
    """
    exponential_strength:    float = 1.0   # 指数衰减后的强度 [0, 1]
    regime_strength:         float = 1.0   # Regime 调整后的强度 [0, 1]
    volatility_strength:     float = 1.0   # 波动率调整后的强度 [0, 1]
    combined_strength:       float = 1.0   # 三模式加权合并强度 [0, 1]

    half_life:               float = 0.0   # 半衰期（交易日）
    decay_rate:              float = 0.0   # 瞬时衰减率 λ
    age_bars:                int   = 0     # Alpha 已存续的 bar 数
    regime_penalty:          float = 0.0   # Regime 施加的额外衰减惩罚 [0, 1]
    volatility_adjustment:   float = 1.0   # 波动率调整乘子


@dataclass
class DecayState:
    """
    单个 Alpha 信号的完整衰减快照。

    由 DecayEngine.compute() 生成，通过 EVENT_ALPHA_DECAY_UPDATED 派发。
    """
    timestamp:       datetime    = field(default_factory=datetime.now)
    alpha_id:        str         = ""
    mode:            DecayMode   = DecayMode.EXPONENTIAL

    metrics:         DecayMetrics = field(default_factory=DecayMetrics)

    cycle_phase:     CyclePhase  = CyclePhase.UNKNOWN
    regime:          RegimeType  = RegimeType.UNKNOWN

    is_expired:      bool        = False   # 强度低于最小阈值
    expiry_bar:      int         = 0       # 预计到期 bar（基于当前衰减速率）

    def to_dict(self) -> dict:
        m = self.metrics
        return {
            "timestamp":            self.timestamp.isoformat(),
            "alpha_id":             self.alpha_id,
            "mode":                 self.mode.value,
            "combined_strength":    round(m.combined_strength, 4),
            "exponential_strength": round(m.exponential_strength, 4),
            "regime_strength":      round(m.regime_strength, 4),
            "volatility_strength":  round(m.volatility_strength, 4),
            "half_life":            round(m.half_life, 2),
            "decay_rate":           round(m.decay_rate, 6),
            "age_bars":             m.age_bars,
            "regime_penalty":       round(m.regime_penalty, 4),
            "volatility_adjustment": round(m.volatility_adjustment, 4),
            "cycle_phase":          self.cycle_phase.value,
            "regime":               self.regime.value,
            "is_expired":           self.is_expired,
            "expiry_bar":           self.expiry_bar,
        }


@dataclass
class DecayCurvePoint:
    """衰减曲线上的单个点。"""
    bar:      int   = 0
    strength: float = 1.0


@dataclass
class DecayCurve:
    """
    Alpha 衰减曲线，表示未来 horizon 个 bar 内的预期强度序列。

    仅基于当前已观测参数外推，不是价格预测。
    """
    alpha_id:  str                    = ""
    mode:      DecayMode              = DecayMode.EXPONENTIAL
    points:    List[DecayCurvePoint]  = field(default_factory=list)
    generated: datetime               = field(default_factory=datetime.now)

    def strengths(self) -> List[float]:
        return [p.strength for p in self.points]

    def bars(self) -> List[int]:
        return [p.bar for p in self.points]


@dataclass
class DecayHistory:
    """单个 Alpha 的历史衰减快照序列。"""
    alpha_id:  str               = ""
    max_size:  int               = 500
    records:   List[DecayState] = field(default_factory=list)

    def append(self, state: DecayState) -> None:
        self.records.append(state)
        if len(self.records) > self.max_size:
            self.records = self.records[-self.max_size:]

    def last(self) -> Optional[DecayState]:
        return self.records[-1] if self.records else None

    def strengths(self) -> List[float]:
        return [r.metrics.combined_strength for r in self.records]

    def timestamps(self) -> List[str]:
        return [r.timestamp.isoformat() for r in self.records]
