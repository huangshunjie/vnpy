"""Phase 5 test: Scheduler (serial)"""

import random
from datetime import datetime, timedelta
from collections.abc import Callable

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy_ctastrategy.backtesting import BacktestingMode
from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy

from vnpy.app.batch_research.parameter import BacktestParameter
from vnpy.app.batch_research.task import BacktestTask, BacktestResult, TaskStatus
from vnpy.app.batch_research.scheduler import (
    Scheduler,
    SerialScheduler,
    SchedulerBase,
    ScheduleJob,
    RunSummary,
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
            gateway_name="CSV", symbol=symbol, exchange=Exchange.SZSE,
            datetime=dt, interval=Interval.DAILY,
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
    "000858.SZSE", "600036.SSE",
]


# ================================================================
# Tests
# ================================================================

def test_scheduler_is_alias_for_serial():
    """Scheduler must be SerialScheduler."""
    assert Scheduler is SerialScheduler
    s = Scheduler()
    assert isinstance(s, SchedulerBase)
    print("PASS  Scheduler is alias for SerialScheduler")


def test_schedule_job_auto_task_id():
    """ScheduleJob assigns task_id if blank."""
    task = BacktestTask(
        vt_symbol="000001.SZSE",
        strategy_class=AtrRsiStrategy,
        strategy_setting={},
        task_id="",
    )
    job = ScheduleJob(task=task, bars=[])
    assert job.task.task_id != "", "task_id should be auto-assigned"
    print(f"PASS  ScheduleJob auto task_id: {job.task.task_id!r}")


def test_empty_queue_returns_empty_list():
    """run() on empty queue returns [] without error."""
    s = SerialScheduler()
    results = s.run(make_parameter(), show_progress=False)
    assert results == []
    print("PASS  empty queue -> []")


def test_serial_single_job():
    """One job produces one BacktestResult."""
    s = SerialScheduler()
    s.submit([make_job("000001.SZSE")])
    results = s.run(make_parameter(), show_progress=False)

    assert len(results) == 1
    r = results[0]
    assert isinstance(r, BacktestResult)
    assert r.vt_symbol == "000001.SZSE"
    assert r.status in (TaskStatus.SUCCESS, TaskStatus.SKIPPED)
    print(f"PASS  serial single job  status={r.status.value}  "
          f"total_return={r.total_return:.2f}%")


def test_serial_multiple_jobs_order_preserved():
    """Results order matches submission order."""
    s = SerialScheduler()
    jobs = [make_job(sym) for sym in SYMBOLS]
    s.submit(jobs)
    results = s.run(make_parameter(), show_progress=False)

    assert len(results) == len(SYMBOLS)
    for i, (res, sym) in enumerate(zip(results, SYMBOLS)):
        assert res.vt_symbol == sym, (
            f"Position {i}: expected {sym}, got {res.vt_symbol}"
        )
    print(f"PASS  results order preserved ({len(SYMBOLS)} symbols)")


def test_run_summary_counts():
    """RunSummary.total / success / failed counters are accurate."""
    jobs = [make_job(sym) for sym in SYMBOLS]

    # Add one guaranteed-FAILED job (invalid exchange)
    failed_task = BacktestTask(
        vt_symbol="000001.INVALID",
        strategy_class=AtrRsiStrategy,
        strategy_setting={},
        task_id="t_fail",
    )
    jobs.append(ScheduleJob(task=failed_task, bars=make_bars(n=100)))

    # Add one SKIPPED job (empty bars)
    skipped_task = BacktestTask(
        vt_symbol="600000.SSE",
        strategy_class=AtrRsiStrategy,
        strategy_setting={},
        task_id="t_skip",
    )
    jobs.append(ScheduleJob(task=skipped_task, bars=[]))

    s = SerialScheduler()
    s.submit(jobs)
    results = s.run(make_parameter(), show_progress=False)

    summary = s.summary
    assert summary.total == len(jobs), f"total mismatch: {summary.total}"
    assert summary.failed >= 1,        f"expected >=1 failed: {summary.failed}"
    assert summary.skipped >= 1,       f"expected >=1 skipped: {summary.skipped}"
    assert summary.success + summary.skipped + summary.failed == summary.total
    assert summary.elapsed_seconds > 0
    assert summary.start_time is not None
    assert summary.end_time is not None
    assert summary.end_time >= summary.start_time
    assert 0.0 <= summary.success_rate <= 100.0

    print(f"PASS  RunSummary: {summary}")


def test_on_task_done_callback():
    """on_task_done is called once per job with correct result."""
    collected: list[BacktestResult] = []

    def on_done(result: BacktestResult) -> None:
        collected.append(result)

    jobs = [make_job(sym) for sym in SYMBOLS[:3]]
    s = SerialScheduler()
    s.submit(jobs)
    results = s.run(
        make_parameter(),
        on_task_done=on_done,
        show_progress=False,
    )

    assert len(collected) == 3
    assert [r.vt_symbol for r in collected] == [r.vt_symbol for r in results]
    print(f"PASS  on_task_done callback  called={len(collected)}x")


def test_on_task_start_callback():
    """on_task_start is called before each task with status RUNNING."""
    started: list[str] = []

    def on_start(task: BacktestTask) -> None:
        assert task.status == TaskStatus.RUNNING
        started.append(task.vt_symbol)

    jobs = [make_job(sym) for sym in SYMBOLS[:3]]
    s = SerialScheduler()
    s.submit(jobs)
    s.run(
        make_parameter(),
        on_task_start=on_start,
        show_progress=False,
    )

    assert started == SYMBOLS[:3]
    print(f"PASS  on_task_start callback  called={len(started)}x")


def test_on_task_done_exception_does_not_abort():
    """Exception inside on_task_done must not abort remaining jobs."""
    call_count = 0

    def bad_callback(result: BacktestResult) -> None:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("callback exploded")

    jobs = [make_job(sym) for sym in SYMBOLS[:3]]
    s = SerialScheduler()
    s.submit(jobs)
    results = s.run(
        make_parameter(),
        on_task_done=bad_callback,
        show_progress=False,
    )

    # All 3 jobs must complete despite callback errors
    assert len(results) == 3, f"expected 3 results, got {len(results)}"
    assert call_count == 3,   f"callback should have been called 3x, got {call_count}"
    print("PASS  on_task_done exception does not abort remaining jobs")


def test_scheduler_clear_and_reuse():
    """clear() resets the queue; scheduler can be reused for a second run."""
    s = SerialScheduler()
    s.submit([make_job("000001.SZSE")])
    assert s.job_count == 1

    s.clear()
    assert s.job_count == 0

    # Second run with fresh jobs
    s.submit([make_job("600519.SSE"), make_job("300750.SZSE")])
    assert s.job_count == 2
    results = s.run(make_parameter(), show_progress=False)
    assert len(results) == 2
    print("PASS  scheduler clear + reuse")


def test_submit_multiple_batches():
    """submit() can be called multiple times before run()."""
    s = SerialScheduler()
    s.submit([make_job("000001.SZSE"), make_job("600519.SSE")])
    s.submit([make_job("300750.SZSE")])
    assert s.job_count == 3

    results = s.run(make_parameter(), show_progress=False)
    assert len(results) == 3
    print("PASS  submit multiple batches")


def test_task_status_synced_after_run():
    """task.status must reflect the result status after run()."""
    jobs = [make_job(sym) for sym in SYMBOLS[:3]]
    s = SerialScheduler()
    s.submit(jobs)
    results = s.run(make_parameter(), show_progress=False)

    for job, result in zip(jobs, results):
        assert job.task.status == result.status, (
            f"{job.task.vt_symbol}: task.status={job.task.status} "
            f"!= result.status={result.status}"
        )
    print("PASS  task.status synced after run")


def test_progress_bar_shown(capsys_or_pass=None):
    """show_progress=True must not raise (smoke test)."""
    s = SerialScheduler()
    s.submit([make_job("000001.SZSE")])
    try:
        results = s.run(make_parameter(), show_progress=True)
        assert len(results) == 1
        print("\nPASS  progress bar smoke test")
    except Exception as e:
        print(f"\nFAIL  progress bar: {e}")
        raise


# ================================================================
# Entry point
# ================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 5 Test: Scheduler (serial)")
    print("=" * 60)

    test_scheduler_is_alias_for_serial()
    test_schedule_job_auto_task_id()
    test_empty_queue_returns_empty_list()
    test_serial_single_job()
    test_serial_multiple_jobs_order_preserved()
    test_run_summary_counts()
    test_on_task_done_callback()
    test_on_task_start_callback()
    test_on_task_done_exception_does_not_abort()
    test_scheduler_clear_and_reuse()
    test_submit_multiple_batches()
    test_task_status_synced_after_run()
    test_progress_bar_shown()

    print()
    print("=" * 60)
    print("Phase 5 ALL TESTS PASSED")
    print("=" * 60)
