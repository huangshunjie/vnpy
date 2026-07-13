"""第三阶段验证：StockPool + CSVLoader"""

import csv
import tempfile
from datetime import date, datetime
from pathlib import Path

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.app.batch_research.datasource.stock_pool import (
    StockPool, StockMeta, PoolType,
    _exchange_of, _to_vt_symbol,
)
from vnpy.app.batch_research.datasource.csv_loader import (
    CSVLoader, CSVLoadConfig, CSVLoadResult,
)


# ================================================================
# 工具：生成临时 CSV 文件
# ================================================================

def make_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


SAMPLE_ROWS = [
    {"datetime": "2023-01-03", "open": "15.10", "high": "15.50", "low": "14.90", "close": "15.30", "volume": "1000000", "turnover": "15300000"},
    {"datetime": "2023-01-04", "open": "15.30", "high": "15.80", "low": "15.20", "close": "15.70", "volume": "1200000", "turnover": "18840000"},
    {"datetime": "2023-01-05", "open": "15.70", "high": "16.00", "low": "15.50", "close": "15.90", "volume": "900000",  "turnover": "14310000"},
]

SAMPLE_FIELDS = ["datetime", "open", "high", "low", "close", "volume", "turnover"]


# ================================================================
# StockPool 测试
# ================================================================

def test_exchange_inference():
    assert _exchange_of("600519") == "SSE"
    assert _exchange_of("688001") == "SSE"
    assert _exchange_of("000001") == "SZSE"
    assert _exchange_of("300750") == "SZSE"
    assert _exchange_of("830799") == "BSE"
    assert _to_vt_symbol("000001") == "000001.SZSE"
    assert _to_vt_symbol("600519") == "600519.SSE"
    print("PASS  exchange inference")


def test_custom_pool():
    pool = StockPool.from_symbols(["000001", "600519", "300750"])
    syms = pool.get_symbols()
    assert "000001.SZSE" in syms
    assert "600519.SSE" in syms
    assert "300750.SZSE" in syms
    assert len(syms) == 3
    print("PASS  StockPool CUSTOM")


def test_vt_symbol_passthrough():
    pool = StockPool.from_symbols(["000001.SZSE", "600519.SSE"])
    assert pool.get_symbols() == ["000001.SZSE", "600519.SSE"]
    print("PASS  StockPool vt_symbol passthrough")


def test_dedup_and_sort():
    pool = StockPool.from_symbols(["600519", "000001", "600519"])
    syms = pool.get_symbols()
    assert len(syms) == 2
    assert syms == sorted(syms)
    print("PASS  StockPool dedup + sort")


def test_st_and_listed_days_filter():
    metas = [
        StockMeta("000001.SZSE", name="平安银行",  listed_date=date(1991, 4, 3),  is_st=False),
        StockMeta("600519.SSE",  name="贵州茅台",  listed_date=date(2001, 8, 27), is_st=False),
        StockMeta("000002.SZSE", name="ST万科",    listed_date=date(1991, 1, 29), is_st=True),
        StockMeta("301500.SZSE", name="新股A",     listed_date=date(2023, 10, 1), is_st=False),
    ]
    pool = StockPool(
        pool_type=PoolType.ALL_A,
        meta_list=metas,
        exclude_st=True,
        min_listed_days=365,
    )
    syms = pool.get_symbols(as_of=date(2024, 1, 1))
    assert "000002.SZSE" not in syms, "ST 未被过滤"
    assert "301500.SZSE" not in syms, "次新股未被过滤"
    assert "000001.SZSE" in syms
    assert "600519.SSE" in syms
    print("PASS  StockPool ST + listed_days filter:", syms)


def test_cyb_star():
    metas = [
        StockMeta("300750.SZSE", name="宁德时代"),
        StockMeta("301500.SZSE", name="某创业板"),
        StockMeta("688001.SSE",  name="华兴源创"),
        StockMeta("000001.SZSE", name="平安银行"),
    ]
    cyb = StockPool(pool_type=PoolType.CYB, meta_list=metas)
    cyb_syms = cyb.get_symbols()
    assert "300750.SZSE" in cyb_syms
    assert "301500.SZSE" in cyb_syms
    assert "688001.SSE" not in cyb_syms
    assert "000001.SZSE" not in cyb_syms

    star = StockPool(pool_type=PoolType.STAR, meta_list=metas)
    star_syms = star.get_symbols()
    assert "688001.SSE" in star_syms
    assert "300750.SZSE" not in star_syms
    print("PASS  StockPool CYB / STAR")


def test_add_remove():
    pool = StockPool.from_symbols(["000001"])
    pool.add_symbols(["600519", "300750"])
    assert pool.size() == 3
    pool.remove_symbol("600519")
    assert pool.size() == 2
    assert "600519.SSE" not in pool.get_symbols()
    print("PASS  StockPool add / remove")


def test_hs300_zz500_factory():
    hs300 = StockPool.from_hs300(["000001", "600519"])
    assert hs300.pool_type == PoolType.HS300
    assert "600519.SSE" in hs300.get_symbols()

    zz500 = StockPool.from_zz500(["300750", "688001"])
    assert zz500.pool_type == PoolType.ZZ500
    assert "688001.SSE" in zz500.get_symbols()
    print("PASS  StockPool HS300 / ZZ500 factory")


# ================================================================
# CSVLoader 测试
# ================================================================

def test_csv_basic_load():
    loader = CSVLoader()
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "000001.csv"
        make_csv(csv_path, SAMPLE_ROWS, SAMPLE_FIELDS)

        config = CSVLoadConfig(
            filepath=csv_path,
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
        )
        result = loader.load(config)

    assert isinstance(result, CSVLoadResult)
    assert result.loaded_count == 3
    assert result.error_rows == 0
    bar0: BarData = result.bars[0]
    assert bar0.symbol == "000001"
    assert bar0.exchange == Exchange.SZSE
    assert bar0.open_price == 15.10
    assert bar0.close_price == 15.30
    assert bar0.volume == 1_000_000
    assert bar0.datetime == datetime(2023, 1, 3, tzinfo=bar0.datetime.tzinfo)
    print("PASS  CSVLoader basic load:", result)


def test_csv_sorted_output():
    """加载结果必须按时间升序排序（即使 CSV 行顺序是倒序）。"""
    reversed_rows = list(reversed(SAMPLE_ROWS))
    loader = CSVLoader()
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "000001.csv"
        make_csv(csv_path, reversed_rows, SAMPLE_FIELDS)
        config = CSVLoadConfig(
            filepath=csv_path,
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
        )
        result = loader.load(config)

    dts = [b.datetime for b in result.bars]
    assert dts == sorted(dts), "BarData 未按时间升序"
    print("PASS  CSVLoader sorted output")


def test_csv_alias_columns():
    """测试列名别名映射：open_price / high_price / vol / amount。"""
    alias_rows = [
        {"trade_date": "2023-01-03", "open_price": "15.10", "high_price": "15.50",
         "low_price": "14.90", "close_price": "15.30", "vol": "1000000", "amount": "15300000"},
    ]
    alias_fields = ["trade_date", "open_price", "high_price", "low_price", "close_price", "vol", "amount"]
    loader = CSVLoader()
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "test.csv"
        make_csv(csv_path, alias_rows, alias_fields)
        config = CSVLoadConfig(
            filepath=csv_path,
            symbol="600519",
            exchange=Exchange.SSE,
            interval=Interval.DAILY,
        )
        result = loader.load(config)

    assert result.loaded_count == 1
    bar = result.bars[0]
    assert bar.open_price == 15.10
    assert bar.volume == 1_000_000
    assert bar.turnover == 15_300_000
    print("PASS  CSVLoader alias columns")


def test_csv_custom_column_map():
    """测试用户自定义列名映射。"""
    custom_rows = [
        {"日期": "2023-01-03", "开盘": "15.10", "最高": "15.50",
         "最低": "14.90", "收盘": "15.30", "成交量": "1000000"},
    ]
    custom_fields = ["日期", "开盘", "最高", "最低", "收盘", "成交量"]
    loader = CSVLoader()
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "test.csv"
        make_csv(csv_path, custom_rows, custom_fields)
        config = CSVLoadConfig(
            filepath=csv_path,
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
            column_map={
                "日期":  "datetime",
                "开盘":  "open",
                "最高":  "high",
                "最低":  "low",
                "收盘":  "close",
                "成交量": "volume",
            },
        )
        result = loader.load(config)

    assert result.loaded_count == 1
    assert result.bars[0].close_price == 15.30
    print("PASS  CSVLoader custom column_map")


def test_csv_bad_rows_skipped():
    """含有错误行时，只跳过错误行，不影响正常行。"""
    bad_rows = [
        {"datetime": "2023-01-03", "open": "15.10", "high": "15.50",
         "low": "14.90", "close": "15.30", "volume": "1000000"},
        {"datetime": "NOT_A_DATE", "open": "15.10", "high": "15.50",
         "low": "14.90", "close": "15.30", "volume": "1000000"},
        {"datetime": "2023-01-05", "open": "15.70", "high": "16.00",
         "low": "15.50", "close": "-1.0",  "volume": "900000"},   # close <= 0
        {"datetime": "2023-01-06", "open": "15.90", "high": "16.10",
         "low": "15.80", "close": "16.00", "volume": "800000"},
    ]
    fields = ["datetime", "open", "high", "low", "close", "volume"]
    loader = CSVLoader()
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "test.csv"
        make_csv(csv_path, bad_rows, fields)
        config = CSVLoadConfig(
            filepath=csv_path,
            symbol="000001",
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
        )
        result = loader.load(config)

    assert result.loaded_count == 2, f"期望2条，实际{result.loaded_count}"
    assert result.error_rows == 2,   f"期望2条错误，实际{result.error_rows}"
    print("PASS  CSVLoader bad rows skipped:", result)


def test_csv_load_directory():
    """测试批量目录加载，文件名自动解析为 symbol。"""
    loader = CSVLoader()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for sym in ["000001", "600519", "300750"]:
            make_csv(tmp_path / f"{sym}.csv", SAMPLE_ROWS, SAMPLE_FIELDS)

        results = loader.load_directory(
            directory=tmp_path,
            exchange=Exchange.SZSE,
            interval=Interval.DAILY,
        )

    assert len(results) == 3
    symbols = {r.symbol for r in results}
    assert symbols == {"000001", "600519", "300750"}
    for r in results:
        assert r.loaded_count == 3
    print("PASS  CSVLoader load_directory:", [r.symbol for r in results])


def test_csv_filename_with_exchange():
    """文件名格式 000001.SZSE.csv 时，交易所从文件名解析。"""
    loader = CSVLoader()
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "600519.SSE.csv"
        make_csv(csv_path, SAMPLE_ROWS, SAMPLE_FIELDS)
        results = loader.load_directory(
            directory=Path(tmp),
            exchange=Exchange.SZSE,   # 默认深交所，但文件名指定了SSE
        )

    assert len(results) == 1
    assert results[0].symbol == "600519"
    assert results[0].exchange == Exchange.SSE
    print("PASS  CSVLoader filename with exchange suffix")


def test_csv_file_not_found():
    loader = CSVLoader()
    config = CSVLoadConfig(
        filepath=Path("nonexistent_path/missing.csv"),
        symbol="000001",
        exchange=Exchange.SZSE,
        interval=Interval.DAILY,
    )
    try:
        loader.load(config)
        print("FAIL  should have raised FileNotFoundError")
    except FileNotFoundError as e:
        print("PASS  CSVLoader FileNotFoundError:", e)


# ================================================================
# 主入口
# ================================================================

if __name__ == "__main__":
    print("=" * 55)
    print("Phase 3 Test: StockPool")
    print("=" * 55)
    test_exchange_inference()
    test_custom_pool()
    test_vt_symbol_passthrough()
    test_dedup_and_sort()
    test_st_and_listed_days_filter()
    test_cyb_star()
    test_add_remove()
    test_hs300_zz500_factory()

    print()
    print("=" * 55)
    print("Phase 3 Test: CSVLoader")
    print("=" * 55)
    test_csv_basic_load()
    test_csv_sorted_output()
    test_csv_alias_columns()
    test_csv_custom_column_map()
    test_csv_bad_rows_skipped()
    test_csv_load_directory()
    test_csv_filename_with_exchange()
    test_csv_file_not_found()

    print()
    print("=" * 55)
    print("Phase 3 ALL TESTS PASSED")
    print("=" * 55)
