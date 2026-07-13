"""
research_ops/engine/governance_engine.py  — Phase 1 骨架
负责：审批流 / 版本冻结 / 发布管理 / 不可变审计日志。
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from ..constant import GovernanceStatus, AuditAction, Priority
from ..model.governance_model import ApprovalRequest, FreezeRecord, AuditLog
from ..repository.memory import InMemoryRepository
from ..utils.id_gen import gen_request_id, gen_freeze_id, gen_audit_id


class GovernanceEngine:
    def __init__(self) -> None:
        self._req_repo:    InMemoryRepository = InMemoryRepository()
        self._freeze_repo: InMemoryRepository = InMemoryRepository()
        self._audit_repo:  InMemoryRepository = InMemoryRepository()

    # ------------------------------------------------------------------
    # ApprovalRequest
    # ------------------------------------------------------------------

    def submit_request(
        self,
        title:       str,
        target_type: str,
        target_id:   str,
        target_name: str       = "",
        action:      str       = "",
        description: str       = "",
        priority:    Priority  = Priority.MEDIUM,
        requester:   str       = "",
    ) -> ApprovalRequest:
        req = ApprovalRequest(
            request_id  = gen_request_id(),
            title       = title,
            description = description,
            target_type = target_type,
            target_id   = target_id,
            target_name = target_name,
            action      = action,
            status      = GovernanceStatus.PENDING,
            priority    = priority,
            requester   = requester,
        )
        self._req_repo.save(req)
        self._log(requester, AuditAction.CREATE, target_type, target_id, target_name,
                  note=f"Submit approval request: {title}")
        return req

    def approve(
        self, request_id: str, approver: str, comment: str = ""
    ) -> None:
        req = self._req_repo.get(request_id)
        if req and req.status == GovernanceStatus.PENDING:
            req.status      = GovernanceStatus.APPROVED
            req.approver    = approver
            req.comment     = comment
            req.resolved_at = datetime.now()
            self._req_repo.save(req)
            self._log(approver, AuditAction.APPROVE,
                      req.target_type, req.target_id, req.target_name,
                      after={"comment": comment})

    def reject(
        self, request_id: str, approver: str, comment: str = ""
    ) -> None:
        req = self._req_repo.get(request_id)
        if req and req.status == GovernanceStatus.PENDING:
            req.status      = GovernanceStatus.REJECTED
            req.approver    = approver
            req.comment     = comment
            req.resolved_at = datetime.now()
            self._req_repo.save(req)
            self._log(approver, AuditAction.REJECT,
                      req.target_type, req.target_id, req.target_name,
                      after={"comment": comment})

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._req_repo.get(request_id)

    def list_requests(
        self,
        status:      Optional[GovernanceStatus] = None,
        requester:   Optional[str]              = None,
        target_type: Optional[str]              = None,
    ) -> List[ApprovalRequest]:
        result = self._req_repo.list()
        if status:      result = [r for r in result if r.status      == status]
        if requester:   result = [r for r in result if r.requester   == requester]
        if target_type: result = [r for r in result if r.target_type == target_type]
        return result

    def pending_requests(self) -> List[ApprovalRequest]:
        return self.list_requests(status=GovernanceStatus.PENDING)

    # ------------------------------------------------------------------
    # FreezeRecord（版本冻结）
    # ------------------------------------------------------------------

    def freeze(
        self,
        target_type: str,
        target_id:   str,
        target_name: str = "",
        version:     str = "",
        reason:      str = "",
        frozen_by:   str = "",
    ) -> FreezeRecord:
        rec = FreezeRecord(
            freeze_id   = gen_freeze_id(),
            target_type = target_type,
            target_id   = target_id,
            target_name = target_name,
            version     = version,
            reason      = reason,
            frozen_by   = frozen_by,
            is_active   = True,
        )
        self._freeze_repo.save(rec)
        self._log(frozen_by, AuditAction.FREEZE,
                  target_type, target_id, target_name,
                  after={"version": version, "reason": reason})
        return rec

    def unfreeze(
        self,
        freeze_id:   str,
        released_by: str = "",
    ) -> None:
        rec = self._freeze_repo.get(freeze_id)
        if rec and rec.is_active:
            rec.is_active   = False
            rec.released_by = released_by
            rec.released_at = datetime.now()
            self._freeze_repo.save(rec)
            self._log(released_by, AuditAction.RELEASE,
                      rec.target_type, rec.target_id, rec.target_name)

    def is_frozen(self, target_id: str) -> bool:
        return any(
            r.target_id == target_id and r.is_active
            for r in self._freeze_repo.list()
        )

    def list_freezes(
        self, active_only: bool = True
    ) -> List[FreezeRecord]:
        recs = self._freeze_repo.list()
        return [r for r in recs if r.is_active] if active_only else recs

    # ------------------------------------------------------------------
    # AuditLog（只追加，不允许修改/删除）
    # ------------------------------------------------------------------

    def _log(
        self,
        actor:       str,
        action:      AuditAction,
        target_type: str,
        target_id:   str,
        target_name: str             = "",
        before:      Optional[dict]  = None,
        after:       Optional[dict]  = None,
        note:        str             = "",
    ) -> AuditLog:
        log = AuditLog(
            log_id      = gen_audit_id(),
            actor       = actor,
            action      = action,
            target_type = target_type,
            target_id   = target_id,
            target_name = target_name,
            before      = before or {},
            after       = after  or {},
            note        = note,
        )
        self._audit_repo.save(log)
        return log

    def log_action(
        self,
        actor:       str,
        action:      AuditAction,
        target_type: str,
        target_id:   str,
        target_name: str            = "",
        before:      Optional[dict] = None,
        after:       Optional[dict] = None,
        note:        str            = "",
    ) -> AuditLog:
        """公开的审计日志写入接口，供外部 Engine 调用。"""
        return self._log(actor, action, target_type, target_id,
                         target_name, before, after, note)

    def list_audit_logs(
        self,
        target_id:   Optional[str]         = None,
        target_type: Optional[str]         = None,
        actor:       Optional[str]         = None,
        action:      Optional[AuditAction] = None,
        limit:       int                   = 200,
    ) -> List[AuditLog]:
        logs = sorted(
            self._audit_repo.list(),
            key=lambda l: l.timestamp,
            reverse=True,
        )
        if target_id:   logs = [l for l in logs if l.target_id   == target_id]
        if target_type: logs = [l for l in logs if l.target_type == target_type]
        if actor:       logs = [l for l in logs if l.actor       == actor]
        if action:      logs = [l for l in logs if l.action      == action]
        return logs[:limit]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        reqs = self._req_repo.list()
        return {
            "total_requests": len(reqs),
            "pending":    sum(1 for r in reqs if r.status == GovernanceStatus.PENDING),
            "approved":   sum(1 for r in reqs if r.status == GovernanceStatus.APPROVED),
            "rejected":   sum(1 for r in reqs if r.status == GovernanceStatus.REJECTED),
            "active_freezes": len(self.list_freezes(active_only=True)),
            "audit_logs": self._audit_repo.count(),
        }
