"""smoke_dash.py — Phase 8 smoke test"""
from vnpy.research_ops.engine.experiment_engine import ExperimentEngine
from vnpy.research_ops.engine.registry_engine import RegistryEngine
from vnpy.research_ops.engine.pipeline_engine import PipelineEngine
from vnpy.research_ops.engine.report_engine import ReportEngine
from vnpy.research_ops.engine.knowledge_engine import KnowledgeEngine
from vnpy.research_ops.constant import ReportType, NoteType, Priority


class MockEngine:
    class _EE:
        def register(self, *a): pass
    event_engine = _EE()

    def __init__(self):
        self._exp = ExperimentEngine()
        self._reg = RegistryEngine()
        self._pl  = PipelineEngine()
        self._rpt = ReportEngine()
        self._kb  = KnowledgeEngine()

    def get_platform_stats(self):
        return {
            "workspace":  {"projects": 0, "workspaces": 0},
            "experiment": self._exp.stats(),
            "registry":   self._reg.stats(),
            "pipeline":   self._pl.stats(),
            "report":     self._rpt.stats(),
            "knowledge":  self._kb.stats(),
            "governance": {"pending": 0},
        }


engine = MockEngine()

# populate data
exp  = engine._exp.create_experiment("alpha研究")
engine._exp.start_run(exp.experiment_id, "run1")
pl   = engine._pl.create_pipeline("每日Pipeline")
rpt  = engine._rpt.create_report("月报", report_type=ReportType.WEEKLY)
note = engine._kb.create_note("研究笔记",
                               note_type=NoteType.RESEARCH,
                               priority=Priority.HIGH)

s = engine.get_platform_stats()
assert s["experiment"]["experiments"] == 1
assert s["experiment"]["runs"] >= 1
assert s["pipeline"]["pipelines"] == 1
assert s["report"]["reports"] == 1
assert s["knowledge"]["notes"] == 1
print("  platform_stats: PASSED")
print("  exp:", s["experiment"])
print("  pl: ", s["pipeline"])

# UI class imports
from vnpy.research_ops.ui.dashboard_tab import (
    DashboardTab, StatGrid, ActivityFeed, AlertPanel,
    KpiCard, ActivityItem, AlertRow,
    CARD_DEFS, EVENT_ALL,
    C_BLUE, C_GREEN, C_RED, C_ORANGE, C_PURPLE,
)
assert len(CARD_DEFS) == 9
assert len(EVENT_ALL) >= 18
print("  constants: PASSED  CARD_DEFS=%d  EVENT_ALL=%d"
      % (len(CARD_DEFS), len(EVENT_ALL)))

assert hasattr(KpiCard,      "update_value")
assert hasattr(ActivityFeed, "push_manual")
assert hasattr(AlertPanel,   "refresh")
assert hasattr(StatGrid,     "refresh")
assert hasattr(DashboardTab, "_do_refresh")
print("  UI class API: PASSED")

import inspect
assert "get_platform_stats" in inspect.getsource(StatGrid.refresh)
assert "get_platform_stats" in inspect.getsource(AlertPanel.refresh)
assert "get_platform_stats" in inspect.getsource(DashboardTab._do_refresh)
print("  logic path check: PASSED")

from vnpy.research_ops.ui.stub_tabs import (
    DashboardTab as DT2, WorkspaceTab, ExperimentTab,
    RegistryTab, PipelineTab, ReportTab, KnowledgeTab,
    GovernanceTab,
)
assert DashboardTab is DT2
print("  stub_tabs re-export: PASSED")

print()
print("=== Phase 8 Smoke Test: ALL PASSED ===")
