"""
market_behavior/model/pattern.py
PatternSignal — 单K形态 / K线组合 / 突破信号
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from ..constant import PatternType, SequenceType, BreakoutType


@dataclass
class PatternSignal:
    """
    单K形态识别结果。
    由 PatternEngine 生成。
    """
    signal_id:    str
    symbol:       str
    pattern_type: PatternType
    dt:           datetime

    # 触发K线的关键比率
    body_ratio:         float = 0.0   # 实体占振幅比
    upper_shadow_ratio: float = 0.0
    lower_shadow_ratio: float = 0.0
    change_pct:         float = 0.0

    # 连续N天触发
    consecutive_days: int = 1

    confidence: float = 1.0           # 0~1，形态置信度（后续可扩展）
    extra:      Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "signal_id":          self.signal_id,
            "symbol":             self.symbol,
            "pattern_type":       self.pattern_type.value,
            "dt":                 str(self.dt)[:19],
            "body_ratio":         round(self.body_ratio, 4),
            "upper_shadow_ratio": round(self.upper_shadow_ratio, 4),
            "lower_shadow_ratio": round(self.lower_shadow_ratio, 4),
            "change_pct":         round(self.change_pct, 4),
            "consecutive_days":   self.consecutive_days,
            "confidence":         round(self.confidence, 4),
        }


@dataclass
class SequenceSignal:
    """
    K线组合模式识别结果。
    由 SequenceEngine 生成。
    """
    signal_id:     str
    symbol:        str
    sequence_type: SequenceType
    dt:            datetime          # 最后一根K线时间

    bars:          int = 3           # 组合K线根数
    dsl_pattern:   str = ""          # 自定义 DSL（如 "UP DOWN UP"）
    confidence:    float = 1.0
    extra:         Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "signal_id":     self.signal_id,
            "symbol":        self.symbol,
            "sequence_type": self.sequence_type.value,
            "dt":            str(self.dt)[:19],
            "bars":          self.bars,
            "dsl_pattern":   self.dsl_pattern,
            "confidence":    round(self.confidence, 4),
        }


@dataclass
class BreakoutSignal:
    """
    突破信号。
    由 BreakoutEngine 生成。
    """
    signal_id:     str
    symbol:        str
    breakout_type: BreakoutType
    dt:            datetime

    window:        int   = 20         # 突破窗口（如 20日新高）
    ref_value:     float = 0.0        # 参考值（如近20日最高价）
    current_value: float = 0.0        # 当前触发值
    vol_ratio:     float = 0.0        # 当日量/均量（量能突破专用）
    extra:         Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "signal_id":     self.signal_id,
            "symbol":        self.symbol,
            "breakout_type": self.breakout_type.value,
            "dt":            str(self.dt)[:19],
            "window":        self.window,
            "ref_value":     round(self.ref_value, 4),
            "current_value": round(self.current_value, 4),
            "vol_ratio":     round(self.vol_ratio, 4),
        }
