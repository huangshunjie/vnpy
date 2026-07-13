"""
capital_allocation_ai/model/alpha_capital_model.py  (Phase 2)

AlphaCapitalScore — Alpha 资本评分数据模型（完善版）。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import AllocationStatus


@dataclass
class AlphaCapitalScore:
    """Alpha 资本竞争力评分（Phase 2 完善字段）。"""
    alpha_id:       str
    # 评分维度（Phase 2 实现）
    ic_mean:        float = 0.0
    stability:      float = 0.0     # IR = mean(IC)/std(IC)
    capacity:       float = 0.0     # 容量评分 [0, 1]
    decay:          float = 0.0     # 衰减评分 [0, 1]（基于半衰期）
    sharpe:         float = 0.0     # 年化 Sharpe
    # 综合资本评分
    capital_score:  float = 0.0     # [0, 1]，越高越好
    # 辅助指标
    ic_series_len:  int   = 0       # 用于计算的 IC 期数
    half_life:      float = 0.0     # IC 半衰期（交易日）
    volatility:     float = 0.0     # 年化波动率
    # 元数据
    status:         AllocationStatus = AllocationStatus.PENDING
    scored_at:      datetime = field(default_factory=datetime.now)
    meta:           dict     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "alpha_id":      self.alpha_id,
            "ic_mean":       round(self.ic_mean,       4),
            "stability":     round(self.stability,     4),
            "capacity":      round(self.capacity,      4),
            "decay":         round(self.decay,         4),
            "sharpe":        round(self.sharpe,        4),
            "capital_score": round(self.capital_score, 4),
            "ic_series_len": self.ic_series_len,
            "half_life":     round(self.half_life,     2),
            "volatility":    round(self.volatility,    4),
            "status":        self.status.value,
            "scored_at":     str(self.scored_at)[:19],
        }
