"""
market_behavior/engine/candle_engine.py
Phase 2: K线解析系统
  - LimitRuleEngine  涨跌停规则（按板块动态计算，不写死）
  - CandleParser     OHLCV → CandleBar 派生字段
  - CandleBuffer     按 symbol 缓存 K线序列
  - CandleEngine     主引擎入口
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from datetime import date, datetime
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

from ..constant import BoardType
from ..model.candle import CandleBar


# ══════════════════════════════════════════════════════════════════════
# LimitRuleEngine — 涨跌停规则
# ══════════════════════════════════════════════════════════════════════

# 各板块正常交易日涨跌停幅度
_BOARD_LIMIT: Dict[BoardType, float] = {
    BoardType.MAIN:    0.10,   # 主板   ±10%
    BoardType.GEM:     0.20,   # 创业板 ±20%
    BoardType.STAR:    0.20,   # 科创板 ±20%
    BoardType.BSE:     0.30,   # 北交所 ±30%
    BoardType.ST:      0.05,   # ST    ±5%
    BoardType.ST_STAR: 0.05,   # *ST   ±5%
}

# 上市首 5 日无涨跌停限制的板块
_NO_LIMIT_FIRST5: frozenset = frozenset({BoardType.GEM, BoardType.STAR})

# 涨跌停判断容差（避免浮点误差漏判）
_LIMIT_TOLERANCE: float = 0.0001


class LimitRuleEngine:
    """
    涨跌停规则引擎。
    - 按 BoardType 返回当日限幅
    - 支持上市首5日无限制逻辑
    - 判断 K线是否触及涨/跌停
    """

    def __init__(self) -> None:
        # 上市日期缓存 {symbol: listing_date}，由外部注入
        self._listing_dates: Dict[str, date] = {}

    def set_listing_date(self, symbol: str, listing_date: date) -> None:
        """注入股票上市日期，用于首5日无限制判断。"""
        self._listing_dates[symbol] = listing_date

    def get_limit_pct(
        self,
        board: BoardType,
        symbol: str = "",
        trade_date: Optional[date] = None,
    ) -> float:
        """
        返回该板块当日涨跌停幅度（小数，如 0.10 = 10%）。
        若股票属于首5日无限制板块且在上市首5日内，返回 math.inf。
        """
        if board in _NO_LIMIT_FIRST5 and symbol and trade_date:
            listing = self._listing_dates.get(symbol)
            if listing:
                delta = (trade_date - listing).days
                if 0 <= delta < 5:
                    return math.inf

        return _BOARD_LIMIT.get(board, 0.10)

    def is_limit_up(
        self,
        close: float,
        prev_close: float,
        limit_pct: float,
    ) -> bool:
        """
        判断是否触及涨停。
        涨停价 = round(prev_close × (1 + limit_pct), 2)
        容差 _LIMIT_TOLERANCE 处理浮点精度。
        """
        if prev_close <= 0 or limit_pct == math.inf:
            return False
        limit_up_price = round(prev_close * (1 + limit_pct), 2)
        return close >= limit_up_price - _LIMIT_TOLERANCE

    def is_limit_down(
        self,
        close: float,
        prev_close: float,
        limit_pct: float,
    ) -> bool:
        """判断是否触及跌停。"""
        if prev_close <= 0 or limit_pct == math.inf:
            return False
        limit_down_price = round(prev_close * (1 - limit_pct), 2)
        return close <= limit_down_price + _LIMIT_TOLERANCE

    def calc_limit_up_price(self, prev_close: float,
                            limit_pct: float) -> float:
        if limit_pct == math.inf:
            return math.inf
        return round(prev_close * (1 + limit_pct), 2)

    def calc_limit_down_price(self, prev_close: float,
                              limit_pct: float) -> float:
        if limit_pct == math.inf:
            return 0.0
        return round(prev_close * (1 - limit_pct), 2)

# ══════════════════════════════════════════════════════════════════════
# CandleParser — OHLCV → CandleBar 派生字段计算
# ══════════════════════════════════════════════════════════════════════

class CandleParser:
    """
    K线解析器。
    将原始 OHLCV 数据解析为带全量派生字段的 CandleBar 对象。
    """

    def __init__(self, limit_engine: LimitRuleEngine) -> None:
        self._limit = limit_engine

    def parse(
        self,
        symbol:     str,
        dt:         datetime,
        open_:      float,
        high:       float,
        low:        float,
        close:      float,
        volume:     float,
        prev_close: float,
        board:      BoardType = BoardType.MAIN,
        turnover:   float = 0.0,
        turnover_rate: float = 0.0,
        trade_date: Optional[date] = None,
    ) -> Optional[CandleBar]:
        """
        解析单根K线，返回 CandleBar。
        数据校验失败时返回 None。
        """
        # ── 数据校验 ──────────────────────────────────────────────────
        if not self._validate(symbol, open_, high, low, close,
                              volume, prev_close):
            return None

        # ── 涨跌幅 ────────────────────────────────────────────────────
        _change_pct = (
            (close - prev_close) / prev_close * 100
            if prev_close > 0 else 0.0
        )

        # ── 实体 ──────────────────────────────────────────────────────
        _body        = abs(close - open_)
        _body_pct    = (_body / prev_close * 100) if prev_close > 0 else 0.0
        _range       = high - low

        # 零振幅保护（一字涨跌停等）
        if _range > 0:
            _body_ratio         = _body / _range
            _upper_shadow       = high - max(open_, close)
            _lower_shadow       = min(open_, close) - low
            _upper_shadow_ratio = _upper_shadow / _range
            _lower_shadow_ratio = _lower_shadow / _range
        else:
            _body_ratio         = 1.0 if _body > 0 else 0.0
            _upper_shadow       = 0.0
            _lower_shadow       = 0.0
            _upper_shadow_ratio = 0.0
            _lower_shadow_ratio = 0.0

        # ── 振幅 ──────────────────────────────────────────────────────
        _amplitude = (_range / prev_close * 100) if prev_close > 0 else 0.0

        # ── 方向 ──────────────────────────────────────────────────────
        _is_yang = close >= open_
        _is_yin  = close < open_

        # ── 涨跌停 ────────────────────────────────────────────────────
        td = trade_date or (dt.date() if hasattr(dt, "date") else None)
        _limit_pct   = self._limit.get_limit_pct(board, symbol, td)
        _is_limit_up   = self._limit.is_limit_up(close, prev_close, _limit_pct)
        _is_limit_down = self._limit.is_limit_down(close, prev_close, _limit_pct)

        # 对外展示用：inf 转成百分数字符串不友好，存实际小数值
        import math as _math
        _limit_pct_store = _limit_pct if not _math.isinf(_limit_pct) else 9999.0

        return CandleBar(
            symbol=symbol,
            dt=dt,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
            turnover=turnover,
            turnover_rate=turnover_rate,
            board=board,
            prev_close=prev_close,
            change_pct=round(_change_pct, 4),
            body=round(_body, 4),
            body_pct=round(_body_pct, 4),
            body_ratio=round(_body_ratio, 4),
            upper_shadow=round(_upper_shadow, 4),
            lower_shadow=round(_lower_shadow, 4),
            upper_shadow_ratio=round(_upper_shadow_ratio, 4),
            lower_shadow_ratio=round(_lower_shadow_ratio, 4),
            amplitude=round(_amplitude, 4),
            is_yang=_is_yang,
            is_yin=_is_yin,
            is_limit_up=_is_limit_up,
            is_limit_down=_is_limit_down,
            limit_pct=_limit_pct_store * 100,  # 存为百分比，如 10.0 / 20.0
        )

    @staticmethod
    def _validate(
        symbol: str,
        open_: float, high: float, low: float, close: float,
        volume: float, prev_close: float,
    ) -> bool:
        """基础数据校验，返回 False 表示数据异常。"""
        if not symbol:
            return False
        if any(v != v for v in (open_, high, low, close)):  # NaN 检测
            return False
        if any(v <= 0 for v in (open_, high, low, close)):
            return False
        if high < low:
            return False
        if high < open_ or high < close:
            return False
        if low > open_ or low > close:
            return False
        if volume < 0:
            return False
        if prev_close < 0:
            return False
        return True


# ══════════════════════════════════════════════════════════════════════
# CandleBuffer — K线序列缓存
# ══════════════════════════════════════════════════════════════════════

class CandleBuffer:
    """
    按 symbol 独立维护最近 max_size 根 CandleBar 的滑动窗口缓存。
    供 EventDetectEngine / PatternEngine / BreakoutEngine 等引擎查询。
    """

    DEFAULT_SIZE = 250   # 约1个交易年

    def __init__(self, max_size: int = DEFAULT_SIZE) -> None:
        self._max_size = max_size
        self._data: Dict[str, Deque[CandleBar]] = defaultdict(
            lambda: deque(maxlen=self._max_size)
        )

    def push(self, bar: CandleBar) -> None:
        """压入一根K线。"""
        self._data[bar.symbol].append(bar)

    def get(self, symbol: str, n: int = 1) -> List[CandleBar]:
        """返回最近 n 根 K线（最新的在列表末尾）。"""
        dq = self._data.get(symbol)
        if not dq:
            return []
        bars = list(dq)
        return bars[-n:] if n < len(bars) else bars

    def latest(self, symbol: str) -> Optional[CandleBar]:
        """返回最新一根 K线，不存在则 None。"""
        dq = self._data.get(symbol)
        return dq[-1] if dq else None

    def get_field(self, symbol: str, field: str,
                  n: int = 20) -> List[float]:
        """
        返回最近 n 根 K线的指定字段值列表。
        field: 'close' / 'open' / 'high' / 'low' / 'volume' /
               'change_pct' / 'body_ratio' / 'upper_shadow_ratio' 等
        """
        bars = self.get(symbol, n)
        result = []
        for bar in bars:
            v = getattr(bar, field, None)
            if v is not None:
                result.append(float(v))
        return result

    def get_closes(self, symbol: str, n: int = 20) -> List[float]:
        return self.get_field(symbol, "close", n)

    def get_volumes(self, symbol: str, n: int = 20) -> List[float]:
        return self.get_field(symbol, "volume", n)

    def get_highs(self, symbol: str, n: int = 20) -> List[float]:
        return self.get_field(symbol, "high", n)

    def get_lows(self, symbol: str, n: int = 20) -> List[float]:
        return self.get_field(symbol, "low", n)

    def size(self, symbol: str) -> int:
        """已缓存的 K线根数。"""
        dq = self._data.get(symbol)
        return len(dq) if dq else 0

    def symbols(self) -> List[str]:
        return list(self._data.keys())

    def clear(self, symbol: str = "") -> None:
        if symbol:
            self._data.pop(symbol, None)
        else:
            self._data.clear()


# ══════════════════════════════════════════════════════════════════════
# CandleEngine — 主引擎入口
# ══════════════════════════════════════════════════════════════════════

class CandleEngine:
    """
    K线解析引擎（Phase 2 完整实现）。

    组合：
      LimitRuleEngine  涨跌停规则
      CandleParser     OHLCV → CandleBar
      CandleBuffer     K线序列缓存

    主入口：
      parse_bar()      解析单根K线，缓存并发布事件
      parse_bars()     批量解析
    """

    def __init__(
        self,
        log_fn: Optional[Callable[[str], None]] = None,
        main_engine: Any = None,
        dispatch_fn: Optional[Callable[[str, dict], None]] = None,
        buffer_size: int = CandleBuffer.DEFAULT_SIZE,
    ) -> None:
        self._log         = log_fn or print
        self._main_engine = main_engine
        self._dispatch    = dispatch_fn
        self._running     = False

        self.limit_engine  = LimitRuleEngine()
        self._parser       = CandleParser(self.limit_engine)
        self.buffer        = CandleBuffer(max_size=buffer_size)

        self._parse_count: int = 0
        self._error_count: int = 0

    # ── BaseEngine 接口 ───────────────────────────────────────────────

    def set_main_engine(self, engine: Any) -> None:
        self._main_engine = engine

    def set_dispatch(self, fn: Callable[[str, dict], None]) -> None:
        self._dispatch = fn

    def init(self) -> None:
        self._log("[CandleEngine] init()")

    def start(self) -> None:
        self._running = True
        self._log("[CandleEngine] start()")

    def stop(self) -> None:
        self._running = False
        self._log("[CandleEngine] stop()")

    def summary(self) -> dict:
        return {
            "engine":       "CandleEngine",
            "status":       "running" if self._running else "stopped",
            "parsed":       self._parse_count,
            "errors":       self._error_count,
            "symbols":      len(self.buffer.symbols()),
        }

    # ── 上市日期注入 ──────────────────────────────────────────────────

    def set_listing_date(self, symbol: str, listing_date) -> None:
        """注入上市日期，用于首5日无限制判断（科创板/创业板）。"""
        if isinstance(listing_date, str):
            from datetime import date as _date
            listing_date = _date.fromisoformat(listing_date)
        self.limit_engine.set_listing_date(symbol, listing_date)

    # ── 主解析接口 ────────────────────────────────────────────────────

    def parse_bar(
        self,
        symbol:     str,
        dt:         datetime,
        open_:      float,
        high:       float,
        low:        float,
        close:      float,
        volume:     float,
        prev_close: float,
        board:      BoardType = BoardType.MAIN,
        turnover:   float = 0.0,
        turnover_rate: float = 0.0,
    ) -> Optional[CandleBar]:
        """
        解析单根K线。
        成功：缓存 + 发布 EVENT_MB_CANDLE_PARSED + 返回 CandleBar。
        失败：发布 ERROR 事件 + 返回 None。
        """
        trade_date = dt.date() if hasattr(dt, "date") else None
        bar = self._parser.parse(
            symbol=symbol, dt=dt,
            open_=open_, high=high, low=low, close=close,
            volume=volume, prev_close=prev_close,
            board=board, turnover=turnover,
            turnover_rate=turnover_rate,
            trade_date=trade_date,
        )

        if bar is None:
            self._error_count += 1
            self._emit_error(symbol, dt, open_, high, low, close)
            return None

        self.buffer.push(bar)
        self._parse_count += 1
        self._emit_parsed(bar)
        return bar

    def parse_bars(
        self,
        symbol:     str,
        rows:       List[dict],
        board:      BoardType = BoardType.MAIN,
    ) -> List[CandleBar]:
        """
        批量解析K线。
        rows 格式: [{"dt":..., "open":..., "high":..., "low":...,
                     "close":..., "volume":..., "prev_close":...}, ...]
        按时间顺序传入，内部自动处理 prev_close 链接。
        """
        results: List[CandleBar] = []
        prev_close = 0.0

        for row in rows:
            dt        = row.get("dt") or row.get("datetime")
            open_     = float(row.get("open",  0))
            high      = float(row.get("high",  0))
            low       = float(row.get("low",   0))
            close     = float(row.get("close", 0))
            volume    = float(row.get("volume", 0))
            pc        = float(row.get("prev_close", prev_close) or prev_close)
            turnover  = float(row.get("turnover", 0))
            tr        = float(row.get("turnover_rate", 0))

            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt)

            bar = self.parse_bar(
                symbol=symbol, dt=dt,
                open_=open_, high=high, low=low, close=close,
                volume=volume, prev_close=pc,
                board=board, turnover=turnover, turnover_rate=tr,
            )
            if bar:
                results.append(bar)
                prev_close = bar.close

        return results

    # ── 查询代理（便捷方法）──────────────────────────────────────────

    def get_bars(self, symbol: str, n: int = 20) -> List[CandleBar]:
        return self.buffer.get(symbol, n)

    def get_closes(self, symbol: str, n: int = 20) -> List[float]:
        return self.buffer.get_closes(symbol, n)

    def get_volumes(self, symbol: str, n: int = 20) -> List[float]:
        return self.buffer.get_volumes(symbol, n)

    def latest_bar(self, symbol: str) -> Optional[CandleBar]:
        return self.buffer.latest(symbol)

    # ── 事件发布 ──────────────────────────────────────────────────────

    def _emit(self, event_type: str, data: dict) -> None:
        if self._dispatch:
            try:
                self._dispatch(event_type, data)
            except Exception:
                pass

    def _emit_parsed(self, bar: CandleBar) -> None:
        from ..event import EVENT_MB_CANDLE_PARSED
        self._emit(EVENT_MB_CANDLE_PARSED, bar.to_dict())

    def _emit_error(self, symbol: str, dt: datetime,
                    o: float, h: float, l: float, c: float) -> None:
        from ..event import EVENT_MB_ERROR
        self._emit(EVENT_MB_ERROR, {
            "msg":    f"CandleEngine: invalid bar {symbol} {dt} O{o} H{h} L{l} C{c}",
            "symbol": symbol,
            "dt":     str(dt),
        })
