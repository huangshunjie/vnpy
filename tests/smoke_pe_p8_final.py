"""
smoke_pe_p8_final.py
Phase 8 + 全系统集成回归测试 (Phase 1-8)
"""
import time
from datetime import datetime

print("=" * 60)
print("Platform Engineering — Full Integration Smoke Test")
print("=" * 60)

# ═══════════════════════════════════════════════════════════
# PHASE 8 — Security & Permission Management
# ═══════════════════════════════════════════════════════════
print("\n── Phase 8: Security ──")

from vnpy.platform_engineering.engine.security_engine import (
    SecurityEngine, JwtTokenManager, TokenRecord,
    _hash_pw, _verify_pw,
)
from vnpy.platform_engineering.constant import UserRole, PermissionAction

# password hashing
h, s = _hash_pw("secret123")
assert _verify_pw("secret123", h, s)
assert not _verify_pw("wrong", h, s)
print("  password_hash: PASSED")

# JwtTokenManager
tm = JwtTokenManager(default_ttl=10)
tok = tm.issue("u1", "alice", UserRole.ADMIN)
assert tok.valid
assert tm.verify(tok.token_id) is not None
refreshed = tm.refresh(tok.token_id)
assert refreshed is not None
assert not tm.verify(tok.token_id)      # old revoked
assert tm.verify(refreshed.token_id)
tm.revoke(refreshed.token_id)
assert tm.verify(refreshed.token_id) is None
print(f"  JwtTokenManager: PASSED  stats={tm.stats()}")

# SecurityEngine — user CRUD
se = SecurityEngine()
alice = se.create_user("alice", "pw123", role=UserRole.ADMIN, created_by="system")
bob   = se.create_user("bob",   "pw456", role=UserRole.ANALYST)
carol = se.create_user("carol", "pw789", role=UserRole.VIEWER)
assert se.get_user_by_name("alice") is not None
assert len(se.list_users()) == 3
# duplicate username
try:
    se.create_user("alice", "x"); assert False, "should raise"
except ValueError: pass
print(f"  create_user: PASSED  count={len(se.list_users())}")

# authenticate
tok_alice = se.authenticate("alice", "pw123")
assert tok_alice is not None and tok_alice.valid
tok_fail  = se.authenticate("alice", "wrong")
assert tok_fail is None
print(f"  authenticate: PASSED  token={tok_alice.token_id[:16]}")

# verify_token
user_from_tok = se.verify_token(tok_alice.token_id)
assert user_from_tok.username == "alice"
print("  verify_token: PASSED")

# check_permission (ADMIN → always True)
assert se.check_permission(alice.user_id, "deployment", PermissionAction.ADMIN)
# ANALYST → READ on config
assert se.check_permission(bob.user_id, "config", PermissionAction.READ)
assert not se.check_permission(bob.user_id, "deployment", PermissionAction.DEPLOY)
print("  check_permission: PASSED")

# grant / revoke
se.grant_permission(carol.user_id, "task",
                    [PermissionAction.READ, PermissionAction.WRITE], operator="alice")
assert se.check_permission(carol.user_id, "task", PermissionAction.WRITE)
se.revoke_permission(carol.user_id, "task", operator="alice")
assert not se.check_permission(carol.user_id, "task", PermissionAction.WRITE)
print("  grant/revoke_permission: PASSED")

# assign_role
se.assign_role(carol.user_id, UserRole.MANAGER, operator="alice")
assert se.get_user(carol.user_id).role == UserRole.MANAGER
assert se.check_permission(carol.user_id, "deployment", PermissionAction.APPROVE)
print("  assign_role: PASSED")

# reset_password
se.reset_password(bob.user_id, "new_pass", operator="alice")
assert se.authenticate("bob", "new_pass") is not None
assert se.authenticate("bob", "pw456") is None
print("  reset_password: PASSED")

# disable / enable
se.disable_user(bob.user_id)
assert not se.get_user(bob.user_id).is_active
assert se.authenticate("bob", "new_pass") is None
se.enable_user(bob.user_id)
assert se.get_user(bob.user_id).is_active
print("  disable/enable_user: PASSED")

# logout
se.logout(tok_alice.token_id)
assert se.verify_token(tok_alice.token_id) is None
print("  logout: PASSED")

# audit log
audits = se.list_audits()
assert len(audits) >= 10
fail_audits = se.list_audits(success=False)
assert len(fail_audits) >= 1
print(f"  audit_log: PASSED  total={len(audits)}  failures={len(fail_audits)}")

# create_role
r = se.create_role("读写角色", role_type=UserRole.ANALYST, description="test")
assert r.role_id.startswith("ROLE-")
assert len(se.list_roles()) == 1
print(f"  create_role: PASSED  id={r.role_id}")

# delete_user
se.delete_user(carol.user_id, operator="alice")
assert se.get_user(carol.user_id) is None
print("  delete_user: PASSED")

# callback
events = []
se.on_auth_event(lambda u, ev, ok: events.append((u, ev, ok)))
dave = se.create_user("dave", "pw000", role=UserRole.VIEWER)
se.authenticate("dave", "pw000")
assert any(ev == "login" for _, ev, ok in events if ok)
print(f"  auth_callback: PASSED  events={len(events)}")

# make_api_auth_fn + ApiEngine integration
from vnpy.platform_engineering.engine.api_engine import ApiEngine
ae = ApiEngine()
ae.register("/secure/data", lambda req: {"data": "secret"},
            methods=["GET"], auth_required=True)

tok_dave = se.authenticate("dave", "pw000")
auth_fn  = se.make_api_auth_fn(resource="*", action=PermissionAction.READ)
ae.set_auth_fn(auth_fn)

# with valid Bearer token
resp_ok = ae.call("/secure/data", "GET",
                  headers={"Authorization": f"Bearer {tok_dave.token_id}"})
assert resp_ok.ok, f"expected 200, got {resp_ok.status_code}"

# with bad token
resp_bad = ae.call("/secure/data", "GET",
                   headers={"Authorization": "Bearer INVALID-TOKEN"})
assert resp_bad.status_code == 401
print(f"  api_auth_integration: PASSED  valid={resp_ok.status_code}  invalid={resp_bad.status_code}")

# stats
s = se.stats()
assert s["users"] >= 2
assert s["audit_logs"] >= 10
print(f"  stats: PASSED  {s}")

# UI imports
from vnpy.platform_engineering.ui.security import (
    SecurityTab, UserList, PermissionPanel, AuditPanel,
    CreateUserDialog, ResetPasswordDialog, AssignRoleDialog,
    ROLE_COLOR, ROLE_ICON, RESOURCES,
)
assert len(ROLE_COLOR) == 5
assert len(ROLE_ICON)  == 5
assert len(RESOURCES)  >= 5
assert hasattr(UserList,       "refresh")
assert hasattr(PermissionPanel,"load")
assert hasattr(AuditPanel,     "refresh")
assert hasattr(SecurityTab,    "_refresh")
print("  SecurityTab UI: PASSED")

# stub_tabs re-export
from vnpy.platform_engineering.ui.stub_tabs import (
    SecurityTab as ST2, DashboardTab, ObservabilityTab,
    TaskTab, DeploymentTab, StrategyHealthTab,
    ConfigTab, ApiTab, LogTab,
)
assert SecurityTab is ST2
print("  stub_tabs re-export: PASSED")

print("\n── Phase 1-7 Regression ──")

# Phase 1 — ObservabilityEngine
from vnpy.platform_engineering.engine.observability_engine import ObservabilityEngine
from vnpy.platform_engineering.constant import MetricLayer
oe = ObservabilityEngine()
pt = oe.make_point("cpu", 55.0, MetricLayer.SYSTEM)
oe.record_metric(pt)
assert oe.stats()["health_score"] == 100.0
print("  Phase1 observability: PASSED")

# Phase 2 — dashboard (import only)
from vnpy.platform_engineering.ui.dashboard import DashboardTab
from vnpy.platform_engineering.ui.monitor   import ObservabilityTab as OT
print("  Phase2 dashboard/monitor: PASSED")

# Phase 3 — TaskEngine
from vnpy.platform_engineering.engine.task_engine import TaskEngine
from vnpy.platform_engineering.constant import TaskType, TaskPriority
te = TaskEngine(num_workers=1, scheduler_interval=9999)
te.start()
t = te.create_task("p8_smoke", task_type=TaskType.CUSTOM,
                   priority=TaskPriority.HIGH)
assert t is not None
te.stop()
print("  Phase3 task_engine: PASSED")

# Phase 4 — DeploymentEngine
from vnpy.platform_engineering.engine.deployment_engine import DeploymentEngine
from vnpy.platform_engineering.constant import DeployStage
de = DeploymentEngine()
rec = de.create_deployment("STR-P8", "RegressionAlpha", created_by="smoke")
de.advance_stage(rec.deploy_id, DeployStage.VALIDATION)
assert de.get_deployment(rec.deploy_id).current_stage == DeployStage.VALIDATION
print("  Phase4 deployment_engine: PASSED")

# Phase 5 — HealthEngine
from vnpy.platform_engineering.engine.health_engine import HealthEngine
from vnpy.platform_engineering.model.health import HealthMetricSnapshot
he = HealthEngine()
he.register_strategy("S_P8", "RegressionStrat")
snap = HealthMetricSnapshot(
    sharpe=1.8, max_drawdown=0.07, win_rate=0.60,
    risk_exposure=0.18, ic_mean=0.07, alpha_decay=0.12,
    order_delay_ms=160.0, fill_rate=0.98, slippage_bps=4.0,
    updated_at=datetime.now(),
)
he.update_snapshot("S_P8", snap)
assert he.get_health("S_P8").score >= 80
print("  Phase5 health_engine: PASSED")

# Phase 6 — ConfigEngine
from vnpy.platform_engineering.engine.config_engine import ConfigEngine, ConfigDiffEngine
from vnpy.platform_engineering.constant import ConfigType
ce = ConfigEngine()
c = ce.create_config("p8_config", config_type=ConfigType.SYSTEM, data={"v": 1})
ce.update_config(c.config_id, {"v": 2})
entries, _ = ce.diff_with_current(c.config_id, c.versions[0].version_id)
assert len(entries) >= 1
print("  Phase6 config_engine: PASSED")

# Phase 7 — ApiEngine
from vnpy.platform_engineering.engine.api_engine import ApiEngine as AE2, ApiRouter
ae2 = AE2()
router = ApiRouter(prefix="/api/v1", group="test")
router.get("/ping", lambda req: {"pong": True})
router.post("/data", lambda req: {"ok": True})
ae2.include_router(router)
assert ae2.call("/api/v1/ping", "GET").ok
assert ae2.call("/api/v1/data", "POST").ok
assert ae2.call("/api/v1/ping", "DELETE").status_code == 405
print("  Phase7 api_engine: PASSED")

print()
print("=" * 60)
print("=== FULL INTEGRATION SMOKE TEST: ALL PASSED ===")
print("=" * 60)
