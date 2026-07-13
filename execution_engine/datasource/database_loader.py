"""
execution_engine/datasource/database_loader.py

DatabaseLoader — VeighNa DatabaseManager 数据接口（Phase 4）。

所有价格 / 订单 / 成交数据必须来自 VeighNa DatabaseManager，
禁止任何外部行情源。

Phase 1 定义了三个 stub 接口；
Phase 4 补全实现，通过 vnpy.trader.database 访问数据库。
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

try:
    from vnpy.trader.database import get_database
    from vnpy.trader.object import BarData, TickData, TradeData, OrderData
    from vnpy.trader.constant import Exchange, Interval
    _HAS_VNPY_DB = True
except ImportError:
    _HAS_VNPY_DB = False


class DatabaseLoader:
    """
    VeighNa DatabaseManager 封装。

    使用方式：
        loader = DatabaseLoader()
        bars   = loader.load_price_data("rb2501", Exchange.SHFE,
                                        Interval.DAILY, start, end)
        orders = loader.load_order_data("rb2501", start, end)
        trades = loader.load_trade_data("rb2501", start, end)
    """

    def __init__(self) -> None:
        self._db = get_database() if _HAS_VNPY_DB else None

    # ------------------------------------------------------------------ #
    #  价格数据
    # ------------------------------------------------------------------ #

    def load_price_data(
        self,
        symbol:    str,
        exchange:  "Exchange",
        interval:  "Interval",
        start:     datetime,
        end:       datetime,
    ) -> list:
        """
        从 VeighNa 数据库加载 K 线数据。

        Parameters
        ----------
        symbol   : 合约代码（不含交易所后缀）
        exchange : Exchange 枚举（如 Exchange.SHFE）
        interval : Interval 枚举（如 Interval.DAILY）
        start    : 开始时间
        end      : 结束时间

        Returns
        -------
        list[BarData]  K 线数据列表（按时间升序）
        """
        if not _HAS_VNPY_DB or self._db is None:
            return []
        try:
            bars = self._db.load_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start=start,
                end=end,
            )
            return bars or []
        except Exception:
            return []

    def load_latest_price(
        self,
        symbol:   str,
        exchange: "Exchange",
    ) -> float:
        """
        获取最新价格（取最近一根日 K 线的收盘价）。

        Returns
        -------
        float  最新收盘价，无数据时返回 0.0
        """
        if not _HAS_VNPY_DB or self._db is None:
            return 0.0
        try:
            end   = datetime.now()
            start = datetime(end.year - 1, end.month, end.day)
            bars  = self._db.load_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.DAILY,
                start=start,
                end=end,
            )
            if bars:
                return float(bars[-1].close_price)
        except Exception:
            pass
        return 0.0

    def load_daily_volume(
        self,
        symbol:   str,
        exchange: "Exchange",
        lookback: int = 20,
    ) -> float:
        """
        计算最近 N 根日 K 线的平均成交量（用于冲击成本模型）。

        Returns
        -------
        float  平均日成交量（手数），无数据时返回 10000.0
        """
        if not _HAS_VNPY_DB or self._db is None:
            return 10000.0
        try:
            end   = datetime.now()
            start = datetime(end.year - 1, end.month, end.day)
            bars  = self._db.load_bar_data(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.DAILY,
                start=start,
                end=end,
            )
            if bars:
                recent = bars[-lookback:]
                volumes = [b.volume for b in recent if b.volume > 0]
                if volumes:
                    return sum(volumes) / len(volumes)
        except Exception:
            pass
        return 10000.0

    # ------------------------------------------------------------------ #
    #  订单数据
    # ------------------------------------------------------------------ #

    def load_order_data(
        self,
        symbol: str,
        start:  datetime,
        end:    datetime,
    ) -> list:
        """
        从数据库加载历史订单记录。

        Returns
        -------
        list[OrderData]  历史订单列表（按时间升序）

        注意：VeighNa 标准 DatabaseManager 不存储 OrderData，
              此接口预留给支持完整订单持久化的扩展数据库适配器。
        """
        if not _HAS_VNPY_DB or self._db is None:
            return []
        try:
            if hasattr(self._db, "load_order_data"):
                return self._db.load_order_data(symbol=symbol, start=start, end=end) or []
        except Exception:
            pass
        return []

    # ------------------------------------------------------------------ #
    #  成交数据
    # ------------------------------------------------------------------ #

    def load_trade_data(
        self,
        symbol: str,
        start:  datetime,
        end:    datetime,
    ) -> list:
        """
        从数据库加载历史成交记录。

        Returns
        -------
        list[TradeData]  历史成交列表（按时间升序）

        注意：同 load_order_data，依赖扩展数据库适配器支持。
        """
        if not _HAS_VNPY_DB or self._db is None:
            return []
        try:
            if hasattr(self._db, "load_trade_data"):
                return self._db.load_trade_data(symbol=symbol, start=start, end=end) or []
        except Exception:
            pass
        return []

    # ------------------------------------------------------------------ #
    #  工具
    # ------------------------------------------------------------------ #

    @property
    def is_available(self) -> bool:
        """数据库连接是否可用。"""
        return _HAS_VNPY_DB and self._db is not None

    def get_available_symbols(
        self,
        exchange: Optional["Exchange"] = None,
    ) -> list[str]:
        """
        获取数据库中已有数据的合约列表（日 K 线）。

        Returns
        -------
        list[str]  合约代码列表（symbol 部分，不含交易所）
        """
        if not _HAS_VNPY_DB or self._db is None:
            return []
        try:
            overviews = self._db.get_bar_overview()
            symbols = []
            for ov in overviews:
                if ov.interval == Interval.DAILY:
                    if exchange is None or ov.exchange == exchange:
                        symbols.append(ov.symbol)
            return symbols
        except Exception:
            return []
