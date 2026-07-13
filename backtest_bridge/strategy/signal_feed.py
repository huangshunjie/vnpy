"""
backtest_bridge/strategy/signal_feed.py

SignalFeed — 信号注入器。

在回测时充当各模块信号的"时间轴对齐缓冲区"：
  - 接收来自各模块的 SignalRecord（带时间戳）
  - 按 bar 时间戳查询当前应使用的信号
  - 支持多信号源融合
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime
from typing import Callable

from ..constant import SignalSource, SignalDirection
from ..model.signal_model import SignalRecord


class SignalFeed:
    """
    信号注入器 — 时间轴对齐信号缓冲区。

    使用方式：
      1. 回测开始前：调用 load_signals(records) 加载全部历史信号
      2. 回测中每根 bar：调用 get_signal(symbol, bar_dt) 获取当前信号
      3. 支持多 source 权重融合
    """

    def __init__(
        self,
        default_source: SignalSource = SignalSource.ALPHA_FACTORY,
        log_fn: Callable | None      = None,
    ) -> None:
        self._default_source = default_source
        self._log            = log_fn or (lambda m: None)

        # {symbol: [(timestamp, SignalRecord), ...]}  已按时间排序
        self._signals: dict[str, list[tuple[datetime, SignalRecord]]] = defaultdict(list)
        # 每个 symbol 的当前指针（二分查找加速）
        self._cursor: dict[str, int] = defaultdict(int)
        # source 权重（用于多信号融合）
        self._weights: dict[SignalSource, float] = {}

    # ── signal loading ────────────────────────────────────────────────
    def load_signals(self, records: list[SignalRecord]) -> int:
        """批量加载信号（必须在回测开始前调用）。"""
        count = 0
        for rec in records:
            self._signals[rec.symbol].append((rec.timestamp, rec))
            count += 1
        # sort by timestamp
        for sym in self._signals:
            self._signals[sym].sort(key=lambda x: x[0])
        self._cursor = defaultdict(int)
        self._log(f"[SignalFeed] loaded {count} signals for "
                  f"{len(self._signals)} symbols")
        return count

    def add_signal(self, rec: SignalRecord) -> None:
        """逐条追加信号（用于实时模拟）。"""
        self._signals[rec.symbol].append((rec.timestamp, rec))
        self._signals[rec.symbol].sort(key=lambda x: x[0])
        self._cursor[rec.symbol] = 0

    def clear(self) -> None:
        self._signals.clear()
        self._cursor.clear()

    def set_source_weights(self, weights: dict[SignalSource, float]) -> None:
        """设置多信号源权重（用于融合模式）。"""
        total = sum(weights.values())
        if total > 0:
            self._weights = {k: v / total for k, v in weights.items()}
        else:
            self._weights = {}

    # ── signal query ──────────────────────────────────────────────────
    def get_signal(
        self,
        symbol:     str,
        bar_dt:     datetime,
        source:     SignalSource | None = None,
    ) -> SignalRecord | None:
        """
        获取截止 bar_dt 最新的信号（最近一条 timestamp <= bar_dt 的记录）。
        若无信号则返回 None。
        """
        src = source or self._default_source
        buf = self._signals.get(symbol, [])
        if not buf:
            return None

        # 线性扫描（cursor加速：只向前不回退）
        cur = self._cursor[symbol]
        while cur + 1 < len(buf) and buf[cur + 1][0] <= bar_dt:
            cur += 1
        self._cursor[symbol] = cur

        ts, rec = buf[cur]
        if ts > bar_dt:
            return None
        return rec

    def get_fused_signal(
        self,
        symbol:  str,
        bar_dt:  datetime,
    ) -> SignalRecord | None:
        """
        融合多信号源：按权重加权 strength，返回合成 SignalRecord。
        若未设置权重则退回 get_signal()。
        """
        if not self._weights:
            return self.get_signal(symbol, bar_dt)

        total_w   = 0.0
        fused_str = 0.0
        fused_conf= 0.0
        n_found   = 0

        for src, w in self._weights.items():
            rec = self.get_signal(symbol, bar_dt, source=src)
            if rec is None:
                continue
            fused_str  += rec.strength   * w
            fused_conf += rec.confidence * w
            total_w    += w
            n_found    += 1

        if n_found == 0:
            return None

        # normalise
        if total_w > 0:
            fused_str  /= total_w
            fused_conf /= total_w

        direction = (SignalDirection.LONG  if fused_str > 0.05
                     else SignalDirection.SHORT if fused_str < -0.05
                     else SignalDirection.FLAT)

        return SignalRecord(
            signal_id  = f"FUSED_{symbol}_{str(bar_dt)[:10]}",
            source     = SignalSource.COMBINED,
            symbol     = symbol,
            direction  = direction,
            strength   = round(fused_str,  4),
            confidence = round(fused_conf, 4),
            timestamp  = bar_dt,
        )

    def reset_cursors(self) -> None:
        """重置游标（每次回测开始前调用）。"""
        self._cursor = defaultdict(int)

    # ── info ──────────────────────────────────────────────────────────
    def signal_count(self, symbol: str | None = None) -> int:
        if symbol:
            return len(self._signals.get(symbol, []))
        return sum(len(v) for v in self._signals.values())

    def symbols(self) -> list[str]:
        return list(self._signals.keys())

    def summary(self) -> dict:
        return {
            "symbols":       len(self._signals),
            "total_signals": self.signal_count(),
            "sources":       list({r.source.value
                                   for v in self._signals.values()
                                   for _, r in v}),
        }
