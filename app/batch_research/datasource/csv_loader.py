"""
CSVLoader

从 CSV 文件读取 A 股历史行情数据，转换为 VeighNa BarData 对象。

支持列名映射（大小写不敏感），适配以下常见数据源格式：
  - 通达信导出 CSV
  - 聚宽 (JoinQuant) 导出 CSV
  - Tushare 导出 CSV
  - 自定义列名（通过 column_map 覆盖）

必需列（至少需要其中一种时间列 + OHLCV）：
  datetime / date / trade_date / time
  open  / open_price
  high  / high_price
  low   / low_price
  close / close_price
  volume

可选列：
  turnover / amount / money
  open_interest
"""

import csv
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData


# 默认时区：上海（A股）
_DEFAULT_TZ = ZoneInfo("Asia/Shanghai")

# 内置列名别名表（统一映射到标准键）
_DEFAULT_COLUMN_MAP: dict[str, str] = {
    # 时间
    "date":         "datetime",
    "trade_date":   "datetime",
    "time":         "datetime",
    "candle_begin_time": "datetime",
    # OHLCV
    "open_price":   "open",
    "high_price":   "high",
    "low_price":    "low",
    "close_price":  "close",
    "vol":          "volume",
    "vol_":         "volume",
    "成交量":        "volume",
    # 成交额
    "amount":       "turnover",
    "money":        "turnover",
    "turnover":     "turnover",
    "成交额":        "turnover",
}

# 常见时间格式（按优先级尝试）
_DATETIME_FORMATS: list[str] = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y%m%d %H:%M:%S",
    "%Y%m%d %H:%M",
    "%Y%m%d",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d",
]


def _parse_datetime(raw: str) -> datetime:
    """尝试所有预设格式解析时间字符串，解析失败抛出 ValueError。"""
    raw = raw.strip()
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析时间字符串：{raw!r}")


def _normalize_header(header: list[str], column_map: dict[str, str]) -> dict[str, str]:
    """
    将 CSV 原始表头映射为标准列名。
    先查 column_map（用户覆盖），再查内置别名表，最后直接使用原名（小写）。

    :return: {标准键: 原始列名} 的映射字典。
    """
    merged_map = {**_DEFAULT_COLUMN_MAP, **{k.lower(): v for k, v in column_map.items()}}
    result: dict[str, str] = {}
    for col in header:
        normalized = col.strip().lower()
        standard = merged_map.get(normalized, normalized)
        result[standard] = col      # 标准键 → 原始列名
    return result


@dataclass
class CSVLoadConfig:
    """
    CSV 加载配置。

    :param filepath:    CSV 文件路径。
    :param symbol:      股票代码，例如 '000001'。
    :param exchange:    交易所枚举，例如 Exchange.SZSE。
    :param interval:    K 线周期，例如 Interval.DAILY。
    :param tz:          时区，默认 Asia/Shanghai。
    :param encoding:    文件编码，默认 utf-8-sig（兼容 BOM）。
    :param delimiter:   分隔符，默认逗号。
    :param column_map:  列名覆盖映射，{原始列名（小写）: 标准键}。
    :param datetime_col: 时间列的标准键名，默认 'datetime'。
    :param skiprows:    跳过开头的非数据行数（不含表头行），默认 0。
    """
    filepath: Path
    symbol: str
    exchange: Exchange
    interval: Interval = Interval.DAILY
    tz: ZoneInfo = field(default_factory=lambda: _DEFAULT_TZ)
    encoding: str = "utf-8-sig"
    delimiter: str = ","
    column_map: dict[str, str] = field(default_factory=dict)
    datetime_col: str = "datetime"
    skiprows: int = 0


@dataclass
class CSVLoadResult:
    """CSV 加载结果摘要。"""
    filepath: Path
    symbol: str
    exchange: Exchange
    bars: list[BarData]
    total_rows: int = 0
    skipped_rows: int = 0
    error_rows: int = 0

    @property
    def loaded_count(self) -> int:
        return len(self.bars)

    def __repr__(self) -> str:
        return (
            f"CSVLoadResult({self.symbol}.{self.exchange.value}: "
            f"loaded={self.loaded_count}, "
            f"skipped={self.skipped_rows}, "
            f"errors={self.error_rows})"
        )


class CSVLoader:
    """
    CSV 历史行情加载器。

    将 CSV 文件转换为 VeighNa BarData 列表，
    可直接传入 BacktestingEngine 或写入数据库。

    用法示例::

        loader = CSVLoader()

        # 单文件加载
        result = loader.load(CSVLoadConfig(
            filepath=Path("data/000001.csv"),
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
        ))
        bars: list[BarData] = result.bars

        # 批量加载目录下所有 CSV
        results = loader.load_directory(
            directory=Path("data/"),
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
        )
    """

    def load(self, config: CSVLoadConfig) -> CSVLoadResult:
        """
        加载单个 CSV 文件。

        :param config: 加载配置。
        :return: CSVLoadResult，包含 BarData 列表和加载统计。
        :raises FileNotFoundError: 文件不存在时抛出。
        """
        filepath = Path(config.filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"CSV 文件不存在：{filepath}")

        bars: list[BarData] = []
        total_rows = 0
        skipped_rows = 0
        error_rows = 0

        with open(filepath, encoding=config.encoding, newline="") as f:
            reader = csv.DictReader(f, delimiter=config.delimiter)

            if reader.fieldnames is None:
                return CSVLoadResult(
                    filepath=filepath,
                    symbol=config.symbol,
                    exchange=config.exchange,
                    bars=[],
                )

            col_map = _normalize_header(list(reader.fieldnames), config.column_map)

            for row_idx, raw_row in enumerate(reader):
                total_rows += 1

                # 跳过指定行数（紧跟表头之后的非数据行）
                if row_idx < config.skiprows:
                    skipped_rows += 1
                    continue

                # 将原始列名映射为标准键
                row = {std_key: raw_row[orig_col] for std_key, orig_col in col_map.items()}

                bar = self._parse_row(row, config)
                if bar is None:
                    error_rows += 1
                    continue

                bars.append(bar)

        # 按时间升序排序，保证回测引擎收到的数据有序
        bars.sort(key=lambda b: b.datetime)

        return CSVLoadResult(
            filepath=filepath,
            symbol=config.symbol,
            exchange=config.exchange,
            bars=bars,
            total_rows=total_rows,
            skipped_rows=skipped_rows,
            error_rows=error_rows,
        )

    def load_directory(
        self,
        directory: Path,
        exchange: Exchange,
        interval: Interval = Interval.DAILY,
        encoding: str = "utf-8-sig",
        column_map: dict[str, str] | None = None,
        glob_pattern: str = "*.csv",
    ) -> list[CSVLoadResult]:
        """
        批量加载目录下所有匹配的 CSV 文件。

        文件名规则：{symbol}.csv，例如 000001.csv。
        文件名中若包含交易所后缀（000001.SZSE.csv）也可正确解析。

        :param directory:    数据目录。
        :param exchange:     默认交易所（文件名中无交易所后缀时使用）。
        :param interval:     K 线周期。
        :param encoding:     文件编码。
        :param column_map:   列名覆盖映射。
        :param glob_pattern: 文件匹配模式，默认 *.csv。
        :return: 每个文件对应一个 CSVLoadResult 的列表。
        """
        directory = Path(directory)
        if not directory.is_dir():
            raise NotADirectoryError(f"路径不是目录：{directory}")

        results: list[CSVLoadResult] = []
        for csv_file in sorted(directory.glob(glob_pattern)):
            symbol, file_exchange = self._symbol_from_filename(csv_file.stem, exchange)
            config = CSVLoadConfig(
                filepath=csv_file,
                symbol=symbol,
                exchange=file_exchange,
                interval=interval,
                encoding=encoding,
                column_map=column_map or {},
            )
            result = self.load(config)
            results.append(result)

        return results

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_row(row: dict[str, Any], config: CSVLoadConfig) -> BarData | None:
        """
        将单行字典解析为 BarData。
        任何字段解析失败均返回 None（由调用方统计 error_rows）。
        """
        try:
            raw_dt = row.get(config.datetime_col, "").strip()
            if not raw_dt:
                return None
            dt = _parse_datetime(raw_dt)
            # 附加时区信息（不转换，只标注）
            dt = dt.replace(tzinfo=config.tz)

            open_price  = float(row.get("open",  0) or 0)
            high_price  = float(row.get("high",  0) or 0)
            low_price   = float(row.get("low",   0) or 0)
            close_price = float(row.get("close", 0) or 0)
            volume      = float(row.get("volume", 0) or 0)
            turnover    = float(row.get("turnover", 0) or 0)

            # 基本数据质量检查
            if close_price <= 0 or volume < 0:
                return None

            bar = BarData(
                gateway_name="CSV",
                symbol=config.symbol,
                exchange=config.exchange,
                datetime=dt,
                interval=config.interval,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                turnover=turnover,
            )
            return bar

        except (ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def _symbol_from_filename(stem: str, default_exchange: Exchange) -> tuple[str, Exchange]:
        """
        从文件名主干提取股票代码和交易所。

        支持格式：
          - "000001"          → ("000001", default_exchange)
          - "000001.SZSE"     → ("000001", Exchange.SZSE)
        """
        if "." in stem:
            parts = stem.split(".", 1)
            symbol = parts[0]
            try:
                exch = Exchange(parts[1].upper())
            except ValueError:
                exch = default_exchange
            return symbol, exch
        return stem, default_exchange
