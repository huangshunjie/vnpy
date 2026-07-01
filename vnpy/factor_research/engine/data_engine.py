"""
factor_research/engine/data_engine.py

DataEngine — 历史数据加载与缓存层。

职责：
  - 封装对 VeighNa DatabaseManager 的访问，上层无需感知 BarData / Exchange / Interval
  - 将 list[BarData] 转换为 pandas DataFrame（datetime index，OHLCV + vwap 列）
  - 本地 LRU 风格缓存，避免重复 IO
  - 提供数据库概览接口（get_overview），供未来股票池选择使用
  - 严禁直接被 Widget 调用；严禁在此写因子算法

数据流：
  DataEngine.load_bars(vt_symbol, start, end, interval)
    → DatabaseLoader.fetch(...)           # 调用 vnpy get_database()
      → list[BarData]
        → _bars_to_dataframe()            # 转换为 DataFrame
          → _cache[cache_key]             # 写入缓存
            → LoadResult                  # 返回结果描述

DataFrame 列定义（全部 float64）：
  open, high, low, close, volume, turnover, open_interest
  index: datetime（无时区，已 normalize 为 date 级别精度的 DatetimeIndex）
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import TYPE_CHECKING

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.database import get_database
from vnpy.trader.object import BarData

from ..constant import FrequencyType
from ..model import BarOverviewItem, LoadResult

if TYPE_CHECKING:
    import pandas as pd


# --------------------------------------------------------------------------- #
#  FrequencyType → Interval 映射
# --------------------------------------------------------------------------- #

_FREQ_TO_INTERVAL: dict[str, Interval] = {
    FrequencyType.DAILY.value:   Interval.DAILY,
    FrequencyType.WEEKLY.value:  Interval.WEEKLY,
    FrequencyType.MONTHLY.value: Interval.DAILY,   # 月频用日线聚合，后续 resample
}


# --------------------------------------------------------------------------- #
#  DatabaseLoader — VeighNa DatabaseManager 适配器
# --------------------------------------------------------------------------- #

class DatabaseLoader:
    """
    VeighNa DatabaseManager 的薄封装层。

    唯一职责：把 (vt_symbol, start, end, interval) 转换为
    VeighNa 原生接口所需的 (symbol, exchange, interval, start_dt, end_dt)，
    并返回原始 list[BarData]。
    """

    @staticmethod
    def parse_vt_symbol(vt_symbol: str) -> tuple[str, Exchange]:
        """
        解析 vt_symbol 为 (symbol, Exchange)。
        格式：'symbol.EXCHANGE_VALUE'，例如 '000001.SZSE'
        """
        parts = vt_symbol.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError(f"无效的 vt_symbol 格式：{vt_symbol!r}，应为 'symbol.EXCHANGE'")
        symbol, exchange_str = parts
        try:
            exchange = Exchange(exchange_str)
        except ValueError:
            raise ValueError(f"不支持的交易所代码：{exchange_str!r}")
        return symbol, exchange

    def fetch(
        self,
        vt_symbol: str,
        start: date,
        end: date,
        interval: Interval,
    ) -> list[BarData]:
        """
        从 VeighNa DatabaseManager 加载 K 线数据。

        参数：
            vt_symbol : str       合约代码，格式 'symbol.EXCHANGE'
            start     : date      开始日期（含）
            end       : date      结束日期（含）
            interval  : Interval  K 线周期

        返回：
            list[BarData]，按时间升序排列
        """
        symbol, exchange = self.parse_vt_symbol(vt_symbol)

        start_dt = datetime.combine(start, time.min)
        end_dt   = datetime.combine(end,   time.max)

        db = get_database()
        bars: list[BarData] = db.load_bar_data(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start=start_dt,
            end=end_dt,
        )
        return bars

    def get_bar_overviews(self) -> list[BarOverviewItem]:
        """
        返回数据库中所有可用 K 线数据的概览列表。
        供 LeftPanel 未来做股票池选择时展示。
        """
        db = get_database()
        raw = db.get_bar_overview()
        result: list[BarOverviewItem] = []
        for ov in raw:
            vt_symbol = f"{ov.symbol}.{ov.exchange.value}" if ov.exchange else ov.symbol
            result.append(BarOverviewItem(
                vt_symbol=vt_symbol,
                interval=ov.interval.value if ov.interval else "",
                count=ov.count,
                start=ov.start.date() if ov.start else None,
                end=ov.end.date() if ov.end else None,
            ))
        return result


# --------------------------------------------------------------------------- #
#  DataEngine — 数据引擎主体
# --------------------------------------------------------------------------- #

class DataEngine:
    """
    数据引擎。

    管理历史行情数据的加载、格式转换与缓存。
    所有子引擎（IcEngine、QuantileEngine 等）通过 DataEngine 取数，
    不直接调用 DatabaseManager。
    """

    def __init__(self) -> None:
        self._loader: DatabaseLoader = DatabaseLoader()
        # cache_key → DataFrame
        self._cache: dict[str, "pd.DataFrame"] = {}

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def load_bars(
        self,
        vt_symbol: str,
        start: date,
        end: date,
        frequency: str = FrequencyType.DAILY.value,
    ) -> LoadResult:
        """
        加载指定合约的历史 K 线数据。

        参数：
            vt_symbol : str   合约代码，格式 'symbol.EXCHANGE'
            start     : date  开始日期（含）
            end       : date  结束日期（含）
            frequency : str   FrequencyType.value，默认 'daily'

        返回：
            LoadResult — 包含加载状态、条数、cache_key
            实际 DataFrame 通过 get_bars(cache_key) 取用
        """
        interval = _FREQ_TO_INTERVAL.get(frequency, Interval.DAILY)
        cache_key = self._make_key(vt_symbol, interval.value, start, end)

        if cache_key in self._cache:
            df = self._cache[cache_key]
            return LoadResult(
                vt_symbol=vt_symbol,
                interval=interval.value,
                start=start,
                end=end,
                count=len(df),
                success=True,
                cache_key=cache_key,
            )

        try:
            bars = self._loader.fetch(vt_symbol, start, end, interval)
        except Exception as exc:
            return LoadResult(
                vt_symbol=vt_symbol,
                interval=interval.value,
                start=start,
                end=end,
                success=False,
                error=str(exc),
            )

        if not bars:
            return LoadResult(
                vt_symbol=vt_symbol,
                interval=interval.value,
                start=start,
                end=end,
                count=0,
                success=False,
                error=f"数据库中无 {vt_symbol} 的 {frequency} 数据（{start} ~ {end}）",
            )

        df = self._bars_to_dataframe(bars)

        # 月频聚合
        if frequency == FrequencyType.MONTHLY.value:
            df = self._resample_monthly(df)

        self._cache[cache_key] = df

        return LoadResult(
            vt_symbol=vt_symbol,
            interval=interval.value,
            start=start,
            end=end,
            count=len(df),
            success=True,
            cache_key=cache_key,
        )

    def get_bars(self, cache_key: str) -> "pd.DataFrame | None":
        """
        通过 cache_key 取出已加载的 DataFrame。
        返回 None 表示该 key 不存在（未加载或已清除）。
        """
        return self._cache.get(cache_key)

    def get_overview(self) -> list[BarOverviewItem]:
        """返回数据库中所有可用 K 线数据的概览。"""
        return self._loader.get_bar_overviews()

    def clear(self, cache_key: str | None = None) -> None:
        """
        清除缓存。
        cache_key=None 时清除全部；否则只清除指定 key。
        """
        if cache_key is None:
            self._cache.clear()
        else:
            self._cache.pop(cache_key, None)

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _make_key(vt_symbol: str, interval_val: str, start: date, end: date) -> str:
        return f"{vt_symbol}_{interval_val}_{start}_{end}"

    @staticmethod
    def _bars_to_dataframe(bars: list[BarData]) -> "pd.DataFrame":
        """
        将 list[BarData] 转换为 pandas DataFrame。

        index   : DatetimeIndex（naive datetime，无时区）
        columns : open, high, low, close, volume, turnover, open_interest
        """
        import pandas as pd  # 延迟导入，避免强制依赖

        records = [
            {
                "datetime":      bar.datetime,
                "open":          bar.open_price,
                "high":          bar.high_price,
                "low":           bar.low_price,
                "close":         bar.close_price,
                "volume":        bar.volume,
                "turnover":      bar.turnover,
                "open_interest": bar.open_interest,
            }
            for bar in bars
        ]
        df = pd.DataFrame(records)
        df.set_index("datetime", inplace=True)
        df.sort_index(inplace=True)
        # 统一去掉时区，保持 naive DatetimeIndex（Asia/Shanghai 本地时间）
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        return df

    @staticmethod
    def _resample_monthly(df: "pd.DataFrame") -> "pd.DataFrame":
        """
        将日频 DataFrame 聚合为月频。
        OHLC 按标准规则聚合，volume/turnover/open_interest 求和。
        """
        import pandas as pd  # noqa: F401

        agg_rules = {
            "open":          "first",
            "high":          "max",
            "low":           "min",
            "close":         "last",
            "volume":        "sum",
            "turnover":      "sum",
            "open_interest": "last",
        }
        # 只聚合存在的列
        existing = {k: v for k, v in agg_rules.items() if k in df.columns}
        return df.resample("ME").agg(existing).dropna(how="all")

    @staticmethod
    def compute_overview(
        vt_symbol: str,
        interval: str,
        df: "pd.DataFrame",
    ) -> "OverviewSummary":
        """
        对已加载的 DataFrame 计算概览统计摘要。

        参数：
            vt_symbol : str          合约代码
            interval  : str          K 线周期值
            df        : pd.DataFrame DataEngine.get_bars() 返回的 DataFrame

        返回：
            OverviewSummary — 包含合约信息与各列统计
        """
        from ..model import ColumnStat, OverviewSummary

        if df is None or df.empty:
            return OverviewSummary(
                vt_symbol=vt_symbol,
                interval=interval,
                data_start=None,
                data_end=None,
                total_bars=0,
            )

        total = len(df)
        data_start = df.index[0].date()
        data_end   = df.index[-1].date()

        col_order = ["open", "high", "low", "close", "volume", "turnover", "open_interest"]
        stats: list[ColumnStat] = []
        for col in col_order:
            if col not in df.columns:
                continue
            s = df[col]
            missing = int(s.isna().sum())
            valid = s.dropna()
            stats.append(ColumnStat(
                name=col,
                mean=float(valid.mean()) if len(valid) else float("nan"),
                std=float(valid.std())  if len(valid) else float("nan"),
                min_val=float(valid.min()) if len(valid) else float("nan"),
                max_val=float(valid.max()) if len(valid) else float("nan"),
                missing_count=missing,
                missing_pct=missing / total if total else 0.0,
            ))

        return OverviewSummary(
            vt_symbol=vt_symbol,
            interval=interval,
            data_start=data_start,
            data_end=data_end,
            total_bars=total,
            column_stats=stats,
        )
