"""
market_behavior/engine/sequence_engine.py
Phase 5: K线组合模式识别引擎

识别模式：
  早晨之星 / 黄昏之星
  三白兵   / 三黑鸦
  看涨吞没 / 看跌吞没
  两阳夹一阴 / 两阴夹一阳
  Pattern DSL（自定义序列）
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..constant import SequenceType
from ..model.candle import CandleBar
from ..model.pattern import SequenceSignal


def _new_signal(
    symbol: str,
    seq_type: SequenceType,
    latest: CandleBar,
    bars: int = 3,
    dsl: str = "",
    **kwargs,
) -> SequenceSignal:
    return SequenceSignal(
        signal_id=uuid.uuid4().hex[:12],
        symbol=symbol,
        sequence_type=seq_type,
        dt=latest.dt,
        bars=bars,
        dsl_pattern=dsl,
        **kwargs,
    )


class SequenceEngine:
    """
    K线组合模式识别引擎 (Phase 5)。

    依赖：CandleEngine.buffer（由 set_candle_buffer() 注入）。
    每次调用 detect() 对最新 N 根K线做组合模式扫描。
    """

    DEFAULT_CFG: Dict[str, Any] = {
        # 大阳/大阴 判断基准（与 PatternEngine 一致）
        "big_yang_change":    3.0,    # 大阳涨幅阈值（%）
        "big_yin_change":     3.0,    # 大阴跌幅阈值（%）
        "big_body_ratio":     0.55,   # 大阳/大阴 实体比下限
        # 小实体（用于星形中间K线）
        "small_body_ratio":   0.35,
        # 早晨/黄昏之星：第3根需收盘超过第1根实体中点多少
        "star_penetration":   0.50,   # 穿透比例
        # 三白兵/三黑鸦：每根开盘在前根实体内的比例
        "soldier_open_pct":   0.90,   # 开盘 <= 前根实体顶部×90%
        # 吞没：吞没实体需超过被吞实体多少
        "engulf_ratio":       1.0,    # 完全覆盖即可（=1.0）
        # 最小振幅过滤
        "min_amplitude":      0.3,    # %
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
        # DSL 规则库 {name: [token, ...]}
        self._dsl_rules: Dict[str, List[str]] = {}

    def set_main_engine(self, engine: Any) -> None:
        self._main_engine = engine

    def set_dispatch(self, fn: Callable[[str, dict], None]) -> None:
        self._dispatch = fn

    def set_candle_buffer(self, buf: Any) -> None:
        self._candle_buf = buf

    def configure(self, **kwargs) -> None:
        self._cfg.update(kwargs)

    def add_dsl_rule(self, name: str, pattern: str) -> None:
        """
        注册自定义 DSL 规则。
        pattern 格式：空格分隔的 token 序列。
        每个 token 可以是:
          YANG / YIN                  方向
          BIG_YANG / BIG_YIN          大阳/大阴
          SMALL / DOJI                小实体/十字星
          UP / DOWN                   收盘较前根涨/跌
          LIMIT_UP / LIMIT_DOWN       涨停/跌停
          ANY                         任意
        示例: "BIG_YANG ANY BIG_YANG"
        """
        tokens = [t.strip().upper() for t in pattern.split() if t.strip()]
        self._dsl_rules[name] = tokens

    def init(self) -> None:
        self._log("[SequenceEngine] init()")

    def start(self) -> None:
        self._running = True
        self._log("[SequenceEngine] start()")

    def stop(self) -> None:
        self._running = False
        self._log("[SequenceEngine] stop()")

    def summary(self) -> dict:
        return {
            "engine":     "SequenceEngine",
            "status":     "running" if self._running else "stopped",
            "detected":   self._detect_count,
            "dsl_rules":  len(self._dsl_rules),
        }

    # ══════════════════════════════════════════════════════════════════
    # 主检测入口
    # ══════════════════════════════════════════════════════════════════

    def detect(self, symbol: str, n_bars: int = 30) -> List[SequenceSignal]:
        """对 symbol 最近 n_bars 根K线做全量组合模式扫描。"""
        if not self._candle_buf:
            return []
        bars = self._candle_buf.get(symbol, n_bars)
        if len(bars) < 2:
            return []

        signals: List[SequenceSignal] = []
        signals += self._detect_morning_star(bars)
        signals += self._detect_evening_star(bars)
        signals += self._detect_three_white(bars)
        signals += self._detect_three_black(bars)
        signals += self._detect_bullish_engulf(bars)
        signals += self._detect_bearish_engulf(bars)
        signals += self._detect_yang_yin_yang(bars)
        signals += self._detect_yin_yang_yin(bars)
        signals += self._detect_dsl(bars)

        self._detect_count += len(signals)
        for sig in signals:
            self._emit_signal(sig)
        return signals

    def detect_bar(self, bar: CandleBar) -> List[SequenceSignal]:
        if self._candle_buf:
            self._candle_buf.push(bar)
        return self.detect(bar.symbol)

    # ══════════════════════════════════════════════════════════════════
    # 辅助方法：K线属性判断
    # ══════════════════════════════════════════════════════════════════

    def _is_big_yang(self, b: CandleBar) -> bool:
        cfg = self._cfg
        return (b.is_yang
                and b.change_pct >= cfg["big_yang_change"]
                and b.body_ratio >= cfg["big_body_ratio"])

    def _is_big_yin(self, b: CandleBar) -> bool:
        cfg = self._cfg
        return (b.is_yin
                and b.change_pct <= -cfg["big_yin_change"]
                and b.body_ratio >= cfg["big_body_ratio"])

    def _is_small_body(self, b: CandleBar) -> bool:
        return b.body_ratio <= self._cfg["small_body_ratio"]

    def _body_top(self, b: CandleBar) -> float:
        return max(b.open, b.close)

    def _body_bot(self, b: CandleBar) -> float:
        return min(b.open, b.close)

    def _body_mid(self, b: CandleBar) -> float:
        return (self._body_top(b) + self._body_bot(b)) / 2

    # ══════════════════════════════════════════════════════════════════
    # 1. 早晨之星（看涨反转，3根）
    # ══════════════════════════════════════════════════════════════════

    def _detect_morning_star(self, bars: List[CandleBar]) -> List[SequenceSignal]:
        """
        早晨之星：
          b1: 大阴线
          b2: 小实体（开盘/收盘均低于 b1 实体底部，跳空低开）
          b3: 大阳线，收盘高于 b1 实体中点（穿透 >= star_penetration）
        """
        if len(bars) < 3:
            return []
        signals = []
        b1, b2, b3 = bars[-3], bars[-2], bars[-1]
        pen = self._cfg["star_penetration"]

        if (self._is_big_yin(b1)
                and self._is_small_body(b2)
                and self._body_top(b2) < self._body_bot(b1)   # 跳空低开
                and self._is_big_yang(b3)
                and b3.close >= self._body_bot(b1) + (self._body_top(b1) - self._body_bot(b1)) * pen):
            signals.append(_new_signal(
                b3.symbol, SequenceType.MORNING_STAR, b3, bars=3,
                confidence=round(
                    (b3.close - self._body_mid(b1)) / (self._body_top(b1) - self._body_bot(b1) + 1e-9), 4
                ),
            ))
        return signals

    # ══════════════════════════════════════════════════════════════════
    # 2. 黄昏之星（看跌反转，3根）
    # ══════════════════════════════════════════════════════════════════

    def _detect_evening_star(self, bars: List[CandleBar]) -> List[SequenceSignal]:
        """
        黄昏之星：
          b1: 大阳线
          b2: 小实体（跳空高开，开盘/收盘均高于 b1 实体顶部）
          b3: 大阴线，收盘低于 b1 实体中点（穿透 >= star_penetration）
        """
        if len(bars) < 3:
            return []
        signals = []
        b1, b2, b3 = bars[-3], bars[-2], bars[-1]
        pen = self._cfg["star_penetration"]

        if (self._is_big_yang(b1)
                and self._is_small_body(b2)
                and self._body_bot(b2) > self._body_top(b1)   # 跳空高开
                and self._is_big_yin(b3)
                and b3.close <= self._body_top(b1) - (self._body_top(b1) - self._body_bot(b1)) * pen):
            signals.append(_new_signal(
                b3.symbol, SequenceType.EVENING_STAR, b3, bars=3,
                confidence=round(
                    (self._body_mid(b1) - b3.close) / (self._body_top(b1) - self._body_bot(b1) + 1e-9), 4
                ),
            ))
        return signals

    # ══════════════════════════════════════════════════════════════════
    # 3. 三白兵（连续3根大阳，逐步走高）
    # ══════════════════════════════════════════════════════════════════

    def _detect_three_white(self, bars: List[CandleBar]) -> List[SequenceSignal]:
        """
        三白兵：
          连续3根大阳线
          每根开盘在前根实体内（不超过前根实体顶部×soldier_open_pct）
          每根收盘高于前根收盘（逐步走高）
        """
        if len(bars) < 3:
            return []
        signals = []
        b1, b2, b3 = bars[-3], bars[-2], bars[-1]
        s = self._cfg["soldier_open_pct"]

        if (self._is_big_yang(b1) and self._is_big_yang(b2) and self._is_big_yang(b3)
                and self._body_bot(b1) <= b2.open <= self._body_top(b1)
                and self._body_bot(b2) <= b3.open <= self._body_top(b2)
                and b2.close > b1.close
                and b3.close > b2.close):
            signals.append(_new_signal(b3.symbol, SequenceType.THREE_WHITE, b3, bars=3))
        return signals

    # ══════════════════════════════════════════════════════════════════
    # 4. 三黑鸦（连续3根大阴，逐步走低）
    # ══════════════════════════════════════════════════════════════════

    def _detect_three_black(self, bars: List[CandleBar]) -> List[SequenceSignal]:
        """
        三黑鸦：
          连续3根大阴线
          每根开盘在前根实体内
          每根收盘低于前根收盘（逐步走低）
        """
        if len(bars) < 3:
            return []
        signals = []
        b1, b2, b3 = bars[-3], bars[-2], bars[-1]
        s = self._cfg["soldier_open_pct"]

        if (self._is_big_yin(b1) and self._is_big_yin(b2) and self._is_big_yin(b3)
                and self._body_bot(b1) <= b2.open <= self._body_top(b1)
                and self._body_bot(b2) <= b3.open <= self._body_top(b2)
                and b2.close < b1.close
                and b3.close < b2.close):
            signals.append(_new_signal(b3.symbol, SequenceType.THREE_BLACK, b3, bars=3))
        return signals

    # ══════════════════════════════════════════════════════════════════
    # 5. 看涨吞没
    # ══════════════════════════════════════════════════════════════════

    def _detect_bullish_engulf(self, bars: List[CandleBar]) -> List[SequenceSignal]:
        """
        看涨吞没：
          b1: 阴线
          b2: 阳线，实体完全包住 b1 实体（open <= b1.close, close >= b1.open）
        """
        if len(bars) < 2:
            return []
        b1, b2 = bars[-2], bars[-1]
        if (b1.is_yin and b2.is_yang
                and b2.open  <= self._body_bot(b1)
                and b2.close >= self._body_top(b1)):
            return [_new_signal(b2.symbol, SequenceType.BULLISH_ENGULF, b2, bars=2)]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 6. 看跌吞没
    # ══════════════════════════════════════════════════════════════════

    def _detect_bearish_engulf(self, bars: List[CandleBar]) -> List[SequenceSignal]:
        """
        看跌吞没：
          b1: 阳线
          b2: 阴线，实体完全包住 b1 实体（open >= b1.close, close <= b1.open）
        """
        if len(bars) < 2:
            return []
        b1, b2 = bars[-2], bars[-1]
        if (b1.is_yang and b2.is_yin
                and b2.open  >= self._body_top(b1)
                and b2.close <= self._body_bot(b1)):
            return [_new_signal(b2.symbol, SequenceType.BEARISH_ENGULF, b2, bars=2)]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 7. 两阳夹一阴（看涨）
    # ══════════════════════════════════════════════════════════════════

    def _detect_yang_yin_yang(self, bars: List[CandleBar]) -> List[SequenceSignal]:
        """
        两阳夹一阴：
          b1: 阳线
          b2: 阴线，且实体在 b1 实体范围内
          b3: 阳线，收盘高于 b1 收盘
        """
        if len(bars) < 3:
            return []
        b1, b2, b3 = bars[-3], bars[-2], bars[-1]
        if (b1.is_yang and b2.is_yin and b3.is_yang
                and self._body_bot(b2) >= self._body_bot(b1)
                and self._body_top(b2) <= self._body_top(b1)
                and b3.close >= b1.close):
            return [_new_signal(b3.symbol, SequenceType.YANG_YIN_YANG, b3, bars=3)]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 8. 两阴夹一阳（看跌）
    # ══════════════════════════════════════════════════════════════════

    def _detect_yin_yang_yin(self, bars: List[CandleBar]) -> List[SequenceSignal]:
        """
        两阴夹一阳：
          b1: 阴线
          b2: 阳线，且实体在 b1 实体范围内
          b3: 阴线，收盘低于 b1 收盘
        """
        if len(bars) < 3:
            return []
        b1, b2, b3 = bars[-3], bars[-2], bars[-1]
        if (b1.is_yin and b2.is_yang and b3.is_yin
                and self._body_bot(b2) >= self._body_bot(b1)
                and self._body_top(b2) <= self._body_top(b1)
                and b3.close <= b1.close):
            return [_new_signal(b3.symbol, SequenceType.YIN_YANG_YIN, b3, bars=3)]
        return []

    # ══════════════════════════════════════════════════════════════════
    # 9. Pattern DSL（自定义序列）
    # ══════════════════════════════════════════════════════════════════

    def _detect_dsl(self, bars: List[CandleBar]) -> List[SequenceSignal]:
        """遍历所有已注册的 DSL 规则，返回匹配的信号。"""
        if not self._dsl_rules:
            return []
        signals = []
        for name, tokens in self._dsl_rules.items():
            n = len(tokens)
            if len(bars) < n:
                continue
            window = bars[-n:]
            if self._match_dsl(window, tokens):
                signals.append(_new_signal(
                    window[-1].symbol, SequenceType.CUSTOM,
                    window[-1], bars=n, dsl=" ".join(tokens),
                    extra={"rule_name": name},
                ))
        return signals

    def _match_dsl(self, bars: List[CandleBar], tokens: List[str]) -> bool:
        """逐根匹配 DSL token。"""
        for bar, token in zip(bars, tokens):
            if not self._match_token(bar, token, bars):
                return False
        return True

    def _match_token(self, bar: CandleBar, token: str,
                     all_bars: List[CandleBar]) -> bool:
        if token == "ANY":
            return True
        if token == "YANG":
            return bar.is_yang
        if token == "YIN":
            return bar.is_yin
        if token == "BIG_YANG":
            return self._is_big_yang(bar)
        if token == "BIG_YIN":
            return self._is_big_yin(bar)
        if token == "SMALL":
            return self._is_small_body(bar)
        if token == "DOJI":
            return bar.body_ratio <= 0.05
        if token == "LIMIT_UP":
            return bar.is_limit_up
        if token == "LIMIT_DOWN":
            return bar.is_limit_down
        if token == "UP":
            idx = all_bars.index(bar)
            return idx > 0 and bar.close > all_bars[idx - 1].close
        if token == "DOWN":
            idx = all_bars.index(bar)
            return idx > 0 and bar.close < all_bars[idx - 1].close
        return False

    # ── 事件发布 ──────────────────────────────────────────────────────

    def _emit(self, event_type: str, data: dict) -> None:
        if self._dispatch:
            try:
                self._dispatch(event_type, data)
            except Exception:
                pass

    def _emit_signal(self, sig: SequenceSignal) -> None:
        from ..event import EVENT_MB_SEQUENCE_FOUND
        self._emit(EVENT_MB_SEQUENCE_FOUND, sig.to_dict())
