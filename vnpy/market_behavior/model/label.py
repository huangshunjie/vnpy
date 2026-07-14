"""
market_behavior/model/label.py
BehaviorLabel — 行为标签对象
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
from ..constant import LabelType


@dataclass
class BehaviorLabel:
    """
    行为标签对象。
    由 LabelEngine 自动生成，描述股票当前的行为特征。
    """
    label_id:  str
    symbol:    str
    dt:        datetime

    # 该股票当前持有的所有标签
    labels:    List[LabelType] = field(default_factory=list)

    # 每个标签对应的置信度 {label.value: score}
    scores:    Dict[str, float] = field(default_factory=dict)

    # 标签触发依据（用于 UI 展示）
    reasons:   Dict[str, str] = field(default_factory=dict)

    extra:     Dict[str, Any] = field(default_factory=dict)

    def has_label(self, lt: LabelType) -> bool:
        return lt in self.labels

    def top_labels(self, n: int = 3) -> List[LabelType]:
        """按置信度返回前 N 个标签。"""
        ranked = sorted(
            self.labels,
            key=lambda l: self.scores.get(l.value, 0.0),
            reverse=True,
        )
        return ranked[:n]

    def to_dict(self) -> dict:
        return {
            "label_id": self.label_id,
            "symbol":   self.symbol,
            "dt":       str(self.dt)[:19],
            "labels":   [l.value for l in self.labels],
            "scores":   {k: round(v, 4) for k, v in self.scores.items()},
            "reasons":  self.reasons,
        }
