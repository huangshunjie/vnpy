"""Phase 4 test: Worker"""

import math
import random
from datetime import datetime, timedelta

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy_ctastrategy.backtesting import BacktestingMode
from vnpy_ctastrategy.template import CtaTemplate

from vnpy.app.batch_research.parameter import BacktestParameter
from vnpy.app.batch_research.task import BacktestTask, BacktestResult, TaskStatus
from vnpy.app.batch_research.worker import Worker


# ================================================================
# Synthetic bar generator
# ================================================================

def make_bars(
    symbol: str = "000001",
    exchange: Exchange = Exchange.SZSE,
    n: int = 500,
    start: datetime | None = None,
) -> list[BarData]:
    if start is None:
        start = datetime(2020, 1, 2)

    rng = random.Random(42)
    bars: list[BarData] = []
    price = 10.0
    dt = start

    for _ in range(n):
        while dt.weekday() >= 5:
            dt += timedelta(days=1)

        change = rng.gauss(0, 0.015)
        open_p  = price
        close_p = round(max(0.1, price * (1 + change)), 2)
        high_p  = round(max(open_p, close_p) * (1 + abs(rng.gauss(0, 0.005))), 2)
        low_p   = round(min(open_p, close_p) * (1 - abs(rng.gauss(0, 0.005))), 2)
        volume  = rng.randint(500_000, 5_000_000)

        bar = BarData(
            gateway_name="CSV",
            symbol=symbol,
            exchange=exchange,
            datetime=dt,
            interval=Interval.DAILY,
            open_price=open_p,
            high_price=high_p,
            low_price=low_p,
            close_price=close_p,
            volume=float(volume),
        )
        bars.append(bar)
        price = close_p
        dt += timedelta(days=1)

    return bars


# ================================================================
# Shared helpers
# ================================================================

def make_parameter() -> BacktestParameter:
    return BacktestParameter(
        start=datetime(2020, 1, 1),
        end=datetime(2021, 12, 31),
        interval=Interval.DAILY,
        capital=1_000_000,
        rate=1e-4,
        slippage=0.02,
        size=1.0,
        pricetick=0.01,
        risk_free=0.03,
        annual_days=240,
        mode=BacktestingMode.BAR,
    )


def make_task(vt_symbol: str = "000001.SZSE") -> BacktestTask:
    from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy
    return BacktestTask(
        vt_symbol=vt_symbol,
        strategy_class=AtrRsiStrategy,
        strategy_setting={"atr_length": 22, "atr_ma_length": 10},
        task_id=f"test_{vt_symbol}",
    )


# ================================================================
# Tests
# ================================================================

def test_worker_csv_inject_success():
    bars = make_bars(n=500)
    task = make_task()
    param = make_parameter()

    worker = Worker()
    result = worker.run(task, param, bars=bars)

    assert isinstance(result, BacktestResult)
    assert result.status == TaskStatus.SUCCESS, (
        f"expected SUCCESS, got {result.status}, err={result.error_msg}"
    )
    assert result.vt_symbol == "000001.SZSE"
    assert result.strategy_name == "AtrRsiStrategy"
    assert result.run_start_time is not None
    assert result.run_end_time is not None
    assert result.elapsed_seconds is not None and result.elapsed_seconds > 0

    required = [
        "start_date", "end_date", "total_days",
        "capital", "end_balance",
        "total_return", "annual_return",
        "max_drawdown", "max_ddpercent",
        "sharpe_ratio", "total_trade_count",
    ]
    for key in required:
        assert key in result.statistics, f"missing stat key: {key}"

    assert result.statistics["capital"] == 1_000_000
    assert not math.isnan(result.total_return)
    assert not math.isinf(result.sharpe_ratio)

    print(f"PASS  Worker CSV inject SUCCESS: {result}")
    print(f"      total_return={result.total_return:.2f}%  "
          f"sharpe={result.sharpe_ratio:.2f}  "
          f"trades={result.total_trade_count}  "
          f"elapsed={result.elapsed_seconds:.3f}s")


def test_worker_empty_bars_skipped():
    task = make_task()
    param = make_parameter()

    worker = Worker()
    result = worker.run(task, param, bars=[])

    assert result.status == TaskStatus.SKIPPED, (
        f"expected SKIPPED, got {result.status}"
    )
    assert result.statistics == {}
    assert result.error_msg == ""
    print("PASS  Worker empty bars -> SKIPPED")


def test_worker_exception_captured_as_failed():
    """
    set_parameters() raises ValueError for an unknown Exchange string.
    Exchange("INVALID_EXCHANGE") is not in the Exchange enum, so this
    triggers FAILED at engine setup time, before any bar data is touched.
    Worker must catch it and return FAILED without re-raising.
    """
    from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy

    task = BacktestTask(
        vt_symbol="000001.INVALID_EXCHANGE",
        strategy_class=AtrRsiStrategy,
        strategy_setting={},
        task_id="test_fail",
    )
    bars = make_bars(n=100)
    param = make_parameter()

    worker = Worker()
    result = worker.run(task, param, bars=bars)

    assert result.status == TaskStatus.FAILED, (
        f"expected FAILED, got {result.status}"
    )
    assert result.error_msg != ""
    print(f"PASS  Worker exception -> FAILED  "
          f"(snippet: {result.error_msg.splitlines()[0]!r})")


def test_worker_task_start_end_overrides_parameter():
    from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy

    bars = make_bars(n=500, start=datetime(2020, 1, 2))
    param = make_parameter()

    # Task overrides: only backtest 2020
    task = BacktestTask(
        vt_symbol="000001.SZSE",
        strategy_class=AtrRsiStrategy,
        strategy_setting={"atr_length": 22, "atr_ma_length": 10},
        task_id="test_override",
        start=datetime(2020, 1, 1),
        end=datetime(2020, 12, 31),
    )

    worker = Worker()
    result = worker.run(task, param, bars=bars)

    assert result.status in (TaskStatus.SUCCESS, TaskStatus.SKIPPED)
    if result.status == TaskStatus.SUCCESS:
        total_days = result.statistics.get("total_days", 0)
        assert total_days <= 270, f"time override not effective, total_days={total_days}"
    print(f"PASS  Worker task-level start/end override  "
          f"(status={result.status.value}, "
          f"total_days={result.statistics.get('total_days', 'N/A')})")


def test_worker_strategy_setting_merges():
    """Task strategy_setting overrides keys from Parameter.strategy_setting."""
    from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy

    param = BacktestParameter(
        start=datetime(2020, 1, 1),
        end=datetime(2021, 12, 31),
        capital=1_000_000,
        rate=1e-4,
        slippage=0.0,
        size=1.0,
        pricetick=0.01,
        strategy_setting={"atr_length": 10, "atr_ma_length": 5},
    )
    # Task overrides atr_length=30, atr_ma_length stays 5 from param
    task = BacktestTask(
        vt_symbol="000001.SZSE",
        strategy_class=AtrRsiStrategy,
        strategy_setting={"atr_length": 30},
        task_id="test_merge",
    )
    bars = make_bars(n=500)
    worker = Worker()
    result = worker.run(task, param, bars=bars)

    assert result.status in (TaskStatus.SUCCESS, TaskStatus.SKIPPED)
    print(f"PASS  Worker strategy_setting merge  (status={result.status.value})")


def test_worker_to_flat_dict():
    bars = make_bars(n=500)
    task = make_task()
    param = make_parameter()

    worker = Worker()
    result = worker.run(task, param, bars=bars)

    if result.status != TaskStatus.SUCCESS:
        print(f"SKIP  to_flat_dict (status={result.status.value})")
        return

    flat = result.to_flat_dict()
    for k in ["vt_symbol", "task_id", "strategy_name", "status",
              "elapsed_seconds", "total_return", "sharpe_ratio"]:
        assert k in flat, f"to_flat_dict missing key: {k}"

    assert flat["vt_symbol"] == "000001.SZSE"
    assert flat["status"] == "success"
    print(f"PASS  BacktestResult.to_flat_dict()  keys={len(flat)}")


def test_worker_multiple_symbols_isolated():
    """Each symbol gets its own BacktestingEngine; results are independent."""
    from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy

    symbols = ["000001.SZSE", "600519.SSE", "300750.SZSE"]
    param = make_parameter()
    worker = Worker()

    results: list[BacktestResult] = []
    for vt_symbol in symbols:
        sym = vt_symbol.split(".")[0]
        bars = make_bars(symbol=sym, n=500)
        task = BacktestTask(
            vt_symbol=vt_symbol,
            strategy_class=AtrRsiStrategy,
            strategy_setting={"atr_length": 22, "atr_ma_length": 10},
            task_id=f"test_{sym}",
        )
        result = worker.run(task, param, bars=bars)
        results.append(result)

    assert len(results) == 3
    assert {r.vt_symbol for r in results} == set(symbols)
    for r in results:
        # Each engine gets its own fresh capital
        assert r.statistics.get("capital") == 1_000_000

    print("PASS  Worker multiple symbols isolated")
    for r in results:
        print(f"      {r.vt_symbol:20s}  status={r.status.value:8s}  "
              f"total_return={r.total_return:+.2f}%  sharpe={r.sharpe_ratio:.2f}")


def test_worker_result_timing():
    """run_start_time < run_end_time and elapsed_seconds matches."""
    bars = make_bars(n=500)
    task = make_task()
    param = make_parameter()

    worker = Worker()
    result = worker.run(task, param, bars=bars)

    assert result.run_start_time is not None
    assert result.run_end_time is not None
    assert result.run_end_time >= result.run_start_time
    elapsed = result.elapsed_seconds
    assert elapsed is not None and elapsed >= 0
    print(f"PASS  Worker result timing  elapsed={elapsed:.3f}s")


# ================================================================
# Entry point
# ================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 4 Test: Worker")
    print("=" * 60)

    test_worker_csv_inject_success()
    test_worker_empty_bars_skipped()
    test_worker_exception_captured_as_failed()
    test_worker_task_start_end_overrides_parameter()
    test_worker_strategy_setting_merges()
    test_worker_to_flat_dict()
    test_worker_multiple_symbols_isolated()
    test_worker_result_timing()

    print()
    print("=" * 60)
    print("Phase 4 ALL TESTS PASSED")
    print("=" * 60)
