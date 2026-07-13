"""
backtest_bridge/strategy/bridge_strategy.py

BridgeCtaStrategy — CtaTemplate 子类，桥接外部信号与 VeighNa 原生回测。

工作原理：
  每根 bar 到达时：
    1. 从 SignalFeed 查询当前信号
    2. 按 PositionSizing 计算目标仓位
    3. 与当前仓位对比，发出买卖指令
    4. 可选：使用 RiskFilter 门控（高风险时强制平仓）
"""
from __future__ import annotations
from copy import copy
from typing import Any

from vnpy_ctastrategy import CtaTemplate
from vnpy.trader.object import BarData, TickData, TradeData, OrderData
from vnpy.trader.constant import Direction, Offset

from ..constant import (
    SignalSource, SignalDirection, PositionSizing, BridgeMode,
)
from ..model.signal_model import SignalRecord, BacktestConfig
from .signal_feed import SignalFeed


class BridgeCtaStrategy(CtaTemplate):
    """
    Backtesting Bridge — 通用信号驱动 CTA 策略。

    Class parameters (可被 BacktestConfig 覆盖):
      signal_threshold  float  最小信号强度，低于此不交易
      max_pos           float  最大多头/空头仓位（手数）
      sizing_method     str    仓位计算方法
      use_risk_filter   bool   是否使用风险门控
    """

    author = "BacktestBridge"

    # ── Class-level parameters (VeighNa convention) ───────────────────
    signal_threshold: float = 0.1
    max_pos:          float = 1.0
    sizing_method:    str   = PositionSizing.SIGNAL_SCALED.value
    use_risk_filter:  bool  = False

    parameters = ["signal_threshold", "max_pos", "sizing_method", "use_risk_filter"]
    variables  = ["pos", "last_signal", "last_strength", "bars_counted",
                  "signals_used", "signals_skipped"]

    def __init__(
        self,
        cta_engine:    Any,
        strategy_name: str,
        vt_symbol:     str,
        setting:       dict,
    ) -> None:
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # injected by BridgeEngine before each run
        self.signal_feed:   SignalFeed | None  = None
        self.risk_filter:   Any | None         = None   # callable(bar) → bool

        # runtime state
        self.last_signal:   float = 0.0
        self.last_strength: float = 0.0
        self.bars_counted:  int   = 0
        self.signals_used:  int   = 0
        self.signals_skipped: int = 0

    # ── lifecycle ─────────────────────────────────────────────────────
    def on_init(self) -> None:
        self.write_log(
            f"[BridgeStrategy] init: threshold={self.signal_threshold} "
            f"max_pos={self.max_pos} sizing={self.sizing_method}")
        self.load_bar(1)

    def on_start(self) -> None:
        if self.signal_feed:
            self.signal_feed.reset_cursors()
        self.write_log("[BridgeStrategy] started")

    def on_stop(self) -> None:
        self.write_log(
            f"[BridgeStrategy] stopped | "
            f"signals_used={self.signals_used} "
            f"signals_skipped={self.signals_skipped} "
            f"bars={self.bars_counted}")

    # ── bar callback ──────────────────────────────────────────────────
    def on_bar(self, bar: BarData) -> None:
        self.bars_counted += 1

        # 1. query signal
        if self.signal_feed is None:
            return
        rec = self.signal_feed.get_fused_signal(
            self.vt_symbol.split(".")[0], bar.datetime)
        if rec is None:
            self.signals_skipped += 1
            return

        # 2. risk filter gate
        if self.use_risk_filter and self.risk_filter:
            if not self.risk_filter(bar, rec):
                # risk gate open → flatten position
                self._flatten(bar)
                self.signals_skipped += 1
                return

        # 3. compute target position
        target = self._compute_target(rec)
        self.last_signal   = float(rec.direction.value)
        self.last_strength = rec.strength

        # 4. reconcile position
        diff = target - self.pos
        if abs(diff) < 1e-9:
            return

        self.signals_used += 1
        self.cancel_all()

        if diff > 0:
            price = bar.close_price * 1.001   # small premium for fill
            self.buy(price, abs(diff))
        elif diff < 0:
            price = bar.close_price * 0.999
            if self.pos > 0:
                close_vol = min(abs(diff), self.pos)
                self.sell(price, close_vol)
                if abs(diff) > close_vol:
                    self.short(price, abs(diff) - close_vol)
            else:
                self.short(price, abs(diff))

    def on_tick(self, tick: TickData) -> None:
        pass

    def on_trade(self, trade: TradeData) -> None:
        self.put_event()

    def on_order(self, order: OrderData) -> None:
        pass

    # ── helpers ───────────────────────────────────────────────────────
    def _compute_target(self, rec: SignalRecord) -> float:
        """根据 PositionSizing 方法计算目标仓位。"""
        strength = rec.strength
        direction_val = float(rec.direction.value)  # +1, 0, -1

        if rec.direction == SignalDirection.FLAT:
            return 0.0
        if abs(strength) < self.signal_threshold:
            return 0.0

        if self.sizing_method == PositionSizing.FIXED_UNIT.value:
            return self.max_pos * direction_val

        elif self.sizing_method == PositionSizing.SIGNAL_SCALED.value:
            scaled = abs(strength) * self.max_pos
            return round(scaled * direction_val, 4)

        elif self.sizing_method == PositionSizing.KELLY.value:
            # simplified Kelly: f = (p*b - q) / b
            # p = confidence, b = strength as reward ratio proxy
            p = rec.confidence
            b = max(abs(strength), 0.1)
            kelly_f = max(0.0, (p * b - (1 - p)) / b)
            kelly_f = min(kelly_f, 0.5)   # half-Kelly cap
            return round(kelly_f * self.max_pos * direction_val, 4)

        else:   # FIXED_NOTIONAL, RISK_PARITY → fall back to signal_scaled
            scaled = abs(strength) * self.max_pos
            return round(scaled * direction_val, 4)

    def _flatten(self, bar: BarData) -> None:
        """强制平仓。"""
        if self.pos > 0:
            self.sell(bar.close_price * 0.999, abs(self.pos))
        elif self.pos < 0:
            self.cover(bar.close_price * 1.001, abs(self.pos))
