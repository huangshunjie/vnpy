"""
market_behavior/model/behavior_factor.py
BehaviorFactor — 行为因子对象
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from ..constant import FactorType


@dataclass
class BehaviorFactor:
    """
    行为因子对象。
    由 FactorEngine 计算生成，输出给 Alpha Factory。
    """
    factor_id:   str
    symbol:      str
    factor_type: FactorType
    dt:          datetime

    # 计算窗口
    window:      int   = 20

    # 因子值
    value:       float = 0.0

    # 归一化值（0~1，由 FactorEngine 标准化后填充）
    norm_value:  float = 0.0

    # 组合因子专用：各子因子权重与分值
    components:  Dict[str, float] = field(default_factory=dict)

    # 描述（如: "0.4*RiseDays + 0.3*LimitCount + 0.3*Breakout"）
    formula:     str = ""
    extra:       Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "factor_id":   self.factor_id,
            "symbol":      self.symbol,
            "factor_type": self.factor_type.value,
            "dt":          str(self.dt)[:19],
            "window":      self.window,
            "value":       round(self.value, 6),
            "norm_value":  round(self.norm_value, 6),
            "components":  {k: round(v, 6) for k, v in self.components.items()},
            "formula":     self.formula,
        }
