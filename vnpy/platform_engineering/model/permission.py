"""
platform_engineering/model/permission.py
用户/角色/权限/审计日志模型。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from ..constant import UserRole, PermissionAction


@dataclass
class Permission:
    perm_id:   str              = ""
    resource:  str              = ""   # e.g. "deployment", "config", "*"
    actions:   List[PermissionAction] = field(default_factory=list)

    def allows(self, action: PermissionAction) -> bool:
        return PermissionAction.ADMIN in self.actions or action in self.actions


@dataclass
class UserRecord:
    user_id:    str       = ""
    username:   str       = ""
    display_name: str     = ""
    email:      str       = ""
    role:       UserRole  = UserRole.VIEWER
    permissions: List[Permission] = field(default_factory=list)
    is_active:  bool      = True
    last_login: Optional[datetime] = None
    created_at: datetime  = field(default_factory=datetime.now)
    updated_at: datetime  = field(default_factory=datetime.now)
    created_by: str       = ""

    def to_dict(self) -> dict:
        return {
            "user_id":      self.user_id,
            "username":     self.username,
            "display_name": self.display_name,
            "role":         self.role.value,
            "is_active":    self.is_active,
            "created_at":   self.created_at.isoformat(),
        }


@dataclass
class RoleRecord:
    role_id:     str       = ""
    name:        str       = ""
    role_type:   UserRole  = UserRole.VIEWER
    permissions: List[Permission] = field(default_factory=list)
    description: str       = ""
    created_at:  datetime  = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "role_id":  self.role_id,
            "name":     self.name,
            "role_type": self.role_type.value,
        }


@dataclass
class AuditEntry:
    entry_id:    str      = ""
    actor:       str      = ""
    action:      str      = ""
    resource:    str      = ""
    resource_id: str      = ""
    detail:      str      = ""
    ip_address:  str      = ""
    success:     bool     = True
    timestamp:   datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "entry_id":    self.entry_id,
            "actor":       self.actor,
            "action":      self.action,
            "resource":    self.resource,
            "resource_id": self.resource_id,
            "detail":      self.detail,
            "success":     self.success,
            "timestamp":   self.timestamp.isoformat(),
        }
