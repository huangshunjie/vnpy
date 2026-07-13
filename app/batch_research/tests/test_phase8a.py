"""
Phase 8 test: ProcessPoolScheduler — Part 1
Interface, state, and no-spawn tests.
"""

import os
import random
from datetime import datetime, timedelta

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy
from vnpy_ctastrategy.backtesting import BacktestingMode

from vnpy.app.batch_research.parameter import BacktestParameter
from vnpy.app.batch_research.task import BacktestTask, BacktestResult, TaskStatus
from vnpy.app.batch_research.scheduler import (
    Scheduler, SerialScheduler, ProcessPoolScheduler,
    SchedulerBase, ScheduleJob, RunSummary,
)


# ================================================================
# Shared helpers
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


def make_parameter() -> BacktestParameter:
    return BacktestParameter(
        start=datetime(2020, 1, 1),
        end=datetime(2021, 6, 30),
        interval=Interval.DAILY,
        capital=1_000_000,
        rate=1e-4,
        slippage=0.02,
        size=1.0,
        pricetick=0.01,
        mode=BacktestingMode.BAR,
    )


def make_job(vt_symbol: str, n_bars: int = 400) -> ScheduleJob:
    sym = vt_symbol.split(".")[0]
    task = BacktestTask(
        vt_symbol=vt_symbol,
        strategy_class=AtrRsiStrategy,
        strategy_setting={"atr_length": 22, "atr_ma_length": 10},
        task_id=f"t_{sym}",
    )
    return ScheduleJob(task=task, bars=make_bars(sym, n_bars))


SYMBOLS = [
    "000001.SZSE", "600519.SSE", "300750.SZSE",
    "000858.SZSE", "600036.SSE", "601318.SSE",
    "600900.SSE",  "000333.SZSE",
]


# ================================================================
# Tests — no process spawn required
# ================================================================

def test_class_hierarchy():
    ps = ProcessPoolScheduler(max_workers=2)
    assert isinstance(ps, SchedulerBase)
    assert isinstance(ps, ProcessPoolScheduler)
    print(f"PASS  class hierarchy  {repr(ps)}")


def test_default_alias_unchanged():
    assert Scheduler is SerialScheduler
    print("PASS  Scheduler alias is still SerialScheduler")


def test_repr_and_job_count():
    ps = ProcessPoolScheduler(max_workers=3)
    assert ps.job_count == 0
    assert "max_workers=3" in repr(ps)
    assert "jobs=0" in repr(ps)

    ps.submit([make_job("000001.SZSE")])
    assert ps.job_count == 1
    assert "jobs=1" in repr(ps)
    print(f"PASS  repr / job_count  {repr(ps)}")


def test_clear_resets_queue():
    ps = ProcessPoolScheduler(max_workers=2)
    ps.submit([make_job("000001.SZSE"), make_job("600519.SSE")])
    assert ps.job_count == 2
    ps.clear()
    assert ps.job_count == 0
    print("PASS  clear() resets queue")


def test_empty_queue_returns_empty():
    ps = ProcessPoolScheduler(max_workers=2)
    results = ps.run(make_parameter(), show_progress=False)
    assert results == []
    print("PASS  empty queue -> []")


def test_max_workers_defaults_to_cpu_count():
    expected = max(1, os.cpu_count() or 1)
    ps = ProcessPoolScheduler()
    assert ps._max_workers == expected
    print(f"PASS  max_workers defaults to cpu_count={expected}")


def test_runsummary_dataclass():
    s = RunSummary(total=10, success=7, skipped=2, failed=1,
                   elapsed_seconds=3.5)
    assert abs(s.success_rate - 70.0) < 0.01
    assert "success_rate=70.0%" in str(s)
    print(f"PASS  RunSummary dataclass  {s}")


def test_process_worker_fn_importable():
    """_process_worker_fn must be importable at top level (pickle requirement)."""
    import importlib
    mod = importlib.import_module("vnpy.app.batch_research.scheduler")
    fn = getattr(mod, "_process_worker_fn", None)
    assert fn is not None and callable(fn)
    print("PASS  _process_worker_fn importable at top level")


if __name__ == "__main__":
    print("=" * 65)
    print("Phase 8 Test Part 1: Interface & state (no spawn)")
    print("=" * 65)

    test_class_hierarchy()
    test_default_alias_unchanged()
    test_repr_and_job_count()
    test_clear_resets_queue()
    test_empty_queue_returns_empty()
    test_max_workers_defaults_to_cpu_count()
    test_runsummary_dataclass()
    test_process_worker_fn_importable()

    print()
    print("=" * 65)
    print("Phase 8 Part 1 ALL TESTS PASSED")
    print("=" * 65)
