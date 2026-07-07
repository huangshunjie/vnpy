"""
temporal_intelligence_ai/datasource/market_loader.py

市场数据加载器。

从 VeighNa 数据库读取历史 K 线数据，供 CycleEngine 使用。
严格只读历史数据，禁止任何前瞻偏差。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from vnpy.trader.database import get_database
from vnpy.trader.object import BarData
from vnpy.trader.constant import Interval, Exchange


@dataclass
class MarketSeries:
    """单品种历史价格序列容器。"""
    symbol:   str
    exchange: Exchange
    interval: Interval
    bars:     List[BarData] = field(default_factory=list)

    @property
    def close_prices(self) -> List[float]:
        return [b.close_price for b in self.bars]

    @property
    def volumes(self) -> List[float]:
        return [b.volume for b in self.bars]

    @property
    def timestamps(self) -> List[datetime]:
        return [b.datetime for b in self.bars]

    def is_empty(self) -> bool:
        return len(self.bars) == 0


class MarketLoader:
    """
    市场数据加载器。

    封装 VeighNa 数据库查询，提供统一的历史数据接口。
    所有查询均基于 end_dt 截止，确保无前瞻偏差。
    """

    def __init__(self) -> None:
        self._db = get_database()

    def load(
        self,
        symbol:   str,
        exchange: Exchange,
        interval: Interval,
        start_dt: datetime,
        end_dt:   Optional[datetime] = None,
    ) -> MarketSeries:
        """
        加载单品种历史 K 线序列。

        Args:
            symbol:   合约代码
            exchange: 交易所
            interval: K 线周期
            start_dt: 起始时间（含）
            end_dt:   截止时间（含），None 表示当前最新
        """
        if end_dt is None:
            end_dt = datetime.now()

        bars = self._db.load_bar_data(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start=start_dt,
            end=end_dt,
        )

        series = MarketSeries(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            bars=bars,
        )
        return series

    def load_multi(
        self,
        symbols:  List[tuple[str, Exchange]],
        interval: Interval,
        start_dt: datetime,
        end_dt:   Optional[datetime] = None,
    ) -> dict[str, MarketSeries]:
        """
        批量加载多品种历史序列，返回 {symbol: MarketSeries}。
        """
        result: dict[str, MarketSeries] = {}
        for symbol, exchange in symbols:
            series = self.load(symbol, exchange, interval, start_dt, end_dt)
            if not series.is_empty():
                result[symbol] = series
        return result
