"""
temporal_intelligence_ai/model/transition_model.py

状态转移数据模型。

TransitionSignal    — 单次转移检测信号
TransitionEvent     — 已确认的状态转移事件
TransitionState     — 完整转移分析快照
TransitionHistory   — 历史转移记录序列
RegimeProbability   — 各 Regime 的概率分布
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from ..constant import RegimeType, TransitionType, CyclePhase


@dataclass
class TransitionSignal:
    """
    单次转移检测原始信号。

    由三种检测器独立输出，汇聚到 TransitionEngine 综合判断。
    """
    signal_type:   TransitionType = TransitionType.REGIME_SHIFT
    strength:      float          = 0.0   # 信号强度 [0, 1]
    is_triggered:  bool           = False
    threshold:     float          = 0.0   # 触发阈值
    raw_value:     float          = 0.0   # 检测指标的原始值
    description:   str            = ""


@dataclass
class RegimeProbability:
    """各 Regime 的后验概率分布（和为 1）。"""
    probabilities: Dict[str, float] = field(default_factory=dict)

    def dominant(self) -> str:
        if not self.probabilities:
            return RegimeType.UNKNOWN.value
        return max(self.probabilities, key=self.probabilities.get)

    def confidence(self) -> float:
        if not self.probabilities:
            return 0.0
        return max(self.probabilities.values())

    def to_dict(self) -> dict:
        return {k: round(v, 4) for k, v in self.probabilities.items()}


@dataclass
class TransitionEvent:
    """
    已确认的状态转移事件。

    当综合置信度超过确认阈值时，由 TransitionEngine 生成。
    """
    timestamp:      datetime       = field(default_factory=datetime.now)
    transition_type: TransitionType = TransitionType.REGIME_SHIFT
    from_regime:    RegimeType     = RegimeType.UNKNOWN
    to_regime:      RegimeType     = RegimeType.UNKNOWN
    from_phase:     CyclePhase     = CyclePhase.UNKNOWN
    confidence:     float          = 0.0
    trigger_signals: List[TransitionSignal] = field(default_factory=list)
    description:    str            = ""

    def to_dict(self) -> dict:
        return {
            "timestamp":       self.timestamp.isoformat(),
            "type":            self.transition_type.value,
            "from_regime":     self.from_regime.value,
            "to_regime":       self.to_regime.value,
            "from_phase":      self.from_phase.value,
            "confidence":      round(self.confidence, 4),
            "description":     self.description,
        }


@dataclass
class TransitionState:
    """
    完整转移分析快照。

    由 TransitionEngine.detect() 生成，通过 EVENT_TRANSITION_DETECTED 派发。
    """
    timestamp:           datetime              = field(default_factory=datetime.now)

    # 当前 Regime 概率分布
    regime_probs:        RegimeProbability     = field(default_factory=RegimeProbability)

    # 三类检测信号
    regime_signal:       TransitionSignal      = field(
        default_factory=lambda: TransitionSignal(TransitionType.REGIME_SHIFT))
    volatility_signal:   TransitionSignal      = field(
        default_factory=lambda: TransitionSignal(TransitionType.VOLATILITY_BREAK))
    liquidity_signal:    TransitionSignal      = field(
        default_factory=lambda: TransitionSignal(TransitionType.LIQUIDITY_REGIME))

    # 综合转移概率与置信度
    transition_prob:     float                 = 0.0   # 发生转移的概率 [0, 1]
    transition_confidence: float               = 0.0   # 当前结论置信度 [0, 1]
    is_transitioning:    bool                  = False # 是否处于转移窗口

    # 最近已确认事件
    latest_event:        Optional[TransitionEvent] = None

    current_regime:      RegimeType            = RegimeType.UNKNOWN
    current_phase:       CyclePhase            = CyclePhase.UNKNOWN

    def to_dict(self) -> dict:
        return {
            "timestamp":             self.timestamp.isoformat(),
            "transition_prob":       round(self.transition_prob, 4),
            "transition_confidence": round(self.transition_confidence, 4),
            "is_transitioning":      self.is_transitioning,
            "current_regime":        self.current_regime.value,
            "current_phase":         self.current_phase.value,
            "regime_probs":          self.regime_probs.to_dict(),
            "regime_signal":         self.regime_signal.strength,
            "volatility_signal":     self.volatility_signal.strength,
            "liquidity_signal":      self.liquidity_signal.strength,
        }


@dataclass
class TransitionHistory:
    """历史转移快照 + 已确认事件列表。"""
    max_snapshots: int                    = 300
    snapshots:     List[TransitionState] = field(default_factory=list)
    events:        List[TransitionEvent] = field(default_factory=list)

    def append_snapshot(self, state: TransitionState) -> None:
        self.snapshots.append(state)
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots = self.snapshots[-self.max_snapshots:]

    def append_event(self, event: TransitionEvent) -> None:
        self.events.append(event)

    def last_snapshot(self) -> Optional[TransitionState]:
        return self.snapshots[-1] if self.snapshots else None

    def transition_probs(self) -> List[float]:
        return [s.transition_prob for s in self.snapshots]

    def recent_events(self, n: int = 20) -> List[TransitionEvent]:
        return self.events[-n:]
