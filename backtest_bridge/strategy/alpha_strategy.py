"""
backtest_bridge/strategy/alpha_strategy.py

AlphaSignalStrategy — 专为 AlphaFactory 2.0 信号设计的回测策略。

特点：
  - 从 SignalFeed 读取 alpha IC 信号
  - 支持多 Alpha 叠加（加权组合）
  - 内置衰减权重（近期信号权重更高）
"""
from __future__ import annotations
from typing import Any

from vnpy_ctastrategy import CtaTemplate
from vnpy.trader.object import BarData, TickData, TradeData, OrderData

from ..constant import SignalSource, SignalDirection, PositionSizing
from ..model.signal_model import SignalRecord
from .signal_feed import SignalFeed


class AlphaSignalStrategy(CtaTemplate):
    """AlphaFactory 2.0 信号回测策略。"""

    author = "BacktestBridge"

    ic_threshold:    float = 0.05   # 最小 IC 阈值
    max_pos:         float = 1.0
    decay_halflife:  int   = 5      # 信号衰减半衰期（bars）
    long_threshold:  float = 0.1    # 做多阈值
    short_threshold: float = -0.1   # 做空阈值

    parameters = ["ic_threshold", "max_pos", "decay_halflife",
                  "long_threshold", "short_threshold"]
    variables  = ["pos", "current_ic", "bars_counted", "signals_used"]

    def __init__(self, cta_engine: Any, strategy_name: str,
                 vt_symbol: str, setting: dict) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.signal_feed:  SignalFeed | None = None
        self.current_ic:   float = 0.0
        self.bars_counted: int   = 0
        self.signals_used: int   = 0
        self._ic_history:  list[float] = []

    def on_init(self) -> None:
        self.write_log(f"[AlphaStrategy] init: ic_threshold={self.ic_threshold}")
        self.load_bar(1)

    def on_start(self) -> None:
        if self.signal_feed:
            self.signal_feed.reset_cursors()

    def on_stop(self) -> None:
        self.write_log(
            f"[AlphaStrategy] bars={self.bars_counted} signals={self.signals_used}")

    def on_bar(self, bar: BarData) -> None:
        self.bars_counted += 1
        if self.signal_feed is None:
            return

        sym = self.vt_symbol.split(".")[0]
        rec = self.signal_feed.get_signal(sym, bar.datetime,
                                           source=SignalSource.ALPHA_FACTORY)
        if rec is None:
            return

        ic = rec.strength
        self.current_ic = ic
        self._ic_history.append(ic)
        if len(self._ic_history) > self.decay_halflife * 3:
            self._ic_history.pop(0)

        # apply exponential decay weight to smooth IC
        smoothed_ic = self._smooth_ic()

        if abs(smoothed_ic) < self.ic_threshold:
            self._flatten(bar)
            return

        target = self._compute_pos(smoothed_ic)
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

    def _smooth_ic(self) -> float:
        if not self._ic_history:
            return 0.0
        import math
        lam   = math.log(2) / max(self.decay_halflife, 1)
        total_w = 0.0; total_ic = 0.0
        for i, ic in enumerate(reversed(self._ic_history)):
            w = math.exp(-lam * i)
            total_ic += ic * w
            total_w  += w
        return round(total_ic / total_w, 6) if total_w > 0 else 0.0

    def _compute_pos(self, ic: float) -> float:
        if ic >= self.long_threshold:
            return round(min(ic / self.long_threshold, 1.0) * self.max_pos, 4)
        elif ic <= self.short_threshold:
            return round(max(ic / abs(self.short_threshold), -1.0) * self.max_pos, 4)
        return 0.0

    def _flatten(self, bar: BarData) -> None:
        if self.pos > 0:
            self.sell(bar.close_price * 0.999, abs(self.pos))
        elif self.pos < 0:
            self.cover(bar.close_price * 1.001, abs(self.pos))
