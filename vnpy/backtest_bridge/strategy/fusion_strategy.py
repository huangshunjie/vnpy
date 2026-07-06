"""
backtest_bridge/strategy/fusion_strategy.py

FusionSignalStrategy — 基于 DIL FusedState 的多维度融合信号回测策略。

接入 DataIntelligenceAI 的 6 维融合状态：
  market / alpha / portfolio / execution / risk / regime
并结合 MarketRegimeAI 的 Regime 信号做动态仓位调整。
"""
from __future__ import annotations
from typing import Any

from vnpy_ctastrategy import CtaTemplate
from vnpy.trader.object import BarData, TickData, TradeData, OrderData

from ..constant import SignalSource, SignalDirection
from ..model.signal_model import SignalRecord
from .signal_feed import SignalFeed


class FusionSignalStrategy(CtaTemplate):
    """DIL 融合信号 + Regime 调制 回测策略。"""

    author = "BacktestBridge"

    fusion_threshold: float = 0.55    # unified_score > 0.55 → Long
    inverse_threshold:float = 0.45    # unified_score < 0.45 → Short
    max_pos:          float = 1.0
    regime_scale:     float = 1.0     # Regime 调制系数 [0, 2]
    confidence_min:   float = 0.5     # 置信度低于此不交易

    parameters = ["fusion_threshold", "inverse_threshold", "max_pos",
                  "regime_scale", "confidence_min"]
    variables  = ["pos", "unified_score", "regime_prob",
                  "bars_counted", "signals_used"]

    def __init__(self, cta_engine: Any, strategy_name: str,
                 vt_symbol: str, setting: dict) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.signal_feed:   SignalFeed | None = None
        self.unified_score: float = 0.5
        self.regime_prob:   float = 0.5
        self.bars_counted:  int   = 0
        self.signals_used:  int   = 0

    def on_init(self) -> None:
        self.write_log(
            f"[FusionStrategy] init: fusion_thr={self.fusion_threshold} "
            f"inverse_thr={self.inverse_threshold}")
        self.load_bar(1)

    def on_start(self) -> None:
        if self.signal_feed:
            self.signal_feed.reset_cursors()

    def on_stop(self) -> None:
        self.write_log(
            f"[FusionStrategy] bars={self.bars_counted} signals={self.signals_used}")

    def on_bar(self, bar: BarData) -> None:
        self.bars_counted += 1
        if self.signal_feed is None:
            return

        sym = self.vt_symbol.split(".")[0]

        # 1. DIL fusion signal
        fusion_rec = self.signal_feed.get_signal(
            sym, bar.datetime, source=SignalSource.DATA_FUSION)

        # 2. Regime signal (optional overlay)
        regime_rec = self.signal_feed.get_signal(
            sym, bar.datetime, source=SignalSource.MARKET_REGIME)

        if fusion_rec is None:
            return

        self.unified_score = fusion_rec.strength   # store as [-1, 1] or [0, 1]
        # normalise to [0, 1] if stored as strength
        score = (fusion_rec.strength + 1.0) / 2.0 if fusion_rec.strength < 0 \
                else fusion_rec.strength

        # confidence gate
        if fusion_rec.confidence < self.confidence_min:
            self._flatten(bar)
            return

        # 3. regime modulation
        regime_mult = 1.0
        if regime_rec is not None:
            self.regime_prob = (regime_rec.strength + 1.0) / 2.0 \
                               if regime_rec.strength < 0 else regime_rec.strength
            # bull regime → scale up long; bear → scale down
            regime_mult = 0.5 + self.regime_prob * self.regime_scale

        # 4. target position
        target = self._compute_target(score, regime_mult, fusion_rec.confidence)
        diff   = target - self.pos
        if abs(diff) < 1e-9:
            return

        self.signals_used += 1
        self.cancel_all()

        if diff > 0:
            self.buy(bar.close_price * 1.001, abs(diff))
        else:
            if self.pos > 0:
                sell_vol = min(abs(diff), self.pos)
                self.sell(bar.close_price * 0.999, sell_vol)
                if abs(diff) > sell_vol:
                    self.short(bar.close_price * 0.999, abs(diff) - sell_vol)
            else:
                self.short(bar.close_price * 0.999, abs(diff))

    def on_tick(self, tick: TickData) -> None:
        pass

    def on_trade(self, trade: TradeData) -> None:
        self.put_event()

    def on_order(self, order: OrderData) -> None:
        pass

    def _compute_target(self, score: float, regime_mult: float,
                         confidence: float) -> float:
        """
        score ∈ [0, 1]:
          > fusion_threshold  → Long
          < inverse_threshold → Short
          else                → Flat
        """
        if score >= self.fusion_threshold:
            size = (score - self.fusion_threshold) / (1.0 - self.fusion_threshold)
            return round(size * self.max_pos * regime_mult * confidence, 4)
        elif score <= self.inverse_threshold:
            size = (self.inverse_threshold - score) / self.inverse_threshold
            return round(-size * self.max_pos * regime_mult * confidence, 4)
        return 0.0

    def _flatten(self, bar: BarData) -> None:
        if self.pos > 0:
            self.sell(bar.close_price * 0.999, abs(self.pos))
        elif self.pos < 0:
            self.cover(bar.close_price * 1.001, abs(self.pos))
