"""
market_behavior/engine/pattern_engine.py
Phase 4: 单K形态识别引擎

识别形态：
  大阳线 / 大阴线
  高开低走 / 低开高走
  长上影线 / 长下影线
  十字星（含墓碑十字 / 蜻蜓十字）
  锤子线 / 射击之星
  连续N天大阳 / 连续N天大阴
  自定义阈值（全部参数 configure() 可调）
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..constant import PatternType
from ..model.candle import CandleBar
from ..model.pattern import PatternSignal


def _new_signal(
    symbol: str,
    pattern_type: PatternType,
    bar: CandleBar,
    **kwargs,
) -> PatternSignal:
    return PatternSignal(
        signal_id=uuid.uuid4().hex[:12],
        symbol=symbol,
        pattern_type=pattern_type,
        dt=bar.dt,
        body_ratio=bar.body_ratio,
        upper_shadow_ratio=bar.upper_shadow_ratio,
        lower_shadow_ratio=bar.lower_shadow_ratio,
        change_pct=bar.change_pct,
        **kwargs,
    )


class PatternEngine:
    """
    单K形态识别引擎 (Phase 4)。

    依赖：CandleEngine.buffer（由 set_candle_buffer() 注入）。
    每次调用 detect() 对最新 K线做形态扫描，返回 PatternSignal 列表。
    """

    DEFAULT_CFG: Dict[str, Any] = {
        # 大阳/大阴
        "big_yang_change_pct":  3.0,   # 涨幅阈值（%）
        "big_yin_change_pct":   3.0,   # 跌幅阈值（%）
        "big_yang_body_ratio":  0.60,  # 实体占振幅比下限
        "big_yin_body_ratio":   0.60,
        # 高开低走 / 低开高走
        "gap_open_ratio":       0.50,  # 开盘价 >= high/low 端 50% 位置
        "close_ratio":          0.50,  # 收盘价 <= low/high 端 50% 位置
        # 长上影 / 长下影
        "long_shadow_ratio":    0.55,  # 影线比下限
        "shadow_body_ratio":    0.35,  # 实体比上限（影线长时实体要短）
        # 十字星
        "doji_body_ratio":      0.05,  # 实体比上限
        # 墓碑十字（上影长，下影极短）
        "gravestone_upper":     0.65,
        "gravestone_lower":     0.10,
        # 蜻蜓十字（下影长，上影极短）
        "dragonfly_lower":      0.65,
        "dragonfly_upper":      0.10,
        # 锤子线（下影长，实体小，阳线）
        "hammer_lower":         0.55,
        "hammer_body":          0.35,
        # 射击之星（上影长，实体小，阴线）
        "shooting_upper":       0.55,
        "shooting_body":        0.35,
        # 连续大阳/大阴天数阈值
        "cont_big_yang_days":   2,
        "cont_big_yin_days":    2,
        # 最小振幅过滤（振幅太小的K线跳过，避免误判）
        "min_amplitude":        0.5,   # %
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
        self._log("[PatternEngine] init()")

    def start(self) -> None:
        self._running = True
        self._log("[PatternEngine] start()")

    def stop(self) -> None:
        self._running = False
        self._log("[PatternEngine] stop()")

    def summary(self) -> dict:
        return {
            "engine":   "PatternEngine",
            "status":   "running" if self._running else "stopped",
            "detected": self._detect_count,
        }

    # ══════════════════════════════════════════════════════════════════
    # 主检测入口
    # ══════════════════════════════════════════════════════════════════

    def detect(self, symbol: str, n_bars: int = 30) -> List[PatternSignal]:
        """对 symbol 最新 K线做全量形态扫描，返回触发的 PatternSignal 列表。"""
        if not self._candle_buf:
            return []
        bars = self._candle_buf.get(symbol, n_bars)
        if not bars:
            return []
        latest = bars[-1]
        signals: List[PatternSignal] = []

        # 最小振幅过滤
        if latest.amplitude < self._cfg["min_amplitude"]:
            return []

        signals += self._detect_big_yang(latest)
        signals += self._detect_big_yin(latest)
        signals += self._detect_high_open_low_close(latest)
        signals += self._detect_low_open_high_close(latest)
        signals += self._detect_long_upper_shadow(latest)
        signals += self._detect_long_lower_shadow(latest)
        signals += self._detect_doji(latest)
        signals += self._detect_gravestone_doji(latest)
        signals += self._detect_dragonfly_doji(latest)
        signals += self._detect_hammer(latest)
        signals += self._detect_shooting_star(latest)
        signals += self._detect_cont_big_yang(bars)
        signals += self._detect_cont_big_yin(bars)

        self._detect_count += len(signals)
        for sig in signals:
            self._emit_signal(sig)
        return signals

    def detect_bar(self, bar: CandleBar) -> List[PatternSignal]:
        """流式模式：每收到新K线后调用。"""
        if self._candle_buf:
            self._candle_buf.push(bar)
        return self.detect(bar.symbol)

    # ══════════════════════════════════════════════════════════════════
    # 1. 大阳线
    # ══════════════════════════════════════════════════════════════════

    def _detect_big_yang(self, bar: CandleBar) -> List[PatternSignal]:
        cfg = self._cfg
        if (bar.is_yang
                and bar.change_pct >= cfg["big_yang_change_pct"]
                and bar.body_ratio >= cfg["big_yang_body_ratio"]):
            return [_new_signal(bar.symbol, PatternType.BIG_YANG, bar)]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 2. 大阴线
    # ══════════════════════════════════════════════════════════════════

    def _detect_big_yin(self, bar: CandleBar) -> List[PatternSignal]:
        cfg = self._cfg
        if (bar.is_yin
                and bar.change_pct <= -cfg["big_yin_change_pct"]
                and bar.body_ratio >= cfg["big_yin_body_ratio"]):
            return [_new_signal(bar.symbol, PatternType.BIG_YIN, bar)]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 3. 高开低走（开盘靠近高点，收盘靠近低点）
    # ══════════════════════════════════════════════════════════════════

    def _detect_high_open_low_close(self, bar: CandleBar) -> List[PatternSignal]:
        """
        高开低走：
          开盘价位于振幅上方 gap_open_ratio 以上
          收盘价位于振幅下方 close_ratio 以下
          必须是阴线
        """
        rng = bar.high - bar.low
        if rng <= 0 or not bar.is_yin:
            return []
        cfg     = self._cfg
        ratio_o = (bar.open  - bar.low) / rng   # 开盘在振幅中的位置（越高越靠近上方）
        ratio_c = (bar.close - bar.low) / rng   # 收盘在振幅中的位置（越低越靠近下方）
        if (ratio_o >= cfg["gap_open_ratio"]
                and ratio_c <= (1 - cfg["close_ratio"])):
            return [_new_signal(bar.symbol, PatternType.HIGH_OPEN_LOW_CLOSE, bar,
                                extra={"open_pos": round(ratio_o, 4),
                                       "close_pos": round(ratio_c, 4)})]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 4. 低开高走（开盘靠近低点，收盘靠近高点）
    # ══════════════════════════════════════════════════════════════════

    def _detect_low_open_high_close(self, bar: CandleBar) -> List[PatternSignal]:
        """
        低开高走：
          开盘价位于振幅下方 gap_open_ratio 以下
          收盘价位于振幅上方 close_ratio 以上
          必须是阳线
        """
        rng = bar.high - bar.low
        if rng <= 0 or not bar.is_yang:
            return []
        cfg     = self._cfg
        ratio_o = (bar.open  - bar.low) / rng
        ratio_c = (bar.close - bar.low) / rng
        if (ratio_o <= (1 - cfg["gap_open_ratio"])
                and ratio_c >= cfg["close_ratio"]):
            return [_new_signal(bar.symbol, PatternType.LOW_OPEN_HIGH_CLOSE, bar,
                                extra={"open_pos": round(ratio_o, 4),
                                       "close_pos": round(ratio_c, 4)})]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 5. 长上影线
    # ══════════════════════════════════════════════════════════════════

    def _detect_long_upper_shadow(self, bar: CandleBar) -> List[PatternSignal]:
        """
        长上影线：
          upper_shadow_ratio >= long_shadow_ratio
          body_ratio         <= shadow_body_ratio
        """
        cfg = self._cfg
        if (bar.upper_shadow_ratio >= cfg["long_shadow_ratio"]
                and bar.body_ratio <= cfg["shadow_body_ratio"]):
            return [_new_signal(bar.symbol, PatternType.LONG_UPPER_SHADOW, bar)]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 6. 长下影线
    # ══════════════════════════════════════════════════════════════════

    def _detect_long_lower_shadow(self, bar: CandleBar) -> List[PatternSignal]:
        """
        长下影线：
          lower_shadow_ratio >= long_shadow_ratio
          body_ratio         <= shadow_body_ratio
        """
        cfg = self._cfg
        if (bar.lower_shadow_ratio >= cfg["long_shadow_ratio"]
                and bar.body_ratio <= cfg["shadow_body_ratio"]):
            return [_new_signal(bar.symbol, PatternType.LONG_LOWER_SHADOW, bar)]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 7. 标准十字星（body_ratio 极小）
    # ══════════════════════════════════════════════════════════════════

    def _detect_doji(self, bar: CandleBar) -> List[PatternSignal]:
        """
        十字星：body_ratio <= doji_body_ratio
        排除墓碑十字和蜻蜓十字（避免重复触发）。
        """
        cfg = self._cfg
        if bar.body_ratio > cfg["doji_body_ratio"]:
            return []
        # 若同时满足墓碑/蜻蜓条件则不在此处触发
        is_gravestone = (
            bar.upper_shadow_ratio >= cfg["gravestone_upper"]
            and bar.lower_shadow_ratio <= cfg["gravestone_lower"]
        )
        is_dragonfly = (
            bar.lower_shadow_ratio >= cfg["dragonfly_lower"]
            and bar.upper_shadow_ratio <= cfg["dragonfly_upper"]
        )
        if is_gravestone or is_dragonfly:
            return []
        return [_new_signal(bar.symbol, PatternType.DOJI, bar)]

    # ══════════════════════════════════════════════════════════════════
    # 8. 墓碑十字（上影极长，下影极短）
    # ══════════════════════════════════════════════════════════════════

    def _detect_gravestone_doji(self, bar: CandleBar) -> List[PatternSignal]:
        cfg = self._cfg
        if (bar.body_ratio <= cfg["doji_body_ratio"]
                and bar.upper_shadow_ratio >= cfg["gravestone_upper"]
                and bar.lower_shadow_ratio <= cfg["gravestone_lower"]):
            return [_new_signal(bar.symbol, PatternType.GRAVESTONE_DOJI, bar)]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 9. 蜻蜓十字（下影极长，上影极短）
    # ══════════════════════════════════════════════════════════════════

    def _detect_dragonfly_doji(self, bar: CandleBar) -> List[PatternSignal]:
        cfg = self._cfg
        if (bar.body_ratio <= cfg["doji_body_ratio"]
                and bar.lower_shadow_ratio >= cfg["dragonfly_lower"]
                and bar.upper_shadow_ratio <= cfg["dragonfly_upper"]):
            return [_new_signal(bar.symbol, PatternType.DRAGONFLY_DOJI, bar)]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 10. 锤子线（下影长，实体小，阳线）
    # ══════════════════════════════════════════════════════════════════

    def _detect_hammer(self, bar: CandleBar) -> List[PatternSignal]:
        """
        锤子线（看涨）：
          is_yang
          lower_shadow_ratio >= hammer_lower
          body_ratio         <= hammer_body
          上影线很短（< lower_shadow_ratio / 2）
        """
        cfg = self._cfg
        if (bar.is_yang
                and bar.lower_shadow_ratio >= cfg["hammer_lower"]
                and bar.body_ratio <= cfg["hammer_body"]
                and bar.upper_shadow_ratio < bar.lower_shadow_ratio / 2):
            return [_new_signal(bar.symbol, PatternType.HAMMER, bar)]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 11. 射击之星（上影长，实体小，阴线）
    # ══════════════════════════════════════════════════════════════════

    def _detect_shooting_star(self, bar: CandleBar) -> List[PatternSignal]:
        """
        射击之星（看跌）：
          is_yin
          upper_shadow_ratio >= shooting_upper
          body_ratio         <= shooting_body
          下影线很短（< upper_shadow_ratio / 2）
        """
        cfg = self._cfg
        if (bar.is_yin
                and bar.upper_shadow_ratio >= cfg["shooting_upper"]
                and bar.body_ratio <= cfg["shooting_body"]
                and bar.lower_shadow_ratio < bar.upper_shadow_ratio / 2):
            return [_new_signal(bar.symbol, PatternType.SHOOTING_STAR, bar)]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 12. 连续N天大阳线
    # ══════════════════════════════════════════════════════════════════

    def _detect_cont_big_yang(self, bars: List[CandleBar]) -> List[PatternSignal]:
        cfg      = self._cfg
        min_days = cfg["cont_big_yang_days"]
        if len(bars) < min_days:
            return []

        latest   = bars[-1]
        window   = bars[-min_days:]
        all_yang = all(
            b.is_yang
            and b.change_pct >= cfg["big_yang_change_pct"]
            and b.body_ratio >= cfg["big_yang_body_ratio"]
            and b.amplitude  >= cfg["min_amplitude"]
            for b in window
        )
        if all_yang:
            return [_new_signal(
                latest.symbol, PatternType.CONT_BIG_YANG, latest,
                consecutive_days=min_days,
            )]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 13. 连续N天大阴线
    # ══════════════════════════════════════════════════════════════════

    def _detect_cont_big_yin(self, bars: List[CandleBar]) -> List[PatternSignal]:
        cfg      = self._cfg
        min_days = cfg["cont_big_yin_days"]
        if len(bars) < min_days:
            return []

        latest  = bars[-1]
        window  = bars[-min_days:]
        all_yin = all(
            b.is_yin
            and b.change_pct <= -cfg["big_yin_change_pct"]
            and b.body_ratio >= cfg["big_yin_body_ratio"]
            and b.amplitude  >= cfg["min_amplitude"]
            for b in window
        )
        if all_yin:
            return [_new_signal(
                latest.symbol, PatternType.CONT_BIG_YIN, latest,
                consecutive_days=min_days,
            )]
        return []

    # ── 事件发布 ──────────────────────────────────────────────────────

    def _emit(self, event_type: str, data: dict) -> None:
        if self._dispatch:
            try:
                self._dispatch(event_type, data)
            except Exception:
                pass

    def _emit_signal(self, sig: PatternSignal) -> None:
        from ..event import EVENT_MB_PATTERN_FOUND
        self._emit(EVENT_MB_PATTERN_FOUND, sig.to_dict())
