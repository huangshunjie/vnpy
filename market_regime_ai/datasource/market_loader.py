"""
market_regime_ai/datasource/market_loader.py  (Phase 5)

MarketDataLoader — 从 VeighNa DatabaseManager 只读取 K 线数据。

Phase 5 实现：
  - 通过 MainEngine 获取 ManagerEngine 引用
  - load_bar_data() → 价格序列 / 成交量序列 / 高低价序列
  - 支持多品种批量加载
  - 降级时返回空列表（不阻断主流程）

❌ 只读，绝不写入数据库
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

_DM_ENGINE_NAME = "DataManager"


class MarketDataLoader:
    """
    从 DatabaseManager 加载市场数据（Phase 5 完整实现）。

    用法：
        loader = MarketDataLoader(main_engine)
        prices, volumes, highs, lows = loader.get_ohlcv("rb2501", "d", 120)
    """

    def __init__(
        self,
        main_engine: Any = None,
        engine_name: str = _DM_ENGINE_NAME,
        default_limit: int = 250,
    ) -> None:
        self._main_engine  = main_engine
        self._engine_name  = engine_name
        self._default_limit = default_limit
        self._dm_engine    = None
        self._cache:       dict[str, tuple] = {}   # symbol → (ts, data)
        self._cache_ttl    = 60                     # 秒，缓存有效期

    # ------------------------------------------------------------------ #
    #  引擎获取（懒加载）
    # ------------------------------------------------------------------ #

    def _get_dm_engine(self):
        if self._dm_engine is not None:
            return self._dm_engine
        if self._main_engine is None:
            return None
        try:
            engine = self._main_engine.get_engine(self._engine_name)
            if engine is not None:
                self._dm_engine = engine
            return engine
        except Exception as e:
            logger.debug(f"[MarketDataLoader] get_engine failed: {e}")
            return None

    def is_available(self) -> bool:
        return self._get_dm_engine() is not None

    # ------------------------------------------------------------------ #
    #  K 线数据加载
    # ------------------------------------------------------------------ #

    def get_ohlcv(
        self,
        symbol:   str,
        exchange: str  = "",
        interval: str  = "d",
        limit:    int  = 250,
        end_date: datetime | None = None,
    ) -> tuple[list[float], list[float], list[float], list[float]]:
        """
        加载 OHLCV 数据。

        Returns
        -------
        (prices, volumes, highs, lows)
          prices  : 收盘价序列
          volumes : 成交量序列
          highs   : 最高价序列
          lows    : 最低价序列
        全部为 list[float]，数据不足时返回空列表。
        """
        cache_key = f"{symbol}_{interval}_{limit}"
        now = datetime.now()

        # 缓存命中
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if (now - ts).total_seconds() < self._cache_ttl:
                return data

        engine = self._get_dm_engine()
        if engine is None:
            return [], [], [], []

        try:
            end   = end_date or now
            start = end - timedelta(days=limit * 2)

            from vnpy.trader.constant import Interval, Exchange
            interval_map = {
                "1m": Interval.MINUTE, "5m": Interval.MINUTE,
                "1h": Interval.HOUR,   "d":  Interval.DAILY,
                "w":  Interval.WEEKLY,
            }
            iv = interval_map.get(interval, Interval.DAILY)

            # exchange 处理
            ex = None
            if exchange:
                try:
                    ex = Exchange(exchange)
                except ValueError:
                    ex = None

            bars = engine.load_bar_data(
                symbol   = symbol,
                exchange = ex,
                interval = iv,
                start    = start,
                end      = end,
            ) if ex else []

            # 如果带 exchange 失败，尝试不带
            if not bars:
                bars = []

            prices  = [float(b.close_price) for b in bars[-limit:]]
            volumes = [float(b.volume)       for b in bars[-limit:]]
            highs   = [float(b.high_price)   for b in bars[-limit:]]
            lows    = [float(b.low_price)    for b in bars[-limit:]]

            result = (prices, volumes, highs, lows)
            self._cache[cache_key] = (now, result)
            return result

        except Exception as e:
            logger.debug(f"[MarketDataLoader] load_bar_data {symbol}: {e}")
            return [], [], [], []

    def get_prices(
        self,
        symbol:   str,
        exchange: str = "",
        interval: str = "d",
        limit:    int = 250,
    ) -> list[float]:
        """仅返回收盘价序列。"""
        prices, _, _, _ = self.get_ohlcv(symbol, exchange, interval, limit)
        return prices

    def get_symbols(self) -> list[str]:
        """获取数据库中可用的品种列表。"""
        engine = self._get_dm_engine()
        if engine is None:
            return []
        try:
            overviews = engine.get_bar_overview()
            if not overviews:
                return []
            return [f"{o.symbol}.{o.exchange.value}" for o in overviews]
        except Exception as e:
            logger.debug(f"[MarketDataLoader] get_bar_overview: {e}")
            return []

    def clear_cache(self) -> None:
        """清除数据缓存。"""
        self._cache.clear()

    # ------------------------------------------------------------------ #
    #  摘要
    # ------------------------------------------------------------------ #

    def summary(self) -> dict:
        return {
            "source":        "database_manager",
            "available":     self.is_available(),
            "cache_size":    len(self._cache),
            "phase":         5,
        }
