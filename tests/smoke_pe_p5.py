"""smoke_pe_p5.py — Phase 5 smoke test"""
from datetime import datetime

# ── 1. HealthScorer ───────────────────────────────────────────────
from vnpy.platform_engineering.engine.health_engine import (
    HealthEngine, HealthScorer, _sm, _wt, _det_status,
)
from vnpy.platform_engineering.model.health import HealthMetricSnapshot
from vnpy.platform_engineering.constant import HealthStatus, HealthLevel

scorer = HealthScorer()

# 全优快照
snap_good = HealthMetricSnapshot(
    sharpe=2.0, max_drawdown=0.05, win_rate=0.60,
    risk_exposure=0.15, ic_mean=0.08, alpha_decay=0.10,
    order_delay_ms=150.0, fill_rate=0.99, slippage_bps=3.0,
    updated_at=datetime.now(),
)
total, perf, risk, alpha, exc, warns = scorer.compute(snap_good)
assert total is not None and total >= 80, f"expected >=80, got {total}"
assert perf  is not None and perf  >= 80
assert risk  is not None and risk  >= 80
assert alpha is not None and alpha >= 80
assert exc   is not None and exc   >= 80
assert len(warns) == 0
print(f"  scorer good: PASSED  total={total:.1f}  warns={warns}")

# 全差快照
snap_bad = HealthMetricSnapshot(
    sharpe=0.1, max_drawdown=0.35, win_rate=0.40,
    risk_exposure=0.70, ic_mean=0.01, alpha_decay=0.55,
    order_delay_ms=1200.0, fill_rate=0.80, slippage_bps=35.0,
    updated_at=datetime.now(),
)
total2, perf2, risk2, alpha2, exc2, warns2 = scorer.compute(snap_bad)
assert total2 is not None and total2 < 50, f"expected <50, got {total2}"
assert len(warns2) >= 5
print(f"  scorer bad: PASSED  total={total2:.1f}  warns={len(warns2)}")

# partial snapshot (some None)
snap_partial = HealthMetricSnapshot(
    sharpe=1.5, max_drawdown=None, win_rate=None,
    risk_exposure=0.25, ic_mean=None, alpha_decay=None,
    order_delay_ms=None, fill_rate=None, slippage_bps=None,
    updated_at=datetime.now(),
)
total3, *_ = scorer.compute(snap_partial)
assert total3 is not None
print(f"  scorer partial: PASSED  total={total3:.1f}")

# ── 2. HealthEngine ───────────────────────────────────────────────
he = HealthEngine()

# register
rec = he.register_strategy("STR-001", "MomentumAlpha")
assert rec.status == HealthStatus.UNKNOWN
print(f"  register_strategy: PASSED  id={rec.health_id}")

# update with good snapshot → HEALTHY
he.update_snapshot("STR-001", snap_good)
rec = he.get_health("STR-001")
assert rec.status == HealthStatus.HEALTHY
assert rec.score >= 80
assert rec.perf_score >= 80
assert rec.risk_score >= 80
print(f"  update_snapshot good: PASSED  status={rec.status.value}  score={rec.score}")

# update with bad snapshot → WARNING or CRITICAL
he.update_snapshot("STR-001", snap_bad)
rec = he.get_health("STR-001")
assert rec.status in (HealthStatus.WARNING, HealthStatus.CRITICAL,
                      HealthStatus.RETIRE)
assert len(rec.warnings) >= 5
print(f"  update_snapshot bad: PASSED  status={rec.status.value}  warns={len(rec.warnings)}")

# callback on status change
changed = []
he.on_health_changed(lambda r: changed.append(r.strategy_id))
he.register_strategy("STR-002", "MeanReversion")
he.update_snapshot("STR-002", snap_good)
he.update_snapshot("STR-002", snap_bad)
assert len(changed) >= 1   # UNKNOWN→HEALTHY, then HEALTHY→WARNING/CRITICAL
print(f"  health_callback: PASSED  fired={len(changed)}")

# list_health
he.register_strategy("STR-003", "StatArb")
he.update_snapshot("STR-003", snap_good)
all_recs = he.list_health()
assert len(all_recs) == 3
healthy = he.list_health(status=HealthStatus.HEALTHY)
assert len(healthy) >= 1
print(f"  list_health: PASSED  total={len(all_recs)}  healthy={len(healthy)}")

# stats
s = he.stats()
assert s["total"] == 3
assert s["avg_score"] > 0
print(f"  stats: PASSED  {s}")

# background monitor
import time
snap_calls = []
def fake_snap(sid):
    snap_calls.append(sid)
    return snap_good

he.start_monitor(interval_secs=1, snapshot_fn=fake_snap)
time.sleep(1.5)
he.stop()
assert len(snap_calls) >= 3   # 3 strategies × ≥1 poll
print(f"  start_monitor: PASSED  snap_calls={len(snap_calls)}")

# ── 3. UI class imports ───────────────────────────────────────────
from vnpy.platform_engineering.ui.strategy_health import (
    StrategyHealthTab, HealthList, DetailPanel, DimScorePanel,
    ScoreRing, RegisterStrategyDialog, UpdateSnapshotDialog,
    STATUS_COLOR, STATUS_ICON, DIM_COLOR, LEVEL_COLOR,
)
assert len(STATUS_COLOR) == 5
assert len(STATUS_ICON)  == 5
assert len(DIM_COLOR)    == 4
assert hasattr(HealthList,           "refresh")
assert hasattr(DetailPanel,          "load")
assert hasattr(DimScorePanel,        "update_scores")
assert hasattr(ScoreRing,            "set_score")
assert hasattr(StrategyHealthTab,    "_refresh")
assert hasattr(RegisterStrategyDialog, "get_strategy_id")
assert hasattr(UpdateSnapshotDialog,   "get_snapshot")
snap_from_dlg = UpdateSnapshotDialog  # class check only
print("  StrategyHealthTab UI: PASSED")

# ── 4. stub_tabs re-export ────────────────────────────────────────
from vnpy.platform_engineering.ui.stub_tabs import (
    StrategyHealthTab as SHT2, DashboardTab, ObservabilityTab,
    TaskTab, DeploymentTab, LogTab, ConfigTab, ApiTab, SecurityTab,
)
assert StrategyHealthTab is SHT2
print("  stub_tabs re-export: PASSED")

# ── 5. Phase 1-4 regression ──────────────────────────────────────
from vnpy.platform_engineering import PlatformEngineeringApp
from vnpy.platform_engineering.engine.deployment_engine import DeploymentEngine
from vnpy.platform_engineering.constant import DeployStage
de = DeploymentEngine()
r  = de.create_deployment("STR-X", "Test", created_by="smoke")
de.advance_stage(r.deploy_id, DeployStage.VALIDATION)
assert de.get_deployment(r.deploy_id).current_stage == DeployStage.VALIDATION
print("  Phase1-4 regression: PASSED")

print()
print("=== Phase 5 Smoke Test: ALL PASSED ===")
