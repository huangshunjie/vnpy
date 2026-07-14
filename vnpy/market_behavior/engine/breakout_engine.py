"""
market_behavior/engine/breakout_engine.py
Phase 5: 突破检测引擎

检测类型：
  N日新高 / N日新低
  量能突破（成交量超过均量 × ratio）
  波动突破（振幅超过 ATR × ratio）
  均线金叉 / 均线死叉（MA cross）
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..constant import BreakoutType
from ..model.candle import CandleBar
from ..model.pattern import BreakoutSignal


def _new_signal(
    symbol: str,
    bk_type: BreakoutType,
    bar: CandleBar,
    **kwargs,
) -> BreakoutSignal:
    return BreakoutSignal(
        signal_id=uuid.uuid4().hex[:12],
        symbol=symbol,
        breakout_type=bk_type,
        dt=bar.dt,
        **kwargs,
    )


def _sma(values: List[float], n: int) -> Optional[float]:
    """简单移动均线，数据不足返回 None。"""
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def _atr(bars: List[CandleBar], n: int) -> Optional[float]:
    """
    Average True Range (ATR)。
    TR = max(high-low, |high-prev_close|, |low-prev_close|)
    """
    if len(bars) < n + 1:
        return None
    tr_list = []
    for i in range(len(bars) - n, len(bars)):
        b    = bars[i]
        prev = bars[i - 1]
        tr   = max(b.high - b.low,
                   abs(b.high - prev.close),
                   abs(b.low  - prev.close))
        tr_list.append(tr)
    return sum(tr_list) / n


class BreakoutEngine:
    """
    突破检测引擎 (Phase 5)。

    依赖：CandleEngine.buffer（由 set_candle_buffer() 注入）。
    """

    DEFAULT_CFG: Dict[str, Any] = {
        # N日新高/低
        "new_high_window":    20,     # 近 N 日新高
        "new_low_window":     20,     # 近 N 日新低
        # 量能突破
        "vol_ma_window":      20,     # 量能均线窗口
        "vol_breakout_ratio": 2.0,    # 成交量 >= 均量 × ratio
        "vol_price_confirm":  True,   # 是否要求价格同向（阳线放量才算突破）
        # 波动突破
        "atr_window":         14,     # ATR 窗口
        "atr_breakout_ratio": 2.0,    # 振幅 >= ATR × ratio
        # 均线穿越
        "ma_fast":            5,      # 快线窗口
        "ma_slow":            20,     # 慢线窗口
    }

    def __init__(
        self,
        log_fn: Optional[Callable[[str], None]] = None,
        main_engine: Any = None,
        dispatch_fn: Optional[Callable[[str, dict], None]] = None,
    ) -> None:
        self._log         = log_fn or print
        self._main_engine = main_engine
        self._dispatch    = dispatch_fn
        self._running     = False
        self._cfg         = dict(self.DEFAULT_CFG)
        self._candle_buf  = None
        self._detect_count = 0

    def set_main_engine(self, engine: Any) -> None:
        self._main_engine = engine

    def set_dispatch(self, fn: Callable[[str, dict], None]) -> None:
        self._dispatch = fn

    def set_candle_buffer(self, buf: Any) -> None:
        self._candle_buf = buf

    def configure(self, **kwargs) -> None:
        self._cfg.update(kwargs)

    def init(self) -> None:
        self._log("[BreakoutEngine] init()")

    def start(self) -> None:
        self._running = True
        self._log("[BreakoutEngine] start()")

    def stop(self) -> None:
        self._running = False
        self._log("[BreakoutEngine] stop()")

    def summary(self) -> dict:
        return {
            "engine":   "BreakoutEngine",
            "status":   "running" if self._running else "stopped",
            "detected": self._detect_count,
        }

    # ══════════════════════════════════════════════════════════════════
    # 主检测入口
    # ══════════════════════════════════════════════════════════════════

    def detect(self, symbol: str, n_bars: int = 60) -> List[BreakoutSignal]:
        """对 symbol 最新K线做全量突破扫描。"""
        if not self._candle_buf:
            return []
        bars = self._candle_buf.get(symbol, n_bars)
        if not bars:
            return []

        signals: List[BreakoutSignal] = []
        signals += self._detect_new_high(bars)
        signals += self._detect_new_low(bars)
        signals += self._detect_volume_breakout(bars)
        signals += self._detect_volatility_breakout(bars)
        signals += self._detect_ma_cross_up(bars)
        signals += self._detect_ma_cross_down(bars)

        self._detect_count += len(signals)
        for sig in signals:
            self._emit_signal(sig)
        return signals

    def detect_bar(self, bar: CandleBar) -> List[BreakoutSignal]:
        if self._candle_buf:
            self._candle_buf.push(bar)
        return self.detect(bar.symbol)

    # ══════════════════════════════════════════════════════════════════
    # 1. N日新高
    # ══════════════════════════════════════════════════════════════════

    def _detect_new_high(self, bars: List[CandleBar]) -> List[BreakoutSignal]:
        """
        N日新高：今收 > 近 N 日（不含今日）最高收盘。
        """
        n = self._cfg["new_high_window"]
        if len(bars) < n + 1:
            return []
        latest    = bars[-1]
        ref_bars  = bars[-(n + 1):-1]          # 不含今日的前 N 根
        ref_high  = max(b.close for b in ref_bars)
        if latest.close > ref_high:
            return [_new_signal(
                latest.symbol, BreakoutType.NEW_HIGH_N, latest,
                window=n,
                ref_value=round(ref_high, 4),
                current_value=latest.close,
            )]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 2. N日新低
    # ══════════════════════════════════════════════════════════════════

    def _detect_new_low(self, bars: List[CandleBar]) -> List[BreakoutSignal]:
        """N日新低：今收 < 近 N 日（不含今日）最低收盘。"""
        n = self._cfg["new_low_window"]
        if len(bars) < n + 1:
            return []
        latest   = bars[-1]
        ref_bars = bars[-(n + 1):-1]
        ref_low  = min(b.close for b in ref_bars)
        if latest.close < ref_low:
            return [_new_signal(
                latest.symbol, BreakoutType.NEW_LOW_N, latest,
                window=n,
                ref_value=round(ref_low, 4),
                current_value=latest.close,
            )]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 3. 量能突破
    # ══════════════════════════════════════════════════════════════════

    def _detect_volume_breakout(self, bars: List[CandleBar]) -> List[BreakoutSignal]:
        """
        量能突破：
          今日成交量 >= 近 N 日均量 × vol_breakout_ratio
          若 vol_price_confirm=True，则还要求今日是阳线（价量配合）
        """
        n     = self._cfg["vol_ma_window"]
        ratio = self._cfg["vol_breakout_ratio"]
        if len(bars) < n + 1:
            return []

        latest  = bars[-1]
        ref_vols = [b.volume for b in bars[-(n + 1):-1]]
        vol_ma   = sum(ref_vols) / n if ref_vols else 0.0

        if vol_ma <= 0:
            return []

        vol_ratio = latest.volume / vol_ma
        if vol_ratio < ratio:
            return []

        if self._cfg["vol_price_confirm"] and not latest.is_yang:
            return []

        return [_new_signal(
            latest.symbol, BreakoutType.VOLUME_BREAKOUT, latest,
            window=n,
            ref_value=round(vol_ma, 2),
            current_value=round(latest.volume, 2),
            vol_ratio=round(vol_ratio, 4),
        )]

    # ══════════════════════════════════════════════════════════════════
    # 4. 波动突破（振幅超过 ATR × ratio）
    # ══════════════════════════════════════════════════════════════════

    def _detect_volatility_breakout(self, bars: List[CandleBar]) -> List[BreakoutSignal]:
        """
        波动突破：今日 TR > ATR(n) × atr_breakout_ratio
        TR = high - low（简化，前收在 CandleBar 中已有）
        """
        n     = self._cfg["atr_window"]
        ratio = self._cfg["atr_breakout_ratio"]
        if len(bars) < n + 1:
            return []

        latest = bars[-1]
        atr    = _atr(bars, n)
        if atr is None or atr <= 0:
            return []

        tr = max(
            latest.high - latest.low,
            abs(latest.high - latest.prev_close),
            abs(latest.low  - latest.prev_close),
        )
        if tr > atr * ratio:
            return [_new_signal(
                latest.symbol, BreakoutType.VOLATILITY_BREAK, latest,
                window=n,
                ref_value=round(atr, 4),
                current_value=round(tr, 4),
                vol_ratio=round(tr / atr, 4),
            )]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 5. 均线金叉（快线向上穿越慢线）
    # ══════════════════════════════════════════════════════════════════

    def _detect_ma_cross_up(self, bars: List[CandleBar]) -> List[BreakoutSignal]:
        """
        金叉：前一根 ma_fast <= ma_slow，今天 ma_fast > ma_slow。
        """
        fast = self._cfg["ma_fast"]
        slow = self._cfg["ma_slow"]
        need = slow + 1          # 至少需要 slow+1 根才能比较前后两根均线
        if len(bars) < need:
            return []

        closes = [b.close for b in bars]
        latest = bars[-1]

        ma_fast_now  = _sma(closes, fast)
        ma_slow_now  = _sma(closes, slow)
        ma_fast_prev = _sma(closes[:-1], fast)
        ma_slow_prev = _sma(closes[:-1], slow)

        if None in (ma_fast_now, ma_slow_now, ma_fast_prev, ma_slow_prev):
            return []

        if ma_fast_prev <= ma_slow_prev and ma_fast_now > ma_slow_now:
            return [_new_signal(
                latest.symbol, BreakoutType.MA_CROSS_UP, latest,
                window=slow,
                ref_value=round(ma_slow_now, 4),
                current_value=round(ma_fast_now, 4),
            )]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 6. 均线死叉（快线向下穿越慢线）
    # ══════════════════════════════════════════════════════════════════

    def _detect_ma_cross_down(self, bars: List[CandleBar]) -> List[BreakoutSignal]:
        """死叉：前一根 ma_fast >= ma_slow，今天 ma_fast < ma_slow。"""
        fast = self._cfg["ma_fast"]
        slow = self._cfg["ma_slow"]
        need = slow + 1
        if len(bars) < need:
            return []

        closes = [b.close for b in bars]
        latest = bars[-1]

        ma_fast_now  = _sma(closes, fast)
        ma_slow_now  = _sma(closes, slow)
        ma_fast_prev = _sma(closes[:-1], fast)
        ma_slow_prev = _sma(closes[:-1], slow)

        if None in (ma_fast_now, ma_slow_now, ma_fast_prev, ma_slow_prev):
            return []

        if ma_fast_prev >= ma_slow_prev and ma_fast_now < ma_slow_now:
            return [_new_signal(
                latest.symbol, BreakoutType.MA_CROSS_DOWN, latest,
                window=slow,
                ref_value=round(ma_slow_now, 4),
                current_value=round(ma_fast_now, 4),
            )]
        return []

    # ── 事件发布 ──────────────────────────────────────────────────────

    def _emit(self, event_type: str, data: dict) -> None:
        if self._dispatch:
            try:
                self._dispatch(event_type, data)
            except Exception:
                pass

    def _emit_signal(self, sig: BreakoutSignal) -> None:
        from ..event import EVENT_MB_BREAKOUT_FOUND
        self._emit(EVENT_MB_BREAKOUT_FOUND, sig.to_dict())
