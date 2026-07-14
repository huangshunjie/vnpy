"""
market_behavior/model/behavior_event.py
BehaviorEvent — 价格行为事件对象
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from ..constant import EventType, ContinuousType


@dataclass
class BehaviorEvent:
    """
    价格行为事件对象。
    由 EventDetectEngine 生成，描述一个股票在某窗口内触发的行为事件。
    """
    event_id:   str
    symbol:     str
    event_type: EventType
    dt:         datetime                     # 触发时间（最后一根K线）

    # ── 事件参数 ──────────────────────────────────────────────────────
    window:     int   = 1                    # 统计窗口（日）
    count:      int   = 1                    # 触发次数
    threshold:  float = 0.0                  # 触发阈值（如涨幅%）
    value:      float = 0.0                  # 实际触发值

    # ── 连续行为扩展 ──────────────────────────────────────────────────
    continuous_type: ContinuousType = ContinuousType.RISE
    days:            int = 0                 # 连续天数（连续行为专用）

    # ── 附加信息 ──────────────────────────────────────────────────────
    extra:  Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id":   self.event_id,
            "symbol":     self.symbol,
            "event_type": self.event_type.value,
            "dt":         str(self.dt)[:19],
            "window":     self.window,
            "count":      self.count,
            "threshold":  self.threshold,
            "value":      round(self.value, 4),
            "days":       self.days,
        }
