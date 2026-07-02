"""
alpha_factory_2/model/score_model.py

AlphaScore — Alpha 评分数据模型（Phase 1 Stub）。
Phase 3 实现 IC/RankIC/Stability/Turnover/Decay 计算。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AlphaScore:
    """Alpha 综合评分记录（stub）。"""
    alpha_id:    str
    ic:          float = 0.0
    rank_ic:     float = 0.0
    stability:   float = 0.0
    turnover:    float = 0.0
    decay:       float = 0.0
    total_score: float = 0.0
    scored_at:   datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "alpha_id":    self.alpha_id,
            "ic":          round(self.ic, 4),
            "rank_ic":     round(self.rank_ic, 4),
            "stability":   round(self.stability, 4),
            "turnover":    round(self.turnover, 4),
            "decay":       round(self.decay, 4),
            "total_score": round(self.total_score, 4),
            "scored_at":   str(self.scored_at)[:19],
        }
