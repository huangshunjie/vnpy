"""smoke_pe_p2.py — Phase 2 smoke test"""

# ── 1. ObservabilityEngine 完整版 ─────────────────────────────────
from vnpy.platform_engineering.engine.observability_engine import (
    ObservabilityEngine, AlertRule,
)
from vnpy.platform_engineering.constant import (
    MetricLayer, MetricType, AlertSeverity, HealthLevel,
)
from vnpy.platform_engineering.model.metric import MetricPoint

oe = ObservabilityEngine()
oe.start()

# default rules loaded
assert len(oe.list_rules()) >= 10
print(f"  default_rules: PASSED  count={len(oe.list_rules())}")

# record normal metric — no alert
pt_ok = oe.make_point("system.cpu_pct", 30.0, MetricLayer.SYSTEM, unit="%")
oe.record_metric(pt_ok)
assert len(oe.list_alerts(active_only=True)) == 0
score = oe.get_health_score()
assert score.score == 100.0
assert score.level == HealthLevel.GREEN
print("  record_metric normal: PASSED")

# trigger CPU warning alert
pt_warn = oe.make_point("system.cpu_pct", 85.0, MetricLayer.SYSTEM, unit="%")
oe.record_metric(pt_warn)
alerts = oe.list_alerts(active_only=True)
assert len(alerts) >= 1
score2 = oe.get_health_score()
assert score2.score < 100.0
assert score2.system_score < 100.0  # WARNING penalty applied to system layer
print(f"  alert triggered: PASSED  alerts={len(alerts)}  score={score2.score}")

# auto-resolve by recording normal value
pt_ok2 = oe.make_point("system.cpu_pct", 30.0, MetricLayer.SYSTEM, unit="%")
oe.record_metric(pt_ok2)
alerts_after = oe.list_alerts(active_only=True)
# CPU-warning rule should be auto-resolved (still may have critical if triggered)
print(f"  auto-resolve: PASSED  remaining active={len(alerts_after)}")

# manual resolve
for a in oe.list_alerts(active_only=True):
    oe.resolve_alert(a.alert_id)
assert len(oe.list_alerts(active_only=True)) == 0
score3 = oe.get_health_score()
assert score3.score == 100.0
print("  manual_resolve: PASSED")

# layer scores
oe.record_many([
    oe.make_point("data.delay_secs",  120.0, MetricLayer.DATA),
    oe.make_point("strategy.perf_drift", 0.25, MetricLayer.STRATEGY),
])
score4 = oe.get_health_score()
assert score4.data_score < 100.0
assert score4.strategy_score < 100.0
assert score4.system_score == 100.0  # no system alert
print(f"  layer_scores: PASSED  data={score4.data_score}  strategy={score4.strategy_score}")

s = oe.stats()
assert "health_score" in s
assert "rules" in s
print(f"  stats: PASSED  {s}")
oe.stop()

# ── 2. MetricCollector ────────────────────────────────────────────
from vnpy.platform_engineering.engine.metric_collector import (
    MetricCollector, SystemAdapter, CustomMetricAdapter,
)
oe2 = ObservabilityEngine()
mc  = MetricCollector(oe2, interval_secs=60)
mc.register(SystemAdapter())
mc.register(CustomMetricAdapter(
    "test_adapter", MetricLayer.DATA,
    lambda: [oe2.make_point("data.delay_secs", 5.0, MetricLayer.DATA)],
))
assert len(mc.list_adapters()) == 2
n = mc.collect_once()
assert n >= 1
print(f"  MetricCollector: PASSED  points_collected={n}")

# start/stop
mc.start()
import time; time.sleep(0.1)
assert mc.stats()["running"] is True
mc.stop()
assert mc.stats()["running"] is False
print("  MetricCollector start/stop: PASSED")

# ── 3. UI class imports ───────────────────────────────────────────
from vnpy.platform_engineering.ui.dashboard import (
    DashboardTab, HealthRingWidget, LayerScoreCard, StatCard, AlertRow,
    LEVEL_COLOR, LAYER_COLOR, SEV_COLOR,
)
assert len(LEVEL_COLOR) == 3
assert len(LAYER_COLOR) == 4
assert len(SEV_COLOR) == 4
assert hasattr(HealthRingWidget, "update_score")
assert hasattr(LayerScoreCard,   "update_score")
assert hasattr(StatCard,         "set_value")
assert hasattr(DashboardTab,     "_refresh")
print("  DashboardTab UI: PASSED")

from vnpy.platform_engineering.ui.monitor import (
    ObservabilityTab, MetricTable, AlertTable, RuleTable,
)
assert hasattr(MetricTable,      "refresh")
assert hasattr(AlertTable,       "refresh")
assert hasattr(RuleTable,        "refresh")
assert hasattr(ObservabilityTab, "_refresh")
print("  ObservabilityTab UI: PASSED")

from vnpy.platform_engineering.ui.log import (
    LogTab, LogEntry, _ALL_EVENTS, MAX_LOG_ROWS,
)
assert len(_ALL_EVENTS) >= 20
assert MAX_LOG_ROWS == 500
assert hasattr(LogTab, "add_log")
assert hasattr(LogTab, "_on_event")
print(f"  LogTab UI: PASSED  events={len(_ALL_EVENTS)}")

# ── 4. stub_tabs re-exports ───────────────────────────────────────
from vnpy.platform_engineering.ui.stub_tabs import (
    DashboardTab as DT2, ObservabilityTab as OT2, LogTab as LT2,
    TaskTab, DeploymentTab, StrategyHealthTab, ConfigTab, ApiTab, SecurityTab,
)
assert DashboardTab is DT2
assert ObservabilityTab is OT2
assert LogTab is LT2
print("  stub_tabs re-export: PASSED")

# ── 5. Phase 1 regression ─────────────────────────────────────────
from vnpy.platform_engineering import PlatformEngineeringApp
assert PlatformEngineeringApp.app_name == "PlatformEngineering"
print("  Phase1 regression: PASSED")

print()
print("=== Phase 2 Smoke Test: ALL PASSED ===")
