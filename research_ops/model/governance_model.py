"""
research_ops/model/governance_model.py
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..constant import GovernanceStatus, AuditAction, Priority


@dataclass
class ApprovalRequest:
    request_id:   str              = ""
    title:        str              = ""
    description:  str              = ""
    target_type:  str              = ""
    target_id:    str              = ""
    target_name:  str              = ""
    action:       str              = ""
    status:       GovernanceStatus = GovernanceStatus.PENDING
    priority:     Priority         = Priority.MEDIUM
    requester:    str              = ""
    approver:     str              = ""
    comment:      str              = ""
    metadata:     Dict[str, Any]   = field(default_factory=dict)
    submitted_at: datetime         = field(default_factory=datetime.now)
    resolved_at:  Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "request_id":  self.request_id,
            "title":       self.title,
            "target_type": self.target_type,
            "target_id":   self.target_id,
            "action":      self.action,
            "status":      self.status.value,
            "requester":   self.requester,
            "submitted_at": self.submitted_at.isoformat(),
        }


@dataclass
class FreezeRecord:
    freeze_id:   str      = ""
    target_type: str      = ""
    target_id:   str      = ""
    target_name: str      = ""
    version:     str      = ""
    reason:      str      = ""
    frozen_by:   str      = ""
    frozen_at:   datetime = field(default_factory=datetime.now)
    released_by: str      = ""
    released_at: Optional[datetime] = None
    is_active:   bool     = True

    def to_dict(self) -> dict:
        return {
            "freeze_id":   self.freeze_id,
            "target_type": self.target_type,
            "target_id":   self.target_id,
            "version":     self.version,
            "is_active":   self.is_active,
            "frozen_by":   self.frozen_by,
            "frozen_at":   self.frozen_at.isoformat(),
        }


@dataclass
class AuditLog:
    log_id:      str         = ""
    actor:       str         = ""
    action:      AuditAction = AuditAction.CREATE
    target_type: str         = ""
    target_id:   str         = ""
    target_name: str         = ""
    before:      Dict[str, Any] = field(default_factory=dict)
    after:       Dict[str, Any] = field(default_factory=dict)
    ip_address:  str         = ""
    note:        str         = ""
    timestamp:   datetime    = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "log_id":      self.log_id,
            "actor":       self.actor,
            "action":      self.action.value,
            "target_type": self.target_type,
            "target_id":   self.target_id,
            "timestamp":   self.timestamp.isoformat(),
        }
