"""smoke_pe_p4.py — Phase 4 smoke test"""

# ── 1. DeploymentEngine 状态机 ────────────────────────────────────
from vnpy.platform_engineering.engine.deployment_engine import DeploymentEngine
from vnpy.platform_engineering.constant import DeployStage

de = DeploymentEngine()

# create
rec = de.create_deployment("STR-001", "MomentumAlpha", created_by="alice")
assert rec.current_stage == DeployStage.RESEARCH
assert len(rec.versions) == 1          # 初始快照
print(f"  create_deployment: PASSED  versions={len(rec.versions)}")

# advance RESEARCH -> VALIDATION
de.advance_stage(rec.deploy_id, DeployStage.VALIDATION, operator="alice")
rec = de.get_deployment(rec.deploy_id)
assert rec.current_stage == DeployStage.VALIDATION
print("  advance RESEARCH->VALIDATION: PASSED")

# submit for approval
de.submit_for_approval(rec.deploy_id, note="提交审批")
rec = de.get_deployment(rec.deploy_id)
assert rec.current_stage == DeployStage.APPROVAL
print("  submit_for_approval: PASSED")

# approve
de.approve(rec.deploy_id, approver="manager", note="已审核")
rec = de.get_deployment(rec.deploy_id)
assert rec.approver == "manager"
assert rec.approved_at is not None
print("  approve: PASSED")

# advance APPROVAL -> PAPER_TRADING (needs approver set)
de.advance_stage(rec.deploy_id, DeployStage.PAPER_TRADING, operator="alice")
rec = de.get_deployment(rec.deploy_id)
assert rec.current_stage == DeployStage.PAPER_TRADING
print("  advance ->PAPER_TRADING: PASSED")

# advance -> PRODUCTION
de.advance_stage(rec.deploy_id, DeployStage.PRODUCTION, operator="alice")
rec = de.get_deployment(rec.deploy_id)
assert rec.current_stage == DeployStage.PRODUCTION
assert rec.live_at is not None
print("  advance ->PRODUCTION: PASSED")

# invalid transition
try:
    de.advance_stage(rec.deploy_id, DeployStage.VALIDATION, operator="x")
    assert False, "should raise"
except ValueError:
    pass
print("  invalid_transition guard: PASSED")

# pause
de.advance_stage(rec.deploy_id, DeployStage.PAUSED, operator="ops")
rec = de.get_deployment(rec.deploy_id)
assert rec.current_stage == DeployStage.PAUSED
print("  pause: PASSED")

# rollback via version
first_ver = rec.versions[0].version_id
de.rollback_to_version(rec.deploy_id, first_ver, operator="ops")
rec = de.get_deployment(rec.deploy_id)
assert rec.current_stage == DeployStage.ROLLED_BACK
print("  rollback_to_version: PASSED")

# reject flow
rec2 = de.create_deployment("STR-002", "MeanReversion", created_by="bob")
de.advance_stage(rec2.deploy_id, DeployStage.VALIDATION)
de.submit_for_approval(rec2.deploy_id)
de.reject(rec2.deploy_id, approver="manager", note="不合规")
rec2 = de.get_deployment(rec2.deploy_id)
assert rec2.current_stage == DeployStage.VALIDATION
assert rec2.approver == ""
print("  reject: PASSED")

# freeze / unfreeze
de.freeze(rec2.deploy_id)
assert de.get_deployment(rec2.deploy_id).is_frozen
try:
    de.advance_stage(rec2.deploy_id, DeployStage.APPROVAL)
    assert False, "frozen should block"
except ValueError:
    pass
de.unfreeze(rec2.deploy_id)
assert not de.get_deployment(rec2.deploy_id).is_frozen
print("  freeze/unfreeze: PASSED")

# stats
s = de.stats()
assert s["total"] == 2
assert s["by_stage"]["rolled_back"] == 1
print(f"  stats: PASSED  {s}")

# callback
fired = []
de.on_stage_changed(lambda r, p: fired.append((r.deploy_id, p)))
rec3 = de.create_deployment("STR-003", "StatArb", created_by="charlie")
de.advance_stage(rec3.deploy_id, DeployStage.VALIDATION)
assert len(fired) >= 1
print(f"  stage_callback: PASSED  fired={len(fired)}")

# ── 2. add_version / list_deployments ─────────────────────────────
ver = de.add_version(rec.deploy_id, version_tag="v2.0",
                     note="hot-fix", created_by="alice")
assert ver is not None
assert ver.version_tag == "v2.0"
live_deps = de.list_deployments(stage=DeployStage.PRODUCTION)
assert len(live_deps) == 0   # rec is now ROLLED_BACK
print("  add_version / list_deployments: PASSED")

# ── 3. UI class imports ───────────────────────────────────────────
from vnpy.platform_engineering.ui.deployment import (
    DeploymentTab, DeployList, DetailPanel,
    CreateDeployDialog, AdvanceStageDialog, ApproveDialog,
    STAGE_COLOR, STAGE_ICON, ROLE_ID,
)
assert len(STAGE_COLOR) == 8
assert len(STAGE_ICON)  == 8
assert hasattr(DeployList,   "refresh")
assert hasattr(DetailPanel,  "load")
assert hasattr(DeploymentTab,"_refresh")
assert hasattr(CreateDeployDialog, "get_strategy_id")
assert hasattr(AdvanceStageDialog, "get_stage")
assert hasattr(ApproveDialog,      "get_approver")
print("  DeploymentTab UI: PASSED")

# ── 4. stub_tabs re-export ────────────────────────────────────────
from vnpy.platform_engineering.ui.stub_tabs import (
    DeploymentTab as DT2, DashboardTab, ObservabilityTab,
    TaskTab, LogTab, StrategyHealthTab, ConfigTab, ApiTab, SecurityTab,
)
assert DeploymentTab is DT2
print("  stub_tabs re-export: PASSED")

# ── 5. Phase 1-3 regression ──────────────────────────────────────
from vnpy.platform_engineering import PlatformEngineeringApp
from vnpy.platform_engineering.engine.task_engine import TaskEngine
te = TaskEngine(num_workers=1, scheduler_interval=9999)
te.start()
t = te.create_task("smoke_p4", created_by="test")
assert t is not None
te.stop()
print("  Phase1-3 regression: PASSED")

print()
print("=== Phase 4 Smoke Test: ALL PASSED ===")
