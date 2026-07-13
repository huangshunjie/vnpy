"""Phase 10 test Part 1a: base.py + engine.py + app.py"""
import os, sys, time
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from vnpy.event import Event, EventEngine
from vnpy.trader.ui import QtWidgets
_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)


class _FakeMainEngine:
    def __init__(self, ee):
        self._engines = {}
        self.event_engine = ee
    def get_engine(self, name): return self._engines.get(name)
    def write_log(self, msg, source=""): pass


def test_base_constants():
    from vnpy.app.batch_research.base import (
        APP_NAME, EVENT_BATCH_PROGRESS, EVENT_BATCH_RESULT,
        EVENT_BATCH_LOG, EVENT_BATCH_FINISHED, EVENT_BATCH_STOPPED,
    )
    assert APP_NAME == "BatchResearch"
    events = [EVENT_BATCH_PROGRESS, EVENT_BATCH_RESULT, EVENT_BATCH_LOG,
              EVENT_BATCH_FINISHED, EVENT_BATCH_STOPPED]
    assert len(set(events)) == 5
    for e in events:
        assert isinstance(e, str) and e.startswith("e")
    print("PASS  base constants")


def test_progress_data():
    from vnpy.app.batch_research.base import ProgressData
    p = ProgressData(5, 10, 3, 1, 1, "000001.SZSE", 2.5)
    assert abs(p.percent - 50.0) < 1e-9
    assert "50.0%" in repr(p)
    assert ProgressData(0, 0, 0, 0, 0).percent == 0.0
    print("PASS  ProgressData")


def test_engine_write_log_event():
    from vnpy.app.batch_research.engine import BatchResearchEngine
    from vnpy.app.batch_research.base import EVENT_BATCH_LOG
    ee = EventEngine(); me = _FakeMainEngine(ee)
    received = []
    ee.register(EVENT_BATCH_LOG, lambda e: received.append(e.data))
    ee.start()
    try:
        eng = BatchResearchEngine(me, ee)
        eng.write_log("hello")
        time.sleep(0.15)
        assert any("hello" in m for m in received)
        print("PASS  engine.write_log -> EVENT_BATCH_LOG")
    finally:
        ee.stop()


def test_engine_initial_state():
    from vnpy.app.batch_research.engine import BatchResearchEngine
    ee = EventEngine(); me = _FakeMainEngine(ee)
    eng = BatchResearchEngine(me, ee)
    assert not eng.is_running()
    assert eng.get_results() == []
    # Scheduler initialises with empty RunSummary(total=0), not None
    from vnpy.app.batch_research.scheduler import RunSummary
    s = eng.get_summary()
    assert s is None or (isinstance(s, RunSummary) and s.total == 0)
    print("PASS  engine initial state")


def test_app_registration():
    from vnpy.app.batch_research.app import BatchResearchApp
    from vnpy.app.batch_research.engine import BatchResearchEngine
    assert BatchResearchApp.app_name == "BatchResearch"
    assert BatchResearchApp.widget_name == "BatchResearchWidget"
    assert BatchResearchApp.display_name == "批量回测研究"
    assert BatchResearchApp.engine_class is BatchResearchEngine
    print("PASS  BatchResearchApp registration")


if __name__ == "__main__":
    print("=" * 55)
    print("Phase 10a: base + engine + app")
    print("=" * 55)
    test_base_constants()
    test_progress_data()
    test_engine_write_log_event()
    test_engine_initial_state()
    test_app_registration()
    print("\nPhase 10a ALL PASSED")
