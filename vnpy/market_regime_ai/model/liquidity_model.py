"""
market_regime_ai/model/liquidity_model.py  (Phase 3)

LiquidityState — 流动性状态数据模型。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import LiquidityLevel


@dataclass
class LiquidityState:
    """流动性状态快照（Phase 3 完整）。"""
    level:             LiquidityLevel = LiquidityLevel.NORMAL
    volume_ratio:      float = 1.0
    turnover_ratio:    float = 1.0
    spread_proxy:      float = 0.0
    vol_percentile:    float = 0.5
    illiquidity_score: float = 0.0
    updated_at:        datetime = field(default_factory=datetime.now)
    meta:              dict     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "level":             self.level.value,
            "volume_ratio":      round(self.volume_ratio,      4),
            "turnover_ratio":    round(self.turnover_ratio,    4),
            "spread_proxy":      round(self.spread_proxy,      6),
            "vol_percentile":    round(self.vol_percentile,    4),
            "illiquidity_score": round(self.illiquidity_score, 4),
            "updated_at":        str(self.updated_at)[:19],
        }
