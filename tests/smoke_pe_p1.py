"""smoke_pe_p1.py — Phase 1 smoke test"""
from vnpy.platform_engineering import (
    PlatformEngineeringApp, PlatformEngineeringEngine, PlatformEngine,
    HealthLevel, MetricLayer, MetricType,
    TaskStatus, TaskType, TaskPriority,
    DeployStage, HealthStatus, ConfigType,
    UserRole, PermissionAction, AlertSeverity, WorkerStatus,
)
print("  top-level imports: PASSED")

# constant enums
assert len(list(HealthLevel))    == 3
assert len(list(TaskStatus))     == 8
assert len(list(DeployStage))    == 8
assert len(list(UserRole))       == 5
assert len(list(PermissionAction)) == 5
print("  enums: PASSED")

# event constants
from vnpy.platform_engineering.event import (
    EVENT_PE_METRIC_UPDATED, EVENT_PE_TASK_CREATED,
    EVENT_PE_DEPLOY_CREATED, EVENT_PE_HEALTH_WARNING,
    EVENT_PE_CONFIG_UPDATED, EVENT_PE_API_REQUEST,
    EVENT_PE_USER_CREATED, EVENT_PE_ENGINE_STARTED,
)
print("  event constants: PASSED")

# model dataclasses
from vnpy.platform_engineering.model import (
    MetricPoint, MetricSeries, AlertRecord, PlatformHealthScore,
    TaskRecord, WorkerRecord,
    DeployVersion, DeploymentRecord,
    HealthMetricSnapshot, StrategyHealthRecord,
    ConfigVersion, ConfigRecord,
    Permission, UserRecord, RoleRecord, AuditEntry,
)
mp = MetricPoint(metric_id="m1", name="cpu", value=42.5)
assert mp.value == 42.5
tr = TaskRecord(task_id="t1", name="backtest")
assert tr.status == TaskStatus.PENDING
print("  models: PASSED")

# repositories
from vnpy.platform_engineering.repository import (
    MetricRepository, TaskRepository, ConfigRepository,
)
repo = MetricRepository()
repo.append_point(mp)
assert len(repo.list_series()) == 1

trepo = TaskRepository()
trepo.save(tr)
assert trepo.get("t1") is not None
s = trepo.stats()
assert s["total"] == 1
print("  repositories: PASSED")

# sub-engines
from vnpy.platform_engineering.engine import (
    ObservabilityEngine, TaskEngine, DeploymentEngine,
    HealthEngine, ConfigEngine, ApiEngine, SecurityEngine,
)

# ObservabilityEngine
oe = ObservabilityEngine()
oe.start()
oe.record_metric(mp)
assert oe.get_health_score().score == 100.0
oe.stop()
print("  ObservabilityEngine: PASSED")

# TaskEngine
te = TaskEngine()
te.start()
task = te.create_task("回测任务", task_type=TaskType.BACKTEST,
                       priority=TaskPriority.HIGH)
assert task.status == TaskStatus.PENDING
assert te.get_task(task.task_id) is not None
te.cancel_task(task.task_id)
assert te.get_task(task.task_id).status == TaskStatus.CANCELLED
print("  TaskEngine: PASSED")

# DeploymentEngine
de = DeploymentEngine()
dep = de.create_deployment("STR-001", "MomentumAlpha", created_by="alice")
assert dep.current_stage == DeployStage.RESEARCH
de.advance_stage(dep.deploy_id, DeployStage.VALIDATION)
assert de.get_deployment(dep.deploy_id).current_stage == DeployStage.VALIDATION
ver = de.add_version(dep.deploy_id, "v1.0", note="首版")
assert ver is not None
s = de.stats()
assert s["total"] == 1
print("  DeploymentEngine: PASSED")

# HealthEngine
he = HealthEngine()
rec = he.register_strategy("STR-001", "MomentumAlpha")
assert rec.status == HealthStatus.UNKNOWN
s = he.stats()
assert s["total"] == 1
print("  HealthEngine: PASSED")

# ConfigEngine
ce = ConfigEngine()
cfg = ce.create_config("策略配置", config_type=ConfigType.STRATEGY,
                        data={"lookback": 20}, owner="alice")
assert cfg.current_data["lookback"] == 20
ver2 = ce.update_config(cfg.config_id, {"lookback": 30}, note="调参")
assert ver2 is not None
assert ce.get_config(cfg.config_id).current_data["lookback"] == 30
ok = ce.rollback_config(cfg.config_id, cfg.versions[0].version_id)
assert ok
assert ce.get_config(cfg.config_id).current_data["lookback"] == 20
print("  ConfigEngine: PASSED")

# ApiEngine
ae = ApiEngine()
ae.register("/health", lambda _: {"ok": True}, methods=["GET"])
result = ae.call("/health", "GET")
assert result["ok"] is True
s = ae.stats()
assert s["routes"] == 1
assert s["total_calls"] == 1
print("  ApiEngine: PASSED")

# SecurityEngine
se = SecurityEngine()
user = se.create_user("alice", role=UserRole.ANALYST)
assert se.get_user(user.user_id).username == "alice"
assert se.get_user_by_name("alice") is not None
entry = se.log_audit("alice", "deploy", "model", "M-001", success=True)
assert entry.actor == "alice"
logs = se.list_audits(actor="alice")
assert len(logs) == 1
print("  SecurityEngine: PASSED")

# utils
from vnpy.platform_engineering.utils import (
    get_system_metrics, format_bytes, health_color,
    next_run_from_cron, human_duration,
    bump_version, is_valid_version, compare_versions,
)
assert format_bytes(1536) == "1.5 KB"
assert health_color(90) == "#52c41a"
assert health_color(60) == "#faad14"
assert health_color(30) == "#ff4d4f"
assert bump_version("v1.2.3", "patch") == "v1.2.4"
assert bump_version("v1.2.3", "minor") == "v1.3.0"
assert bump_version("v1.2.3", "major") == "v2.0.0"
assert is_valid_version("v1.0.0")
assert not is_valid_version("1.0")
assert compare_versions("v1.2.3", "v1.2.4") == -1
assert compare_versions("v2.0.0", "v1.9.9") == 1
assert human_duration(3665) == "1h 1m 5s"
nxt = next_run_from_cron("*/5 * * * *")
assert nxt is not None
print("  utils: PASSED")

# App class
assert PlatformEngineeringApp.app_name == "PlatformEngineering"
assert PlatformEngineeringApp.engine_class is PlatformEngineeringEngine
print("  App class: PASSED")

# UI stub tabs (no QApp needed for class checks)
from vnpy.platform_engineering.ui.stub_tabs import (
    DashboardTab, ObservabilityTab, TaskTab, DeploymentTab,
    StrategyHealthTab, ConfigTab, ApiTab, SecurityTab, LogTab,
)
assert len([DashboardTab, ObservabilityTab, TaskTab, DeploymentTab,
            StrategyHealthTab, ConfigTab, ApiTab, SecurityTab, LogTab]) == 9
print("  UI stub tabs: PASSED")

print()
print("=== Phase 1 Smoke Test: ALL PASSED ===")
