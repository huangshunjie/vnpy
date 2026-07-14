"""
market_behavior/engine_main.py
MarketBehaviorEngine — 主引擎，聚合 9 个子引擎 (Phase 9)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..event import EventEngine, Event
from ..trader.engine import BaseEngine, MainEngine

from .constant import APP_NAME
from .event import (
    EVENT_MB_LOG, EVENT_MB_STARTED, EVENT_MB_STOPPED,
)
from .engine.candle_engine   import CandleEngine, CandleBuffer
from .engine.event_engine    import EventDetectEngine
from .engine.pattern_engine  import PatternEngine
from .engine.sequence_engine import SequenceEngine
from .engine.breakout_engine import BreakoutEngine
from .engine.factor_engine   import FactorEngine
from .engine.label_engine    import LabelEngine
from .engine.adapter_engine  import AdapterEngine, ScreenSpec
from .engine.backtest_engine import BacktestEngine, BacktestResult
from .model.candle import CandleBar


class MarketBehaviorEngine(BaseEngine):
    """
    Quant Market Behavior 主引擎 (Phase 9)。

    聚合 9 个子引擎，提供统一接口：
      on_bar()     流式推送新K线，自动触发完整分析链路
      subscribe()  注册关注标的
      query()      查询指定标的当前行为快照
      screen()     对全部订阅标的做选股
      backtest()   对指定标的做条件回测
      get_status() 所有子引擎 summary 汇总
    """

    def __init__(
        self,
        main_engine:  MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)

        def _log(msg: str) -> None:
            self.write_log(msg)

        def _dispatch(event_type: str, data: dict) -> None:
            self.event_engine.put(Event(event_type, data))

        # ── 共享 buffer ───────────────────────────────────────────────
        self._buffer = CandleBuffer()

        # ── 子引擎实例化 ──────────────────────────────────────────────
        self._candle   = CandleEngine  (log_fn=_log, dispatch_fn=_dispatch)
        self._event    = EventDetectEngine(log_fn=_log, dispatch_fn=_dispatch)
        self._pattern  = PatternEngine (log_fn=_log, dispatch_fn=_dispatch)
        self._sequence = SequenceEngine(log_fn=_log, dispatch_fn=_dispatch)
        self._breakout = BreakoutEngine(log_fn=_log, dispatch_fn=_dispatch)
        self._factor   = FactorEngine  (log_fn=_log, dispatch_fn=_dispatch)
        self._label    = LabelEngine   (log_fn=_log, dispatch_fn=_dispatch)
        self._adapter  = AdapterEngine (log_fn=_log, dispatch_fn=_dispatch)
        self._backtest = BacktestEngine(log_fn=_log, dispatch_fn=_dispatch)

        self._analysis_engines = [
            self._event, self._pattern, self._sequence,
            self._breakout, self._factor, self._label,
        ]
        self._all_engines = [
            self._candle, *self._analysis_engines,
            self._adapter, self._backtest,
        ]

        # 订阅标的集合
        self._subscribed: set = set()
        # 行为快照缓存 {symbol: snapshot_dict}
        self._snapshots: Dict[str, dict] = {}

    # ══════════════════════════════════════════════════════════════════
    # BaseEngine 接口
    # ══════════════════════════════════════════════════════════════════

    def init_engine(self) -> None:
        """初始化所有子引擎并注入依赖。"""
        # 注入共享 buffer
        for eng in self._all_engines:
            if hasattr(eng, "set_candle_buffer"):
                eng.set_candle_buffer(self._buffer)
            if hasattr(eng, "set_main_engine"):
                eng.set_main_engine(self.main_engine)

        # 注入跨引擎依赖
        self._adapter.set_factor_engine(self._factor)
        self._adapter.set_label_engine(self._label)
        self._backtest.set_adapter_engine(self._adapter)

        for eng in self._all_engines:
            eng.init()

        self.write_log(
            f"[{APP_NAME}] init_engine — {len(self._all_engines)} sub-engines ready"
        )
        self.event_engine.put(Event(EVENT_MB_STARTED, {"engine": APP_NAME}))

    def close(self) -> None:
        """逆序停止所有子引擎。"""
        for eng in reversed(self._all_engines):
            eng.stop()
        self.write_log(f"[{APP_NAME}] stopped")
        self.event_engine.put(Event(EVENT_MB_STOPPED, {"engine": APP_NAME}))

    # ══════════════════════════════════════════════════════════════════
    # 标的管理
    # ══════════════════════════════════════════════════════════════════

    def subscribe(self, symbol: str) -> None:
        """注册关注标的。"""
        if symbol not in self._subscribed:
            self._subscribed.add(symbol)
            self.write_log(f"[{APP_NAME}] subscribed: {symbol}")

    def unsubscribe(self, symbol: str) -> None:
        self._subscribed.discard(symbol)
        self._buffer.clear(symbol)
        self._snapshots.pop(symbol, None)

    def get_subscribed(self) -> List[str]:
        return sorted(self._subscribed)

    # ══════════════════════════════════════════════════════════════════
    # on_bar() 流式处理链路
    # ══════════════════════════════════════════════════════════════════

    def on_bar(self, bar: CandleBar) -> None:
        """
        接收新K线，依次触发完整分析链路：
          1. CandleEngine   — 解析并压入 buffer
          2. EventDetect    — 价格事件检测
          3. PatternEngine  — 单K形态
          4. SequenceEngine — K线组合模式
          5. BreakoutEngine — 突破检测
          6. FactorEngine   — 行为因子
          7. LabelEngine    — 行为标签
        结果写入 _snapshots[symbol]，并发布事件。
        """
        if not bar:
            return

        symbol = bar.symbol

        # 1. 压入 buffer（CandleEngine 仅作解析校验）
        self._buffer.push(bar)

        # 2. 价格事件检测
        events   = self._event.detect(symbol)

        # 3. 单K形态
        patterns = self._pattern.detect(symbol)

        # 4. K线组合模式
        seqs     = self._sequence.detect(symbol)

        # 5. 突破检测
        bks      = self._breakout.detect(symbol)

        # 6. 行为因子
        factors  = self._factor.compute(symbol)

        # 7. 行为标签
        label    = self._label.label(symbol, factors=factors)

        # 更新快照
        self._snapshots[symbol] = {
            "symbol":    symbol,
            "dt":        str(bar.dt)[:19],
            "close":     bar.close,
            "change_pct": bar.change_pct,
            "events":    [e.to_dict()  for e in events],
            "patterns":  [p.to_dict()  for p in patterns],
            "sequences": [s.to_dict()  for s in seqs],
            "breakouts": [b.to_dict()  for b in bks],
            "factors":   {f.factor_type.value: round(f.norm_value, 4)
                          for f in factors},
            "labels":    [lt.value for lt in (label.labels if label else [])],
            "label_scores": label.scores if label else {},
        }

    def on_bars(self, bars: list) -> None:
        """批量推送K线（历史回放或批量更新场景）。"""
        for bar in bars:
            self.on_bar(bar)

    # ══════════════════════════════════════════════════════════════════
    # query()
    # ══════════════════════════════════════════════════════════════════

    def query(self, symbol: str) -> dict:
        """
        查询指定标的的当前行为快照。
        若尚无数据则触发一次全量计算后返回。
        """
        if symbol not in self._snapshots:
            bars = self._buffer.get(symbol, 1)
            if not bars:
                return {"symbol": symbol, "error": "no_data"}
            self.on_bar(bars[-1])
        return self._snapshots.get(symbol, {"symbol": symbol, "error": "no_data"})

    def query_all(self) -> Dict[str, dict]:
        """返回所有订阅标的的快照字典。"""
        return {sym: self.query(sym) for sym in self._subscribed}

    # ══════════════════════════════════════════════════════════════════
    # screen()
    # ══════════════════════════════════════════════════════════════════

    def screen(
        self,
        spec:    "ScreenSpec",
        symbols: Optional[List[str]] = None,
    ) -> list:
        """
        对订阅标的（或指定列表）做选股筛选。
        返回 ScreenResult 列表，按 score 降序排列。
        """
        target = symbols if symbols is not None else list(self._subscribed)
        if not target:
            return []
        return self._adapter.screen(target, spec)

    # ══════════════════════════════════════════════════════════════════
    # backtest()
    # ══════════════════════════════════════════════════════════════════

    def backtest(
        self,
        symbol:    str,
        spec:      "ScreenSpec",
        hold_days: int = 5,
        all_bars:  Optional[list] = None,
    ) -> "BacktestResult":
        """
        对指定标的做条件回测。
        all_bars 可外部传入；不传则从 buffer 取全量历史。
        """
        bars = all_bars if all_bars is not None else self._buffer.get(symbol, 9999)
        return self._backtest.run(symbol, bars, spec, hold_days=hold_days)

    # ══════════════════════════════════════════════════════════════════
    # 状态 / 工具
    # ══════════════════════════════════════════════════════════════════

    def get_status(self) -> dict:
        """汇总所有子引擎状态。"""
        return {
            "engine":     APP_NAME,
            "subscribed": list(self._subscribed),
            "snapshots":  len(self._snapshots),
            "sub_engines": {
                "candle":   self._candle.summary(),
                "event":    self._event.summary(),
                "pattern":  self._pattern.summary(),
                "sequence": self._sequence.summary(),
                "breakout": self._breakout.summary(),
                "factor":   self._factor.summary(),
                "label":    self._label.summary(),
                "adapter":  self._adapter.summary(),
                "backtest": self._backtest.summary(),
            },
        }

    def summary(self) -> dict:
        return self.get_status()

    def write_log(self, msg: str) -> None:
        self.event_engine.put(Event(EVENT_MB_LOG, {"msg": msg}))

    # ── 子引擎直接访问（供高级用法）─────────────────────────────────

    @property
    def candle_engine(self)   -> CandleEngine:        return self._candle
    @property
    def event_engine_(self)   -> EventDetectEngine:   return self._event
    @property
    def pattern_engine(self)  -> PatternEngine:       return self._pattern
    @property
    def sequence_engine(self) -> SequenceEngine:      return self._sequence
    @property
    def breakout_engine(self) -> BreakoutEngine:      return self._breakout
    @property
    def factor_engine(self)   -> FactorEngine:        return self._factor
    @property
    def label_engine(self)    -> LabelEngine:         return self._label
    @property
    def adapter_engine(self)  -> AdapterEngine:       return self._adapter
    @property
    def backtest_engine(self) -> BacktestEngine:      return self._backtest
    @property
    def buffer(self)          -> CandleBuffer:        return self._buffer
