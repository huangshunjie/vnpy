"""
market_regime_ai/model/volatility_model.py  (Phase 3)

VolatilityState — 波动率状态数据模型。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import VolatilityRegime


@dataclass
class VolatilityState:
    """波动率状态快照（Phase 3 完整）。"""
    regime:          VolatilityRegime = VolatilityRegime.NORMAL
    realized_vol:    float = 0.0
    rolling_vol_20:  float = 0.0
    rolling_vol_60:  float = 0.0
    vol_percentile:  float = 0.0
    vol_ratio:       float = 1.0
    regime_shifted:  bool  = False
    updated_at:      datetime = field(default_factory=datetime.now)
    meta:            dict     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "regime":         self.regime.value,
            "realized_vol":   round(self.realized_vol,   4),
            "rolling_vol_20": round(self.rolling_vol_20, 4),
            "rolling_vol_60": round(self.rolling_vol_60, 4),
            "vol_percentile": round(self.vol_percentile, 4),
            "vol_ratio":      round(self.vol_ratio,      4),
            "regime_shifted": self.regime_shifted,
            "updated_at":     str(self.updated_at)[:19],
        }
