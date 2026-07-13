"""
strategy_lifecycle_ai/model/decay_model.py  (Phase 3)

DecayState + DecayHistory — 策略衰减状态数据模型（完整实现）。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import DecayLevel


@dataclass
class DecayState:
    """策略衰减状态快照（Phase 3 完整）。"""
    strategy_id:     str        = ""
    decay_level:     DecayLevel = DecayLevel.NONE
    decay_score:     float      = 0.0
    sharpe_slope:    float      = 0.0
    dd_expansion:    float      = 0.0
    ic_decay_proxy:  float      = 0.0
    perf_slope:      float      = 0.0
    decay_days:      int        = 0
    regime_sensitivity: float   = 0.0
    detected_at:     datetime   = field(default_factory=datetime.now)
    prev_level:      DecayLevel = DecayLevel.NONE
    level_changed:   bool       = False
    meta:            dict       = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "strategy_id":       self.strategy_id,
            "decay_level":       self.decay_level.value,
            "decay_score":       round(self.decay_score,        4),
            "sharpe_slope":      round(self.sharpe_slope,       6),
            "dd_expansion":      round(self.dd_expansion,       4),
            "ic_decay_proxy":    round(self.ic_decay_proxy,     4),
            "perf_slope":        round(self.perf_slope,         6),
            "decay_days":        self.decay_days,
            "regime_sensitivity": round(self.regime_sensitivity, 4),
            "level_changed":     self.level_changed,
            "prev_level":        self.prev_level.value,
            "detected_at":       str(self.detected_at)[:19],
        }


@dataclass
class DecayRecord:
    """单次衰减检测记录。"""
    strategy_id: str
    snapshot:    DecayState
    bar_index:   int
    recorded_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        d = self.snapshot.to_dict()
        d["bar_index"]   = self.bar_index
        d["recorded_at"] = str(self.recorded_at)[:19]
        return d


class DecayHistory:
    """策略衰减历史管理器。"""

    def __init__(self, strategy_id: str, max_len: int = 500) -> None:
        self.strategy_id = strategy_id
        self._records:   list[DecayRecord] = []
        self._levels:    list[DecayLevel]  = []
        self._max_len    = max_len
        self._bar        = 0

    def append(self, state: DecayState) -> None:
        self._bar += 1
        self._records.append(DecayRecord(
            strategy_id = self.strategy_id,
            snapshot    = state,
            bar_index   = self._bar,
        ))
        self._levels.append(state.decay_level)
        if len(self._records) > self._max_len:
            self._records.pop(0)
            self._levels.pop(0)

    def get_records(self, limit: int = 30) -> list[dict]:
        return [r.to_dict() for r in self._records[-limit:]]

    def get_level_history(self) -> list[DecayLevel]:
        return list(self._levels)

    def get_score_series(self) -> list[float]:
        return [r.snapshot.decay_score for r in self._records]

    def get_latest(self) -> DecayState | None:
        return self._records[-1].snapshot if self._records else None

    def __len__(self) -> int:
        return len(self._records)
