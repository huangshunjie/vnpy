"""
Phase 8 test: ProcessPoolScheduler — Part 2
Tests that spawn worker processes.
MUST be run as a top-level script (guarded by __main__).
"""

import os
import random
import time
from datetime import datetime, timedelta

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy
from vnpy_ctastrategy.backtesting import BacktestingMode

from vnpy.app.batch_research.parameter import BacktestParameter
from vnpy.app.batch_research.task import BacktestTask, BacktestResult, TaskStatus
from vnpy.app.batch_research.scheduler import (
    SerialScheduler, ProcessPoolScheduler, ScheduleJob,
)
from vnpy.app.batch_research.batch_engine import BatchBacktestingEngine


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
# Tests (spawn processes — only safe under __main__)
# ================================================================

def test_single_job():
    ps = ProcessPoolScheduler(max_workers=1)
    ps.submit([make_job("000001.SZSE")])
    results = ps.run(make_parameter(), show_progress=False)

    assert len(results) == 1
    r = results[0]
    assert r.vt_symbol == "000001.SZSE"
    assert r.status in (TaskStatus.SUCCESS, TaskStatus.SKIPPED)
    print(f"PASS  single job  status={r.status.value}")


def test_multiple_jobs_order_preserved():
    """Results must be in submission order regardless of completion order."""
    ps = ProcessPoolScheduler(max_workers=4)
    jobs = [make_job(sym) for sym in SYMBOLS]
    ps.submit(jobs)
    results = ps.run(make_parameter(), show_progress=False)

    assert len(results) == len(SYMBOLS)
    for i, (res, sym) in enumerate(zip(results, SYMBOLS)):
        assert res.vt_symbol == sym, (
            f"Position {i}: expected {sym}, got {res.vt_symbol}"
        )
    print(f"PASS  results order preserved ({len(SYMBOLS)} symbols)")


def test_runsummary_counts():
    jobs = [make_job(sym) for sym in SYMBOLS[:5]]

    failed_task = BacktestTask(
        vt_symbol="000001.INVALID",
        strategy_class=AtrRsiStrategy,
        strategy_setting={},
        task_id="t_fail",
    )
    jobs.append(ScheduleJob(task=failed_task, bars=make_bars(n=100)))

    skipped_task = BacktestTask(
        vt_symbol="600000.SSE",
        strategy_class=AtrRsiStrategy,
        strategy_setting={},
        task_id="t_skip",
    )
    jobs.append(ScheduleJob(task=skipped_task, bars=[]))

    ps = ProcessPoolScheduler(max_workers=4)
    ps.submit(jobs)
    ps.run(make_parameter(), show_progress=False)

    s = ps.summary
    assert s.total == len(jobs),  f"total mismatch: {s.total}"
    assert s.failed >= 1,         f"expected >=1 failed: {s.failed}"
    assert s.skipped >= 1,        f"expected >=1 skipped: {s.skipped}"
    assert s.success + s.skipped + s.failed == s.total
    assert s.elapsed_seconds > 0
    assert s.start_time is not None and s.end_time is not None
    assert 0.0 <= s.success_rate <= 100.0
    print(f"PASS  RunSummary: {s}")


def test_on_task_done_callback():
    collected: list[BacktestResult] = []

    def on_done(result: BacktestResult) -> None:
        collected.append(result)

    ps = ProcessPoolScheduler(max_workers=4)
    ps.submit([make_job(sym) for sym in SYMBOLS[:4]])
    results = ps.run(make_parameter(), on_task_done=on_done, show_progress=False)

    assert len(collected) == 4
    assert {r.vt_symbol for r in collected} == {r.vt_symbol for r in results}
    print(f"PASS  on_task_done callback  fired={len(collected)}x")


def test_on_task_start_callback():
    started: list[str] = []

    def on_start(task: BacktestTask) -> None:
        assert task.status == TaskStatus.RUNNING
        started.append(task.vt_symbol)

    ps = ProcessPoolScheduler(max_workers=4)
    ps.submit([make_job(sym) for sym in SYMBOLS[:4]])
    ps.run(make_parameter(), on_task_start=on_start, show_progress=False)

    assert set(started) == set(SYMBOLS[:4])
    print(f"PASS  on_task_start callback  fired={len(started)}x")


def test_callback_exception_does_not_abort():
    call_count = 0

    def bad_callback(result: BacktestResult) -> None:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("callback exploded")

    ps = ProcessPoolScheduler(max_workers=4)
    ps.submit([make_job(sym) for sym in SYMBOLS[:4]])
    results = ps.run(
        make_parameter(), on_task_done=bad_callback, show_progress=False
    )

    assert len(results) == 4
    assert call_count == 4
    print("PASS  callback exception does not abort remaining jobs")


def test_clear_and_reuse():
    ps = ProcessPoolScheduler(max_workers=2)

    ps.submit([make_job("000001.SZSE")])
    r1 = ps.run(make_parameter(), show_progress=False)
    assert len(r1) == 1

    ps.clear()
    assert ps.job_count == 0

    ps.submit([make_job("600519.SSE"), make_job("300750.SZSE")])
    r2 = ps.run(make_parameter(), show_progress=False)
    assert len(r2) == 2
    assert r2[0].vt_symbol == "600519.SSE"
    print("PASS  clear and reuse")


def test_task_status_synced_after_run():
    jobs = [make_job(sym) for sym in SYMBOLS[:4]]
    ps = ProcessPoolScheduler(max_workers=4)
    ps.submit(jobs)
    results = ps.run(make_parameter(), show_progress=False)

    for job, result in zip(jobs, results):
        assert job.task.status == result.status, (
            f"{job.task.vt_symbol}: task={job.task.status} result={result.status}"
        )
    print("PASS  task.status synced after run")


def test_timing_observation():
    """
    Timing observation: documents serial vs parallel wall-clock.

    Note: on Windows the 'spawn' start method adds ~1-2s fixed overhead
    per worker pool creation, which dominates for fast backtests (<0.1s/symbol).
    ProcessPoolScheduler is designed for large pools (300+ symbols) where
    per-symbol work exceeds 1s — at that scale the speedup is significant.

    This test only verifies correctness (same count, same order), NOT speed,
    because synthetic 400-bar backtests are too fast to show speedup.
    """
    n_workers = min(4, os.cpu_count() or 1)

    serial = SerialScheduler()
    serial.submit([make_job(sym) for sym in SYMBOLS])
    t0 = time.perf_counter()
    serial_results = serial.run(make_parameter(), show_progress=False)
    serial_elapsed = time.perf_counter() - t0

    ps = ProcessPoolScheduler(max_workers=n_workers)
    ps.submit([make_job(sym) for sym in SYMBOLS])
    t1 = time.perf_counter()
    parallel_results = ps.run(make_parameter(), show_progress=False)
    parallel_elapsed = time.perf_counter() - t1

    ratio = parallel_elapsed / max(serial_elapsed, 1e-6)
    print(f"  Serial  : {serial_elapsed:.2f}s  ({len(serial_results)} results)")
    print(f"  Parallel: {parallel_elapsed:.2f}s  "
          f"({n_workers} workers, {len(parallel_results)} results)")
    print(f"  Ratio   : {ratio:.2f}x  "
          f"(>1 = spawn overhead; <1 = speedup; expected <1 for heavy workloads)")

    # Correctness assertions only
    assert len(parallel_results) == len(serial_results)
    for sr, pr in zip(serial_results, parallel_results):
        assert sr.vt_symbol == pr.vt_symbol
        assert sr.status == pr.status

    print("PASS  timing observation (correctness OK; timing is informational)")


def test_drop_in_swap_batch_engine():
    """BatchBacktestingEngine with ProcessPoolScheduler produces same results."""
    syms = ["000001.SZSE", "600519.SSE", "300750.SZSE", "000858.SZSE"]

    def build_engine(scheduler):
        eng = BatchBacktestingEngine(scheduler=scheduler)
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
        eng.set_stock_pool(syms)
        for vt in syms:
            eng.set_bars(vt, make_bars(vt.split(".")[0]))
        return eng

    serial_results = build_engine(SerialScheduler()).run_backtesting(
        show_progress=False
    )
    parallel_eng = build_engine(ProcessPoolScheduler(max_workers=4))
    parallel_results = parallel_eng.run_backtesting(show_progress=False)

    assert len(parallel_results) == len(serial_results)
    assert parallel_eng.summary.total == len(syms)

    for sr, pr in zip(serial_results, parallel_results):
        assert sr.vt_symbol == pr.vt_symbol
        assert sr.status == pr.status, (
            f"{sr.vt_symbol}: serial={sr.status} parallel={pr.status}"
        )

    print(
        f"PASS  drop-in swap  "
        f"serial={len(serial_results)} results  "
        f"parallel_summary={parallel_eng.summary}"
    )


def test_progress_bar_smoke():
    """show_progress=True must not raise on Windows GBK console."""
    ps = ProcessPoolScheduler(max_workers=2)
    ps.submit([make_job("000001.SZSE"), make_job("600519.SSE")])
    results = ps.run(make_parameter(), show_progress=True)
    assert len(results) == 2
    print("\nPASS  progress bar smoke test")


# ================================================================
# Entry point  (MUST be guarded on Windows)
# ================================================================

if __name__ == "__main__":
    print("=" * 65)
    print("Phase 8 Test Part 2: ProcessPoolScheduler (spawn)")
    print("=" * 65)

    test_single_job()
    test_multiple_jobs_order_preserved()
    test_runsummary_counts()
    test_on_task_done_callback()
    test_on_task_start_callback()
    test_callback_exception_does_not_abort()
    test_clear_and_reuse()
    test_task_status_synced_after_run()
    test_timing_observation()
    test_drop_in_swap_batch_engine()
    test_progress_bar_smoke()

    print()
    print("=" * 65)
    print("Phase 8 Part 2 ALL TESTS PASSED")
    print("=" * 65)
