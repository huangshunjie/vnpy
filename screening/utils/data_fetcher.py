"""
screening/utils/data_fetcher.py

统一数据获取层（Phase 3）。

为 ConditionEngine 提供每只股票的字段值查询接口。
优先从 vnpy DatabaseManager 获取 bar 数据并计算技术指标；
无数据时返回 None，ConditionEngine 对 None 值的条件判定为 True（不过滤）。
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta


class SymbolData:
    """单只股票的缓存数据容器。"""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.closes: List[float] = []
        self.volumes: List[float] = []
        self.turnovers: List[float] = []
        self.highs: List[float] = []
        self.lows: List[float] = []
        self._cache: Dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    # ── 技术指标计算 ──────────────────────────────────────────────────

    def ma(self, period: int) -> Optional[float]:
        key = f"ma{period}"
        if key not in self._cache:
            if len(self.closes) < period:
                self._cache[key] = None
            else:
                self._cache[key] = sum(self.closes[-period:]) / period
        return self._cache[key]

    def ema(self, period: int) -> Optional[float]:
        key = f"ema{period}"
        if key not in self._cache:
            if len(self.closes) < period:
                self._cache[key] = None
            else:
                k = 2.0 / (period + 1)
                ema = self.closes[0]
                for p in self.closes[1:]:
                    ema = p * k + ema * (1 - k)
                self._cache[key] = ema
        return self._cache[key]

    def rsi(self, period: int = 14) -> Optional[float]:
        key = f"rsi{period}"
        if key not in self._cache:
            if len(self.closes) < period + 1:
                self._cache[key] = None
            else:
                diffs = [self.closes[i] - self.closes[i-1]
                         for i in range(1, len(self.closes))]
                gains = [d for d in diffs if d > 0]
                losses = [-d for d in diffs if d < 0]
                avg_gain = sum(gains[-period:]) / period if gains else 0
                avg_loss = sum(losses[-period:]) / period if losses else 0
                if avg_loss == 0:
                    self._cache[key] = 100.0
                else:
                    rs = avg_gain / avg_loss
                    self._cache[key] = 100 - 100 / (1 + rs)
        return self._cache[key]

    def avg_turnover(self, period: int = 20) -> Optional[float]:
        key = f"avg_turnover{period}"
        if key not in self._cache:
            if not self.turnovers:
                self._cache[key] = None
            else:
                vals = self.turnovers[-period:]
                self._cache[key] = sum(vals) / len(vals)
        return self._cache[key]

    def volatility(self, period: int = 20) -> Optional[float]:
        """年化波动率。"""
        key = f"vol{period}"
        if key not in self._cache:
            if len(self.closes) < period + 1:
                self._cache[key] = None
            else:
                import math
                rets = []
                for i in range(1, period + 1):
                    c0 = self.closes[-(period + 1) + i - 1]
                    c1 = self.closes[-(period + 1) + i]
                    if c0 > 0:
                        rets.append((c1 - c0) / c0)
                if not rets:
                    self._cache[key] = None
                else:
                    mean = sum(rets) / len(rets)
                    var = sum((r - mean) ** 2 for r in rets) / len(rets)
                    self._cache[key] = math.sqrt(var * 252)
        return self._cache[key]


class DataFetcher:
    """
    统一数据获取层。

    为 ConditionEngine 提供 get_field(symbol, field_name) 接口。
    所有字段名与 ConditionWidget 中的字段定义一一对应。
    """

    _FIELD_MAP = {
        # 技术面
        "ma5": lambda d: d.ma(5),
        "ma10": lambda d: d.ma(10),
        "ma20": lambda d: d.ma(20),
        "ma60": lambda d: d.ma(60),
        "ma120": lambda d: d.ma(120),
        "ma250": lambda d: d.ma(250),
        "ema12": lambda d: d.ema(12),
        "ema26": lambda d: d.ema(26),
        "rsi14": lambda d: d.rsi(14),
        "close": lambda d: d.closes[-1] if d.closes else None,
        "volume": lambda d: d.volumes[-1] if d.volumes else None,
        "volatility20": lambda d: d.volatility(20),
        # 资金面
        "avg_turnover20": lambda d: d.avg_turnover(20),
        "turnover": lambda d: d.turnovers[-1] if d.turnovers else None,
    }

    def __init__(self, main_engine: Any = None) -> None:
        self._main_engine = main_engine
        self._cache: Dict[str, SymbolData] = {}

    def set_main_engine(self, main_engine: Any) -> None:
        self._main_engine = main_engine

    def clear_cache(self) -> None:
        self._cache.clear()

    def get_symbol_data(self, symbol: str, limit: int = 250) -> SymbolData:
        """获取（或从缓存读取）股票历史 bar 数据。"""
        if symbol in self._cache:
            return self._cache[symbol]

        sd = SymbolData(symbol)
        self._load_bars(sd, symbol, limit)
        self._cache[symbol] = sd
        return sd

    def _load_bars(self, sd: SymbolData, symbol: str, limit: int) -> None:
        """从 DatabaseManager 加载 bar 数据。无数据时保持空列表。"""
        if self._main_engine is None:
            return
        try:
            from vnpy.trader.constant import Exchange, Interval
            from vnpy.trader.object import BarData

            parts = symbol.split(".")
            if len(parts) != 2:
                return
            code, exch_str = parts
            try:
                exchange = Exchange(exch_str)
            except ValueError:
                return

            db = self._main_engine.get_database()
            if db is None:
                return

            end = datetime.now()
            start = end - timedelta(days=limit * 2)
            bars: List[BarData] = db.load_bar_data(
                symbol=code,
                exchange=exchange,
                interval=Interval.DAILY,
                start=start,
                end=end,
            )
            if not bars:
                return

            bars = bars[-limit:]
            sd.closes = [b.close_price for b in bars]
            sd.volumes = [b.volume for b in bars]
            sd.turnovers = [b.turnover for b in bars if b.turnover]
            sd.highs = [b.high_price for b in bars]
            sd.lows = [b.low_price for b in bars]
        except Exception:
            pass

    def get_field(self, symbol: str, field_name: str) -> Optional[Any]:
        """
        获取指定股票的指定字段值。
        返回 None 表示数据不可用，调用方应视为条件通过（不过滤）。
        """
        field_lower = field_name.lower().replace(" ", "").replace("_", "")

        sd = self.get_symbol_data(symbol)

        # 先查预定义字段
        for key, fn in self._FIELD_MAP.items():
            if key.lower().replace("_", "") == field_lower:
                return fn(sd)

        # 查自定义缓存
        return sd.get(field_name)

    def set_fundamental(self, symbol: str, field: str, value: float) -> None:
        """注入基本面数据（供测试或外部数据源使用）。"""
        sd = self.get_symbol_data(symbol)
        sd.set(field, value)
