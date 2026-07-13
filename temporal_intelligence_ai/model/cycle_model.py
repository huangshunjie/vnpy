"""
temporal_intelligence_ai/model/cycle_model.py

市场周期数据模型。

CycleState    — 单次周期分析结果快照
CycleHistory  — 周期历史序列
CycleMetrics  — 周期量化指标集合
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from ..constant import CyclePhase, RegimeType


@dataclass
class CycleMetrics:
    """
    周期量化指标集合。

    所有指标均基于历史市场数据计算，无前瞻偏差。
    Cycle = f(volatility, trend, liquidity, correlation)
    """
    volatility:       float = 0.0   # 滚动波动率（annualized）
    trend_strength:   float = 0.0   # 趋势强度 [-1, 1]，正值为上行趋势
    liquidity_score:  float = 0.0   # 流动性评分 [0, 1]
    correlation:      float = 0.0   # 跨资产相关性均值
    momentum:         float = 0.0   # 动量指标（滚动收益率）
    breadth:          float = 0.0   # 市场宽度（上涨品种占比）
    drawdown:         float = 0.0   # 当前回撤深度（负值）


@dataclass
class CycleState:
    """
    单次周期分析结果快照。

    由 CycleEngine.analyze() 生成，通过 EVENT_CYCLE_DETECTED 派发。
    """
    timestamp:      datetime              = field(default_factory=datetime.now)
    phase:          CyclePhase            = CyclePhase.UNKNOWN
    regime:         RegimeType            = RegimeType.UNKNOWN
    confidence:     float                 = 0.0    # 识别置信度 [0, 1]
    metrics:        CycleMetrics          = field(default_factory=CycleMetrics)

    phase_duration: int                   = 0      # 当前阶段已持续的周期数（bars）
    prev_phase:     CyclePhase            = CyclePhase.UNKNOWN
    is_transitioning: bool                = False  # 是否处于阶段切换窗口

    def to_dict(self) -> dict:
        return {
            "timestamp":       self.timestamp.isoformat(),
            "phase":           self.phase.value,
            "regime":          self.regime.value,
            "confidence":      round(self.confidence, 4),
            "phase_duration":  self.phase_duration,
            "prev_phase":      self.prev_phase.value,
            "is_transitioning": self.is_transitioning,
            "volatility":      round(self.metrics.volatility, 6),
            "trend_strength":  round(self.metrics.trend_strength, 4),
            "liquidity_score": round(self.metrics.liquidity_score, 4),
            "correlation":     round(self.metrics.correlation, 4),
            "momentum":        round(self.metrics.momentum, 6),
            "breadth":         round(self.metrics.breadth, 4),
            "drawdown":        round(self.metrics.drawdown, 6),
        }


@dataclass
class CycleHistory:
    """周期历史序列，维护最近 N 次识别结果。"""
    max_size: int               = 500
    records:  List[CycleState] = field(default_factory=list)

    def append(self, state: CycleState) -> None:
        self.records.append(state)
        if len(self.records) > self.max_size:
            self.records = self.records[-self.max_size:]

    def last(self) -> CycleState | None:
        return self.records[-1] if self.records else None

    def phases(self) -> list[str]:
        return [r.phase.value for r in self.records]

    def confidences(self) -> list[float]:
        return [r.confidence for r in self.records]

    def timestamps(self) -> list[str]:
        return [r.timestamp.isoformat() for r in self.records]
