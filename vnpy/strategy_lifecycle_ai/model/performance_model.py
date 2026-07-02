"""
strategy_lifecycle_ai/model/performance_model.py  (Phase 2)

PerformanceState + PerformanceHistory — 策略表现数据模型（完整实现）。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import PerformanceRating


@dataclass
class PerformanceState:
    """策略表现快照（Phase 2 完整）。"""
    strategy_id:      str   = ""
    sharpe:           float = 0.0
    sortino:          float = 0.0
    calmar:           float = 0.0
    max_drawdown:     float = 0.0
    win_rate:         float = 0.0
    profit_factor:    float = 0.0
    total_pnl:        float = 0.0
    ann_return:       float = 0.0
    cum_return:       float = 0.0
    daily_pnl:        float = 0.0
    turnover:         float = 0.0
    trade_count:      int   = 0
    sample_count:     int   = 0
    rating:           PerformanceRating = PerformanceRating.UNKNOWN
    period:           str   = "daily"
    updated_at:       datetime = field(default_factory=datetime.now)
    multi_period:     dict     = field(default_factory=dict)
    meta:             dict     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "strategy_id":   self.strategy_id,
            "sharpe":        round(self.sharpe,        4),
            "sortino":       round(self.sortino,       4),
            "calmar":        round(self.calmar,        4),
            "max_drawdown":  round(self.max_drawdown,  4),
            "win_rate":      round(self.win_rate,      4),
            "profit_factor": round(self.profit_factor, 4),
            "total_pnl":     round(self.total_pnl,     4),
            "ann_return":    round(self.ann_return,     4),
            "cum_return":    round(self.cum_return,     4),
            "daily_pnl":     round(self.daily_pnl,     4),
            "turnover":      round(self.turnover,      4),
            "trade_count":   self.trade_count,
            "sample_count":  self.sample_count,
            "rating":        self.rating.value,
            "period":        self.period,
            "updated_at":    str(self.updated_at)[:19],
        }


@dataclass
class PerformanceRecord:
    """单次绩效记录（用于历史追踪）。"""
    strategy_id: str
    snapshot:    PerformanceState
    bar_index:   int
    recorded_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        d = self.snapshot.to_dict()
        d["bar_index"]   = self.bar_index
        d["recorded_at"] = str(self.recorded_at)[:19]
        return d


class PerformanceHistory:
    """策略绩效历史管理器。"""

    def __init__(self, strategy_id: str, max_len: int = 500) -> None:
        self.strategy_id = strategy_id
        self._records:   list[PerformanceRecord] = []
        self._max_len    = max_len
        self._bar        = 0

    def append(self, state: PerformanceState) -> None:
        self._bar += 1
        rec = PerformanceRecord(
            strategy_id = self.strategy_id,
            snapshot    = state,
            bar_index   = self._bar,
        )
        self._records.append(rec)
        if len(self._records) > self._max_len:
            self._records.pop(0)

    def get_records(self, limit: int = 30) -> list[dict]:
        return [r.to_dict() for r in self._records[-limit:]]

    def get_sharpe_series(self) -> list[float]:
        return [r.snapshot.sharpe for r in self._records]

    def get_drawdown_series(self) -> list[float]:
        return [r.snapshot.max_drawdown for r in self._records]

    def get_latest(self) -> PerformanceState | None:
        if self._records:
            return self._records[-1].snapshot
        return None

    def __len__(self) -> int:
        return len(self._records)
