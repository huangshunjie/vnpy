"""
market_regime_ai/model/trend_model.py  (Phase 3)

TrendState — 趋势状态数据模型。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import TrendDirection


@dataclass
class TrendState:
    """趋势状态快照（Phase 3 完整）。"""
    direction:     TrendDirection = TrendDirection.FLAT
    strength:      float = 0.0
    persistence:   float = 0.0
    adx:           float = 0.0
    slope:         float = 0.0
    r_squared:     float = 0.0
    bars_in_trend: int   = 0
    updated_at:    datetime = field(default_factory=datetime.now)
    meta:          dict     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "direction":     self.direction.value,
            "strength":      round(self.strength,    4),
            "persistence":   round(self.persistence, 4),
            "adx":           round(self.adx,         4),
            "slope":         round(self.slope,       6),
            "r_squared":     round(self.r_squared,   4),
            "bars_in_trend": self.bars_in_trend,
            "updated_at":    str(self.updated_at)[:19],
        }
