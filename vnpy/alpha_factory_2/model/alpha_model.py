"""
alpha_factory_2/model/alpha_model.py

AlphaSignal — Alpha 信号数据模型（Phase 1 Stub）。
Phase 2 实现生成逻辑。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import AlphaStatus, AlphaType


@dataclass
class AlphaSignal:
    """Alpha 信号（不可变，一经生成不得修改）。"""
    alpha_id:    str
    alpha_type:  AlphaType             = AlphaType.LINEAR_COMBO
    status:      AlphaStatus           = AlphaStatus.GENERATED
    factors:     list[str]             = field(default_factory=list)
    weights:     list[float]           = field(default_factory=list)
    expression:  str                   = ""       # e.g. "0.3*F1 + 0.5*F2"
    created_at:  datetime              = field(default_factory=datetime.now)
    meta:        dict                  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "alpha_id":   self.alpha_id,
            "alpha_type": self.alpha_type.value,
            "status":     self.status.value,
            "factors":    self.factors,
            "weights":    self.weights,
            "expression": self.expression,
            "created_at": str(self.created_at)[:19],
        }
