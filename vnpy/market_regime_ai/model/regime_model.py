"""
market_regime_ai/model/regime_model.py  (Phase 2)

MarketRegimeState + RegimeHistory — 市场状态数据模型（完整实现）。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import MarketRegime, RegimeConfidence, StrategyRecommendation


@dataclass
class MarketRegimeState:
    """当前市场状态快照（Phase 2 完整）。"""
    regime:             MarketRegime           = MarketRegime.UNKNOWN
    confidence:         RegimeConfidence       = RegimeConfidence.LOW
    confidence_score:   float = 0.0            # 数值置信度 [0, 1]
    recommendation:     StrategyRecommendation = StrategyRecommendation.NEUTRAL
    regime_score:       float = 0.0            # 胜出状态评分
    factor_scores:      dict  = field(default_factory=dict)  # 各状态评分
    vol_score:          float = 0.0            # 波动率因子输入
    trend_score:        float = 0.0            # 趋势因子输入
    trend_sign:         float = 0.0            # 趋势方向符号
    liq_score:          float = 0.0            # 流动性因子输入
    corr_score:         float = 0.0            # 相关性因子输入
    prev_regime:        MarketRegime   = MarketRegime.UNKNOWN
    regime_changed:     bool  = False
    duration_bars:      int   = 0
    stability:          float = 0.0
    detected_at:        datetime = field(default_factory=datetime.now)
    meta:               dict     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "regime":           self.regime.value,
            "confidence":       self.confidence.value,
            "confidence_score": round(self.confidence_score, 4),
            "recommendation":   self.recommendation.value,
            "regime_score":     round(self.regime_score,     4),
            "factor_scores":    {k: round(v, 4)
                                 for k, v in self.factor_scores.items()},
            "vol_score":        round(self.vol_score,   4),
            "trend_score":      round(self.trend_score, 4),
            "trend_sign":       self.trend_sign,
            "liq_score":        round(self.liq_score,   4),
            "corr_score":       round(self.corr_score,  4),
            "prev_regime":      self.prev_regime.value,
            "regime_changed":   self.regime_changed,
            "duration_bars":    self.duration_bars,
            "stability":        round(self.stability,   4),
            "detected_at":      str(self.detected_at)[:19],
        }


@dataclass
class RegimeRecord:
    """单次状态记录（用于历史追踪）。"""
    regime:           MarketRegime
    confidence_score: float
    duration_bars:    int
    started_at:       datetime
    ended_at:         datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    def to_dict(self) -> dict:
        return {
            "regime":           self.regime.value,
            "confidence_score": round(self.confidence_score, 4),
            "duration_bars":    self.duration_bars,
            "started_at":       str(self.started_at)[:19],
            "ended_at":         str(self.ended_at)[:19] if self.ended_at else None,
            "is_active":        self.is_active,
        }


class RegimeHistory:
    """
    市场状态历史管理器（Phase 2）。

    维护：
      - 状态序列（用于稳定性计算）
      - 状态切换记录
      - 各状态累计时长
    """

    def __init__(self, max_len: int = 500) -> None:
        self._max_len  = max_len
        self._sequence: list[MarketRegime]  = []
        self._records:  list[RegimeRecord]  = []
        self._current:  RegimeRecord | None = None

    def append(self, state: MarketRegimeState) -> None:
        """追加一个新状态快照。"""
        self._sequence.append(state.regime)
        if len(self._sequence) > self._max_len:
            self._sequence.pop(0)

        # 状态切换时，关闭旧记录，开启新记录
        if state.regime_changed or self._current is None:
            if self._current is not None:
                self._current.ended_at = state.detected_at
            self._current = RegimeRecord(
                regime           = state.regime,
                confidence_score = state.confidence_score,
                duration_bars    = state.duration_bars,
                started_at       = state.detected_at,
            )
            self._records.append(self._current)
        else:
            if self._current is not None:
                self._current.duration_bars = state.duration_bars
                self._current.confidence_score = state.confidence_score

    def get_sequence(self, limit: int = 50) -> list[str]:
        return [r.value for r in self._sequence[-limit:]]

    def get_records(self, limit: int = 20) -> list[dict]:
        return [r.to_dict() for r in self._records[-limit:]]

    def get_regime_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self._sequence:
            counts[r.value] = counts.get(r.value, 0) + 1
        return counts

    def get_latest_change(self) -> RegimeRecord | None:
        for rec in reversed(self._records):
            if rec.ended_at is not None:
                return rec
        return None

    def __len__(self) -> int:
        return len(self._sequence)
