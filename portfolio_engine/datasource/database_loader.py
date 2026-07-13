"""
portfolio_engine/datasource/database_loader.py

DatabaseLoader — Portfolio Engine 唯一数据入口。

职责：
  - 封装 VeighNa DatabaseManager.load_bar_data()
  - 把 list[BarData] 转换为 pandas DataFrame（OHLCV + datetime index）
  - 提供合约概览查询（可用合约列表）
  - 严禁：外部数据源、直接写数据库、连接行情接口

Phase 1：接口骨架，_to_dataframe() 已实现（无业务依赖）。
         load() 骨架已就绪，Phase 2 直接调用。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

import pandas as pd

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database

if TYPE_CHECKING:
    from vnpy.trader.object import BarData

# VeighNa Interval 字符串 → Interval 枚举
_INTERVAL_MAP: dict[str, Interval] = {
    "daily":  Interval.DAILY,
    "d":      Interval.DAILY,
    "60min":  Interval.HOUR,
    "1h":     Interval.HOUR,
    "15min":  Interval.MINUTE_15 if hasattr(Interval, "MINUTE_15") else Interval.MINUTE,
    "1min":   Interval.MINUTE,
    "m":      Interval.MINUTE,
}


class DatabaseLoader:
    """
    VeighNa DatabaseManager 的轻量封装。

    所有子引擎通过本类获取 OHLCV 数据，不直接调用 get_database()。
    """

    def __init__(self) -> None:
        self._db = get_database()

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def load(
        self,
        vt_symbol: str,
        start: date,
        end: date,
        interval: str = "daily",
    ) -> pd.DataFrame:
        """
        加载单合约 OHLCV 数据，返回 DataFrame。

        Parameters
        ----------
        vt_symbol : str
            VeighNa 合约代码，如 "000001.SZSE"
        start / end : date
            闭区间，[start, end]
        interval : str
            "daily" / "60min" / "15min" / "1min"

        Returns
        -------
        pd.DataFrame
            columns: open, high, low, close, volume
            index:   datetime（tz-naive）
            空 DataFrame 表示数据库中无对应数据
        """
        symbol, exchange_str = self._parse_vt_symbol(vt_symbol)
        exchange  = self._parse_exchange(exchange_str)
        iv        = self._parse_interval(interval)

        start_dt = datetime.combine(start, datetime.min.time())
        end_dt   = datetime.combine(end,   datetime.max.time())

        bars: list[BarData] = self._db.load_bar_data(
            symbol   = symbol,
            exchange = exchange,
            interval = iv,
            start    = start_dt,
            end      = end_dt,
        )

        return self._to_dataframe(bars)

    def get_bar_overview(self) -> list[dict]:
        """
        返回数据库中所有合约的概览列表（用于左侧面板下拉）。

        Returns
        -------
        list[dict]
            每项：{"vt_symbol": str, "interval": str,
                   "start": date, "end": date, "count": int}
        """
        overviews = self._db.get_bar_overview()
        result: list[dict] = []
        for ov in overviews:
            result.append({
                "vt_symbol": f"{ov.symbol}.{ov.exchange.value}",
                "interval":  ov.interval.value,
                "start":     ov.start.date() if ov.start else None,
                "end":       ov.end.date()   if ov.end   else None,
                "count":     ov.count,
            })
        return result

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _to_dataframe(bars: "list[BarData]") -> pd.DataFrame:
        """Convert list[BarData] → OHLCV DataFrame (datetime index)."""
        if not bars:
            return pd.DataFrame(
                columns=["open", "high", "low", "close", "volume"]
            )
        rows = [
            {
                "datetime": b.datetime,
                "open":     b.open_price,
                "high":     b.high_price,
                "low":      b.low_price,
                "close":    b.close_price,
                "volume":   b.volume,
            }
            for b in bars
        ]
        df = pd.DataFrame(rows)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.set_index("datetime").sort_index()
        df.index = df.index.tz_localize(None)   # tz-naive
        return df

    @staticmethod
    def _parse_vt_symbol(vt_symbol: str) -> tuple[str, str]:
        """"000001.SZSE" → ("000001", "SZSE")"""
        parts = vt_symbol.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid vt_symbol: {vt_symbol!r}")
        return parts[0], parts[1]

    @staticmethod
    def _parse_exchange(exchange_str: str) -> Exchange:
        try:
            return Exchange(exchange_str)
        except ValueError:
            raise ValueError(f"Unknown exchange: {exchange_str!r}")

    @staticmethod
    def _parse_interval(interval_str: str) -> Interval:
        iv = _INTERVAL_MAP.get(interval_str.lower())
        if iv is None:
            raise ValueError(f"Unsupported interval: {interval_str!r}")
        return iv
