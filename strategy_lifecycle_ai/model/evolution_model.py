"""
strategy_lifecycle_ai/model/evolution_model.py  (Phase 4)

EvolutionRecord + EvolutionHistory — 策略进化数据模型（完整实现）。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import EvolutionType


@dataclass
class EvolutionRecord:
    """策略单次进化记录（Phase 4 完整）。"""
    evolution_id:    str           = ""
    strategy_id:     str           = ""
    evolution_type:  EvolutionType = EvolutionType.NONE
    parent_id:       str           = ""
    peer_id:         str           = ""       # 重组时的第二父本
    params_before:   dict          = field(default_factory=dict)
    params_after:    dict          = field(default_factory=dict)
    weights_before:  dict          = field(default_factory=dict)
    weights_after:   dict          = field(default_factory=dict)
    trigger_reason:  str           = ""
    decay_score:     float         = 0.0
    sharpe_before:   float         = 0.0
    sharpe_after:    float         = 0.0
    improvement:     float         = 0.0      # sharpe_after - sharpe_before
    success:         bool          = False
    evolution_score: float         = 0.0
    evolved_at:      datetime      = field(default_factory=datetime.now)
    meta:            dict          = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "evolution_id":   self.evolution_id,
            "strategy_id":    self.strategy_id,
            "evolution_type": self.evolution_type.value,
            "parent_id":      self.parent_id,
            "peer_id":        self.peer_id,
            "trigger_reason": self.trigger_reason,
            "decay_score":    round(self.decay_score,     4),
            "sharpe_before":  round(self.sharpe_before,   4),
            "sharpe_after":   round(self.sharpe_after,    4),
            "improvement":    round(self.improvement,     4),
            "success":        self.success,
            "evolution_score": round(self.evolution_score, 4),
            "evolved_at":     str(self.evolved_at)[:19],
        }


class EvolutionHistory:
    """策略进化历史管理器（Phase 4 完整）。"""

    def __init__(self, strategy_id: str, max_len: int = 200) -> None:
        self.strategy_id  = strategy_id
        self._records:    list[EvolutionRecord] = []
        self._max_len     = max_len

    def append(self, record: EvolutionRecord) -> None:
        self._records.append(record)
        if len(self._records) > self._max_len:
            self._records.pop(0)

    def get_records(self, limit: int = 20) -> list[dict]:
        return [r.to_dict() for r in self._records[-limit:]]

    def get_successful(self) -> list[EvolutionRecord]:
        return [r for r in self._records if r.success]

    def get_by_type(self, etype: EvolutionType) -> list[EvolutionRecord]:
        return [r for r in self._records if r.evolution_type == etype]

    def get_improvement_series(self) -> list[float]:
        return [r.improvement for r in self._records]

    def get_latest(self) -> EvolutionRecord | None:
        return self._records[-1] if self._records else None

    def success_rate(self) -> float:
        if not self._records:
            return 0.0
        return len(self.get_successful()) / len(self._records)

    def total_improvement(self) -> float:
        return sum(r.improvement for r in self.get_successful())

    def __len__(self) -> int:
        return len(self._records)
