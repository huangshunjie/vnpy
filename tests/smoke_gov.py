"""smoke_gov.py — Phase 9 smoke test"""
from vnpy.research_ops.engine.governance_engine import GovernanceEngine
from vnpy.research_ops.constant import Priority, AuditAction

ge = GovernanceEngine()

# 1. submit request
r1 = ge.submit_request(
    title="部署 LightGBM-v3",
    target_type="model", target_id="MODEL-001",
    target_name="LightGBM-v3",
    action="deploy",
    description="将模型部署至生产环境",
    priority=Priority.HIGH,
    requester="alice")
r2 = ge.submit_request(
    title="发布周报 2024-W52",
    target_type="report", target_id="RPT-001",
    target_name="周报 2024-W52",
    action="publish",
    requester="bob")
assert ge.get_request(r1.request_id).title == "部署 LightGBM-v3"
print("  submit_request: PASSED")

# 2. pending
pending = ge.pending_requests()
assert len(pending) == 2
print("  pending_requests: PASSED, count:", len(pending))

# 3. approve
ge.approve(r1.request_id, approver="manager", comment="已审核通过")
from vnpy.research_ops.constant import GovernanceStatus
assert ge.get_request(r1.request_id).status == GovernanceStatus.APPROVED
print("  approve: PASSED")

# 4. reject
ge.reject(r2.request_id, approver="manager", comment="内容不完整")
assert ge.get_request(r2.request_id).status == GovernanceStatus.REJECTED
print("  reject: PASSED")

# 5. stats
s = ge.stats()
assert s["total_requests"] == 2
assert s["approved"] == 1
assert s["rejected"] == 1
assert s["pending"] == 0
print("  stats:", s)
print("  stats: PASSED")

# 6. freeze / unfreeze
fr = ge.freeze("model", "MODEL-001", target_name="LightGBM-v3",
               version="v3", reason="等待生产验证", frozen_by="ops")
assert fr.is_active
assert ge.is_frozen("MODEL-001")
print("  freeze: PASSED")

ge.unfreeze(fr.freeze_id, released_by="ops")
assert not ge.is_frozen("MODEL-001")
active = ge.list_freezes(active_only=True)
assert len(active) == 0
print("  unfreeze: PASSED")

# 7. audit log
ge.log_action(actor="alice", action=AuditAction.DEPLOY,
              target_type="model", target_id="MODEL-001",
              target_name="LightGBM-v3", note="生产部署")
ge.log_action(actor="bob", action=AuditAction.CREATE,
              target_type="report", target_id="RPT-001",
              target_name="周报")
logs = ge.list_audit_logs()
assert len(logs) >= 2
actor_logs = ge.list_audit_logs(actor="alice")
assert all(l.actor == "alice" for l in actor_logs)
print("  audit_log: PASSED, total:", len(logs))

s2 = ge.stats()
assert s2["audit_logs"] >= 2
print("  stats after audit:", s2)
print("  stats audit: PASSED")

# 8. UI class imports
from vnpy.research_ops.ui.governance_tab import (
    GovernanceTab, ApprovalList, ApprovalDetail,
    FreezePanel, AuditLogPanel,
    ApprovalDialog, ReviewDialog, FreezeDialog,
    STATUS_COLOR, STATUS_ICON, PRIORITY_COLOR, GOV_EVENTS,
)
assert len(STATUS_COLOR) == 5
assert len(STATUS_ICON) == 5
assert len(PRIORITY_COLOR) == 4
assert len(GOV_EVENTS) == 6
assert hasattr(ApprovalDialog,  "get_title")
assert hasattr(ApprovalDialog,  "get_priority")
assert hasattr(ReviewDialog,    "get_approver")
assert hasattr(ReviewDialog,    "get_comment")
assert hasattr(FreezeDialog,    "get_reason")
assert hasattr(FreezeDialog,    "get_frozen_by")
assert hasattr(ApprovalList,    "selected_id")
assert hasattr(ApprovalDetail,  "load")
assert hasattr(FreezePanel,     "_refresh")
assert hasattr(AuditLogPanel,   "_refresh")
assert hasattr(GovernanceTab,   "_refresh_stats")
print("  UI class API: PASSED")

# 9. stub_tabs
from vnpy.research_ops.ui.stub_tabs import (
    GovernanceTab as GT2, WorkspaceTab, ExperimentTab,
    RegistryTab, PipelineTab, ReportTab, KnowledgeTab, DashboardTab,
)
assert GovernanceTab is GT2
print("  stub_tabs re-export: PASSED")

# 10. all 8 tabs importable together
tabs = [WorkspaceTab, ExperimentTab, RegistryTab, PipelineTab,
        ReportTab, KnowledgeTab, DashboardTab, GovernanceTab]
assert len(tabs) == 8
print("  all 8 tabs: PASSED")

print()
print("=== Phase 9 Smoke Test: ALL PASSED ===")
