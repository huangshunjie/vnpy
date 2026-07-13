"""Phase 6 test: BatchBacktestingEngine (end-to-end pipeline)"""

import random
import tempfile
import csv
from datetime import datetime, timedelta
from pathlib import Path

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy_ctastrategy.backtesting import BacktestingMode
from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy

from vnpy.app.batch_research.batch_engine import BatchBacktestingEngine
from vnpy.app.batch_research.datasource.stock_pool import StockPool, PoolType
from vnpy.app.batch_research.task import TaskStatus
from vnpy.app.batch_research.scheduler import SerialScheduler


# ================================================================
# Helpers
# ================================================================

def make_bars(symbol: str = "000001", n: int = 400) -> list[BarData]:
    rng = random.Random(hash(symbol) & 0xFFFF)
    bars: list[BarData] = []
    price = 10.0
    dt = datetime(2020, 1, 2)
    for _ in range(n):
        while dt.weekday() >= 5:
            dt += timedelta(days=1)
        chg = rng.gauss(0, 0.015)
        o = price
        c = round(max(0.1, price * (1 + chg)), 2)
        h = round(max(o, c) * (1 + abs(rng.gauss(0, 0.004))), 2)
        l = round(min(o, c) * (1 - abs(rng.gauss(0, 0.004))), 2)
        bars.append(BarData(
            gateway_name="CSV", symbol=symbol,
            exchange=Exchange.SZSE, datetime=dt,
            interval=Interval.DAILY,
            open_price=o, high_price=h, low_price=l, close_price=c,
            volume=float(rng.randint(500_000, 3_000_000)),
        ))
        price = c
        dt += timedelta(days=1)
    return bars


def make_csv_dir(symbols: list[str], n: int = 400) -> tempfile.TemporaryDirectory:
    """Write CSV files for each symbol into a temp directory."""
    tmp = tempfile.TemporaryDirectory()
    for sym in symbols:
        bars = make_bars(sym, n)
        path = Path(tmp.name) / f"{sym}.csv"
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["datetime", "open", "high", "low", "close", "volume"])
            for b in bars:
                writer.writerow([
                    b.datetime.strftime("%Y-%m-%d"),
                    b.open_price, b.high_price,
                    b.low_price, b.close_price, int(b.volume),
                ])
    return tmp


SYMBOLS = ["000001", "600519", "300750", "000858", "600036"]
VT_SYMBOLS = ["000001.SZSE", "600519.SSE", "300750.SZSE",
              "000858.SZSE", "600036.SSE"]


def base_engine(symbols=None) -> BatchBacktestingEngine:
    """Return a configured engine with set_parameters and set_stock_pool called."""
    eng = BatchBacktestingEngine()
    eng.set_parameters(
        strategy_class=AtrRsiStrategy,
        start=datetime(2020, 1, 1),
        end=datetime(2021, 6, 30),
        capital=1_000_000,
        rate=1e-4,
        slippage=0.02,
        size=1.0,
        pricetick=0.01,
        strategy_setting={"atr_length": 22, "atr_ma_length": 10},
    )
    eng.set_stock_pool(symbols or VT_SYMBOLS)
    return eng


# ================================================================
# Tests
# ================================================================

def test_engine_repr():
    eng = BatchBacktestingEngine()
    r = repr(eng)
    assert "BatchBacktestingEngine" in r
    print(f"PASS  repr: {r}")


def test_validate_config_missing_parameters():
    eng = BatchBacktestingEngine()
    try:
        eng.run_backtesting(show_progress=False)
        assert False, "should have raised"
    except RuntimeError as e:
        assert "set_parameters" in str(e)
    print("PASS  RuntimeError when parameters not set")


def test_validate_config_missing_pool():
    eng = BatchBacktestingEngine()
    eng.set_parameters(
        strategy_class=AtrRsiStrategy,
        start=datetime(2020, 1, 1),
        end=datetime(2021, 6, 30),
    )
    try:
        eng.run_backtesting(show_progress=False)
        assert False, "should have raised"
    except RuntimeError as e:
        assert "set_stock_pool" in str(e)
    print("PASS  RuntimeError when stock pool not set")


def test_set_bars_inject():
    """set_bars() injects bars; run_backtesting uses them."""
    eng = base_engine(["000001.SZSE"])
    eng.set_bars("000001.SZSE", make_bars("000001", 400))
    results = eng.run_backtesting(show_progress=False)

    assert len(results) == 1
    r = results[0]
    assert r.vt_symbol == "000001.SZSE"
    assert r.status == TaskStatus.SUCCESS
    print(f"PASS  set_bars inject  total_return={r.total_return:.2f}%")


def test_load_bars_from_directory():
    """load_bars_from_directory() loads CSV files; pipeline runs end-to-end."""
    syms = ["000001", "600519", "300750"]
    with make_csv_dir(syms) as tmpdir:
        eng = BatchBacktestingEngine()
        eng.set_parameters(
            strategy_class=AtrRsiStrategy,
            start=datetime(2020, 1, 1),
            end=datetime(2021, 6, 30),
            capital=1_000_000,
            rate=1e-4,
            slippage=0.02,
            size=1.0,
            pricetick=0.01,
        )
        eng.set_stock_pool(["000001.SZSE", "600519.SSE", "300750.SZSE"])
        eng.load_bars_from_directory(
            directory=Path(tmpdir),
            exchange=Exchange.SZSE,
        )
        results = eng.run_backtesting(show_progress=False)

    assert len(results) == 3
    vt_set = {r.vt_symbol for r in results}
    assert "000001.SZSE" in vt_set
    print(f"PASS  load_bars_from_directory  {len(results)} results")


def test_load_bars_from_file():
    """load_bars_from_file() loads one CSV; that symbol runs from CSV data."""
    with make_csv_dir(["000001"]) as tmpdir:
        eng = base_engine(["000001.SZSE"])
        eng.load_bars_from_file(
            filepath=Path(tmpdir) / "000001.csv",
            vt_symbol="000001.SZSE",
        )
        results = eng.run_backtesting(show_progress=False)

    assert len(results) == 1
    assert results[0].status == TaskStatus.SUCCESS
    print("PASS  load_bars_from_file")


def test_empty_pool_returns_empty():
    """Empty stock pool after filter returns [] without error."""
    from vnpy.app.batch_research.datasource.stock_pool import StockMeta
    from datetime import date

    # All symbols are ST -> filtered out
    metas = [
        StockMeta("000001.SZSE", is_st=True),
        StockMeta("600519.SSE", is_st=True),
    ]
    pool = StockPool(
        pool_type=PoolType.ALL_A,
        meta_list=metas,
        exclude_st=True,
    )
    eng = BatchBacktestingEngine()
    eng.set_parameters(
        strategy_class=AtrRsiStrategy,
        start=datetime(2020, 1, 1),
        end=datetime(2021, 6, 30),
    )
    eng.set_stock_pool(pool)
    results = eng.run_backtesting(show_progress=False)

    assert results == []
    print("PASS  empty pool after filter -> []")


def test_results_property():
    """engine.results returns same list as run_backtesting() return value."""
    eng = base_engine(["000001.SZSE"])
    eng.set_bars("000001.SZSE", make_bars("000001"))
    returned = eng.run_backtesting(show_progress=False)
    assert eng.results is returned
    print("PASS  engine.results property")


def test_summary_populated():
    """engine.summary is populated after run_backtesting()."""
    eng = base_engine(["000001.SZSE", "600519.SSE"])
    eng.set_bars("000001.SZSE", make_bars("000001"))
    eng.set_bars("600519.SSE",  make_bars("600519"))
    eng.run_backtesting(show_progress=False)

    s = eng.summary
    assert s is not None
    assert s.total == 2
    assert s.success + s.skipped + s.failed == 2
    assert s.elapsed_seconds > 0
    print(f"PASS  engine.summary: {s}")


def test_get_result_dataframe():
    """get_result_dataframe() returns a DataFrame sorted by sharpe_ratio."""
    import pandas as pd
    syms = ["000001.SZSE", "600519.SSE", "300750.SZSE"]
    eng = base_engine(syms)
    for vt in syms:
        eng.set_bars(vt, make_bars(vt.split(".")[0]))

    eng.run_backtesting(show_progress=False)
    df = eng.get_result_dataframe()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "vt_symbol" in df.columns
    assert "sharpe_ratio" in df.columns
    assert "total_return" in df.columns
    sharpes = df["sharpe_ratio"].tolist()
    assert sharpes == sorted(sharpes, reverse=True), "Not sorted by sharpe_ratio desc"
    print(f"PASS  get_result_dataframe  shape={df.shape}")
    print(df[["vt_symbol", "total_return", "sharpe_ratio"]].to_string(index=False))


def test_get_results_by_status():
    """successful_results / failed_results / skipped_results filter correctly."""
    syms = ["000001.SZSE", "600519.SSE"]
    eng = base_engine(syms + ["000001.INVALID"])
    for vt in syms:
        eng.set_bars(vt, make_bars(vt.split(".")[0]))
    # INVALID stays without bars -> will FAIL at set_parameters
    eng.set_bars("000001.INVALID", make_bars("000001", 100))

    eng.run_backtesting(show_progress=False)

    assert len(eng.failed_results) >= 1
    total = (len(eng.successful_results)
             + len(eng.failed_results)
             + len(eng.skipped_results))
    assert total == len(eng.results)
    print(f"PASS  results by status: "
          f"success={len(eng.successful_results)} "
          f"failed={len(eng.failed_results)} "
          f"skipped={len(eng.skipped_results)}")


def test_on_task_done_callback():
    """on_task_done callback fires for every symbol."""
    done_calls: list[str] = []

    def on_done(result) -> None:
        done_calls.append(result.vt_symbol)

    syms = ["000001.SZSE", "600519.SSE", "300750.SZSE"]
    eng = base_engine(syms)
    for vt in syms:
        eng.set_bars(vt, make_bars(vt.split(".")[0]))

    eng.run_backtesting(show_progress=False, on_task_done=on_done)

    assert len(done_calls) == 3
    assert set(done_calls) == set(syms)
    print(f"PASS  on_task_done callback  fired={len(done_calls)}x")


def test_custom_scheduler_injection():
    """A custom scheduler passed to __init__ is used instead of default."""
    custom = SerialScheduler()
    eng = BatchBacktestingEngine(scheduler=custom)
    eng.set_parameters(
        strategy_class=AtrRsiStrategy,
        start=datetime(2020, 1, 1),
        end=datetime(2021, 6, 30),
    )
    eng.set_stock_pool(["000001.SZSE"])
    eng.set_bars("000001.SZSE", make_bars("000001"))
    eng.run_backtesting(show_progress=False)

    assert eng._scheduler is custom
    assert custom.summary.total == 1
    print("PASS  custom scheduler injection")


def test_db_mode_no_bars_attached():
    """
    When no bars are pre-loaded for a symbol, Worker calls engine.load_data().
    With no DB configured the engine returns empty data -> SKIPPED (not FAILED).
    """
    eng = base_engine(["000001.SZSE"])
    # deliberately do NOT call set_bars or load_bars_from_directory
    results = eng.run_backtesting(show_progress=False)

    assert len(results) == 1
    assert results[0].status == TaskStatus.SKIPPED
    print("PASS  DB mode (no bars pre-loaded) -> SKIPPED")


def test_engine_full_pipeline_five_symbols():
    """End-to-end smoke test: 5 symbols, CSV inject, get_result_dataframe."""
    import pandas as pd
    eng = base_engine(VT_SYMBOLS)
    for vt in VT_SYMBOLS:
        eng.set_bars(vt, make_bars(vt.split(".")[0]))

    results = eng.run_backtesting(show_progress=True)

    assert len(results) == 5
    df = eng.get_result_dataframe()
    assert len(df) == 5

    print(f"\nPASS  full pipeline 5 symbols")
    print(df[["vt_symbol", "total_return", "annual_return",
              "sharpe_ratio", "max_ddpercent", "total_trade_count"]].to_string(index=False))
    print(f"Summary: {eng.summary}")


# ================================================================
# Entry point
# ================================================================

if __name__ == "__main__":
    print("=" * 65)
    print("Phase 6 Test: BatchBacktestingEngine")
    print("=" * 65)

    test_engine_repr()
    test_validate_config_missing_parameters()
    test_validate_config_missing_pool()
    test_set_bars_inject()
    test_load_bars_from_directory()
    test_load_bars_from_file()
    test_empty_pool_returns_empty()
    test_results_property()
    test_summary_populated()
    test_get_result_dataframe()
    test_get_results_by_status()
    test_on_task_done_callback()
    test_custom_scheduler_injection()
    test_db_mode_no_bars_attached()
    test_engine_full_pipeline_five_symbols()

    print()
    print("=" * 65)
    print("Phase 6 ALL TESTS PASSED")
    print("=" * 65)
