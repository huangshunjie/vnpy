"""
market_regime_ai/model/decision_model.py  (Phase 4)

DecisionSignal — 决策信号数据模型。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import MarketRegime, StrategyRecommendation


@dataclass
class DecisionSignal:
    """
    市场状态决策信号快照（Phase 4）。

    输出方向：
      → Capital Allocation AI : capital_adjustment
      → Quant OS / Risk        : risk_adjustment
      → 下游策略系统            : recommendation
    """
    regime:             MarketRegime           = MarketRegime.UNKNOWN
    recommendation:     StrategyRecommendation = StrategyRecommendation.NEUTRAL
    capital_adjustment: float = 1.0    # [0.40, 1.50] 资本调整系数
    risk_adjustment:    float = 1.0    # [0.30, 1.30] 风险调整系数
    position_limit:     float = 1.0    # [0.10, 1.50] 仓位上限
    rebalance_urgency:  float = 0.0    # [0,  1]     再平衡紧迫度
    confidence:         float = 0.0    # [0,  1]     置信度
    action:             str   = "MAINTAIN"
    regime_changed:     bool  = False
    created_at:         datetime = field(default_factory=datetime.now)
    meta:               dict     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "regime":             self.regime.value,
            "recommendation":     self.recommendation.value,
            "capital_adjustment": round(self.capital_adjustment, 4),
            "risk_adjustment":    round(self.risk_adjustment,    4),
            "position_limit":     round(self.position_limit,     4),
            "rebalance_urgency":  round(self.rebalance_urgency,  4),
            "confidence":         round(self.confidence,         4),
            "action":             self.action,
            "regime_changed":     self.regime_changed,
            "created_at":         str(self.created_at)[:19],
        }


@dataclass
class DecisionRecord:
    """单次决策历史记录。"""
    signal:     DecisionSignal
    bar_index:  int
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        d = self.signal.to_dict()
        d["bar_index"] = self.bar_index
        return d


class DecisionHistory:
    """决策信号历史管理器。"""

    def __init__(self, max_len: int = 200) -> None:
        self._records: list[DecisionRecord] = []
        self._max_len = max_len
        self._bar     = 0

    def append(self, signal: DecisionSignal) -> None:
        self._bar += 1
        rec = DecisionRecord(signal=signal, bar_index=self._bar)
        self._records.append(rec)
        if len(self._records) > self._max_len:
            self._records.pop(0)

    def get_records(self, limit: int = 20) -> list[dict]:
        return [r.to_dict() for r in self._records[-limit:]]

    def get_latest(self) -> DecisionSignal | None:
        if self._records:
            return self._records[-1].signal
        return None

    def count_action(self, action: str) -> int:
        return sum(1 for r in self._records
                   if r.signal.action == action)

    def __len__(self) -> int:
        return len(self._records)
