"""Phase 10 test Part 2: EventEngine integration with real backtest thread"""
import os, sys, time, random
from datetime import datetime, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData
from vnpy.event import Event, EventEngine
from vnpy.trader.ui import QtWidgets
from vnpy_ctastrategy.strategies.atr_rsi_strategy import AtrRsiStrategy

_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)


class _FakeMainEngine:
    def __init__(self, ee):
        self._engines = {}
        self.event_engine = ee
    def get_engine(self, name): return self._engines.get(name)
    def write_log(self, msg, source=""): pass


def make_bars(symbol="000001", n=400):
    rng = random.Random(hash(symbol) & 0xFFFF)
    bars, price, dt = [], 10.0, datetime(2020, 1, 2)
    for _ in range(n):
        while dt.weekday() >= 5:
            dt += timedelta(days=1)
        chg = rng.gauss(0, 0.015)
        o, c = price, round(max(0.1, price*(1+chg)), 2)
        h = round(max(o, c)*(1+abs(rng.gauss(0, 0.004))), 2)
        l = round(min(o, c)*(1-abs(rng.gauss(0, 0.004))), 2)
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


SYMS = ["000001.SZSE", "600519.SSE", "300750.SZSE", "000858.SZSE"]


def _make_engine(syms=SYMS):
    from vnpy.app.batch_research.engine import BatchResearchEngine
    ee = EventEngine()
    me = _FakeMainEngine(ee)
    eng = BatchResearchEngine(me, ee)
    me._engines[eng.engine_name] = eng
    eng.set_parameters(
        strategy_class=AtrRsiStrategy,
        start=datetime(2020, 1, 1),
        end=datetime(2021, 6, 30),
        capital=1_000_000, rate=1e-4, slippage=0.02,
        size=1.0, pricetick=0.01,
        strategy_setting={"atr_length": 22, "atr_ma_length": 10},
    )
    eng.set_stock_pool(syms)
    for vt in syms:
        eng.set_bars(vt, make_bars(vt.split(".")[0]))
    return eng, ee


def _wait(engine, timeout=60):
    deadline = time.time() + timeout
    while engine.is_running() and time.time() < deadline:
        time.sleep(0.1)
    time.sleep(0.3)   # let EventEngine dispatch remaining events


# ================================================================
# Tests
# ================================================================

def test_full_run_emits_all_events():
    """Run 4 symbols; verify RESULT, PROGRESS, FINISHED events."""
    from vnpy.app.batch_research.base import (
        EVENT_BATCH_RESULT, EVENT_BATCH_PROGRESS,
        EVENT_BATCH_LOG, EVENT_BATCH_FINISHED,
    )
    eng, ee = _make_engine()

    results_rx   = []
    progress_rx  = []
    log_rx       = []
    finished_rx  = []

    ee.register(EVENT_BATCH_RESULT,   lambda e: results_rx.append(e.data))
    ee.register(EVENT_BATCH_PROGRESS, lambda e: progress_rx.append(e.data))
    ee.register(EVENT_BATCH_LOG,      lambda e: log_rx.append(e.data))
    ee.register(EVENT_BATCH_FINISHED, lambda e: finished_rx.append(e.data))

    ee.start()
    try:
        eng.run_backtesting()
        _wait(eng)

        assert len(results_rx) == len(SYMS), (
            f"Expected {len(SYMS)} results, got {len(results_rx)}"
        )
        assert len(progress_rx) == len(SYMS), (
            f"Expected {len(SYMS)} progress events, got {len(progress_rx)}"
        )
        assert len(finished_rx) == 1, "Expected exactly 1 FINISHED event"
        assert len(log_rx) >= 3

        # Progress must be monotonically increasing
        for i, prog in enumerate(progress_rx):
            assert prog.completed == i + 1
            assert prog.total == len(SYMS)

        # Summary from FINISHED event
        summary = finished_rx[0]
        assert summary is not None
        assert summary.total == len(SYMS)
        assert summary.success + summary.skipped + summary.failed == summary.total

        # get_results() returns all
        assert len(eng.get_results()) == len(SYMS)

        print(
            f"PASS  full run events  results={len(results_rx)}  "
            f"progress={len(progress_rx)}  logs={len(log_rx)}  "
            f"summary={summary}"
        )
    finally:
        ee.stop()


def test_run_twice_sequential():
    """Calling run_backtesting twice (sequentially) should both succeed."""
    from vnpy.app.batch_research.base import EVENT_BATCH_FINISHED

    eng, ee = _make_engine()
    finished_count = [0]
    ee.register(EVENT_BATCH_FINISHED, lambda e: finished_count.__setitem__(0, finished_count[0]+1))
    ee.start()
    try:
        eng.run_backtesting()
        _wait(eng)
        assert finished_count[0] == 1

        eng.run_backtesting()
        _wait(eng)
        assert finished_count[0] == 2

        print("PASS  run twice sequentially")
    finally:
        ee.stop()


def test_run_while_running_noop():
    """Calling run_backtesting while already running must be a no-op."""
    from vnpy.app.batch_research.base import EVENT_BATCH_FINISHED

    # Use more symbols so the run takes long enough to test
    syms = SYMS * 2
    eng, ee = _make_engine(syms)
    finished_count = [0]
    ee.register(EVENT_BATCH_FINISHED, lambda e: finished_count.__setitem__(0, finished_count[0]+1))
    ee.start()
    try:
        eng.run_backtesting()
        assert eng.is_running()
        # Second call while running — should be no-op
        eng.run_backtesting()
        _wait(eng, timeout=90)
        # Only one FINISHED event
        assert finished_count[0] == 1
        print("PASS  run while running is no-op")
    finally:
        ee.stop()


def test_stop_emits_stopped_event():
    """stop_backtesting() causes EVENT_BATCH_STOPPED to be emitted."""
    from vnpy.app.batch_research.base import EVENT_BATCH_STOPPED, EVENT_BATCH_RESULT

    syms = SYMS + ["600036.SSE", "601318.SSE", "600900.SSE", "000333.SZSE"]
    eng, ee = _make_engine(syms)
    stopped_rx = []
    results_rx = []
    ee.register(EVENT_BATCH_STOPPED, lambda e: stopped_rx.append(e))
    ee.register(EVENT_BATCH_RESULT,  lambda e: results_rx.append(e.data))
    ee.start()
    try:
        eng.run_backtesting()
        time.sleep(0.03)
        eng.stop_backtesting()
        _wait(eng, timeout=30)

        assert len(stopped_rx) == 1, f"Expected 1 STOPPED, got {len(stopped_rx)}"
        assert len(results_rx) < len(syms), (
            f"Expected partial results, got all {len(results_rx)}"
        )
        partial = eng.get_results()
        assert len(partial) == len(results_rx)
        print(
            f"PASS  stop_backtesting  "
            f"partial={len(results_rx)}/{len(syms)}"
        )
    finally:
        ee.stop()


def test_progress_percent_correct():
    """ProgressData.percent must equal completed/total*100."""
    from vnpy.app.batch_research.base import EVENT_BATCH_PROGRESS

    eng, ee = _make_engine()
    progress_rx = []
    ee.register(EVENT_BATCH_PROGRESS, lambda e: progress_rx.append(e.data))
    ee.start()
    try:
        eng.run_backtesting()
        _wait(eng)
        assert len(progress_rx) == len(SYMS)
        for prog in progress_rx:
            expected_pct = prog.completed / prog.total * 100
            assert abs(prog.percent - expected_pct) < 1e-9
        print("PASS  progress percent correct")
    finally:
        ee.stop()


def test_get_summary_after_run():
    """get_summary() returns non-None RunSummary after a completed run."""
    eng, ee = _make_engine()
    ee.start()
    try:
        eng.run_backtesting()
        _wait(eng)
        summary = eng.get_summary()
        assert summary is not None
        assert summary.total == len(SYMS)
        print(f"PASS  get_summary after run  summary={summary}")
    finally:
        ee.stop()


if __name__ == "__main__":
    print("=" * 65)
    print("Phase 10 Test Part 2: EventEngine integration")
    print("=" * 65)

    test_full_run_emits_all_events()
    test_run_twice_sequential()
    test_run_while_running_noop()
    test_stop_emits_stopped_event()
    test_progress_percent_correct()
    test_get_summary_after_run()

    print()
    print("=" * 65)
    print("Phase 10 Part 2 ALL TESTS PASSED")
    print("=" * 65)
