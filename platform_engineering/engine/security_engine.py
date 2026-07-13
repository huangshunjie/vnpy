"""
platform_engineering/engine/security_engine.py
SecurityEngine 完整版 — Phase 8
"""
from __future__ import annotations
import hashlib, hmac, os, time, uuid
from collections import deque
from datetime import datetime
from typing import Callable, Dict, List, Optional

from ..model.permission import UserRecord, RoleRecord, AuditEntry, Permission
from ..constant import UserRole, PermissionAction


def _hash_pw(plain: str, salt: str = "") -> tuple:
    if not salt: salt = os.urandom(16).hex()
    dk = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100_000)
    return dk.hex(), salt

def _verify_pw(plain: str, hashed: str, salt: str) -> bool:
    dk, _ = _hash_pw(plain, salt)
    return hmac.compare_digest(dk, hashed)


class TokenRecord:
    __slots__ = ("token_id","user_id","username","role","issued_at","expires_at","revoked")
    def __init__(self, user_id, username, role, ttl=3600):
        self.token_id   = "TOK-" + uuid.uuid4().hex[:16].upper()
        self.user_id    = user_id
        self.username   = username
        self.role       = role
        self.issued_at  = time.time()
        self.expires_at = self.issued_at + ttl
        self.revoked    = False
    @property
    def valid(self) -> bool:
        return not self.revoked and time.time() < self.expires_at


class JwtTokenManager:
    def __init__(self, default_ttl: int = 3600):
        self._tokens: Dict[str, TokenRecord] = {}
        self._ttl = default_ttl

    def issue(self, user_id, username, role, ttl=0) -> TokenRecord:
        rec = TokenRecord(user_id, username, role, ttl or self._ttl)
        self._tokens[rec.token_id] = rec
        self._gc(); return rec

    def verify(self, token_id: str) -> Optional[TokenRecord]:
        rec = self._tokens.get(token_id)
        return rec if rec and rec.valid else None

    def revoke(self, token_id: str) -> bool:
        rec = self._tokens.get(token_id)
        if rec: rec.revoked = True; return True
        return False

    def revoke_all(self, user_id: str) -> int:
        n = 0
        for rec in self._tokens.values():
            if rec.user_id == user_id and rec.valid:
                rec.revoked = True; n += 1
        return n

    def refresh(self, token_id: str, ttl=0) -> Optional[TokenRecord]:
        old = self._tokens.get(token_id)
        if not old or not old.valid: return None
        old.revoked = True
        return self.issue(old.user_id, old.username, old.role, ttl or self._ttl)

    def list_active(self, user_id="") -> List[TokenRecord]:
        items = [r for r in self._tokens.values() if r.valid]
        return [r for r in items if r.user_id == user_id] if user_id else items

    def _gc(self):
        dead = [k for k,r in self._tokens.items() if r.revoked]
        for k in dead[:100]: del self._tokens[k]

    def stats(self) -> dict:
        active = sum(1 for r in self._tokens.values() if r.valid)
        return {"total": len(self._tokens), "active": active}


_ROLE_DEFAULTS = {
    UserRole.ADMIN:   [("*", [PermissionAction.ADMIN])],
    UserRole.MANAGER: [
        ("deployment", [PermissionAction.READ, PermissionAction.WRITE,
                        PermissionAction.DEPLOY, PermissionAction.APPROVE]),
        ("config",     [PermissionAction.READ, PermissionAction.WRITE]),
        ("task",       [PermissionAction.READ, PermissionAction.WRITE]),
    ],
    UserRole.ANALYST: [
        ("config", [PermissionAction.READ]),
        ("task",   [PermissionAction.READ, PermissionAction.WRITE]),
        ("health", [PermissionAction.READ]),
    ],
    UserRole.TRADER: [
        ("deployment", [PermissionAction.READ, PermissionAction.DEPLOY]),
        ("task",       [PermissionAction.READ, PermissionAction.WRITE]),
    ],
    UserRole.VIEWER: [("*", [PermissionAction.READ])],
}

def _default_perms(role: UserRole) -> List[Permission]:
    return [
        Permission(perm_id="PERM-"+uuid.uuid4().hex[:6].upper(),
                   resource=res, actions=list(acts))
        for res, acts in _ROLE_DEFAULTS.get(role, [])
    ]


class SecurityEngine:
    def __init__(self) -> None:
        self._users:   Dict[str, UserRecord] = {}
        self._by_name: Dict[str, str]        = {}
        self._passwd:  Dict[str, tuple]      = {}
        self._roles:   Dict[str, RoleRecord] = {}
        self._audits:  deque                 = deque(maxlen=10_000)
        self._tokens   = JwtTokenManager()
        self._callbacks: List[Callable] = []

    def start(self) -> None: pass
    def stop(self)  -> None: pass

    def on_auth_event(self, cb) -> None: self._callbacks.append(cb)
    def _fire(self, username, event, success):
        for cb in self._callbacks:
            try: cb(username, event, success)
            except Exception: pass

    # ── user CRUD ────────────────────────────────────────────────
    def create_user(self, username: str, password: str = "changeme",
                    display_name: str = "", email: str = "",
                    role: UserRole = UserRole.VIEWER,
                    created_by: str = "") -> UserRecord:
        if username in self._by_name:
            raise ValueError(f"\u7528\u6237\u540d {username!r} \u5df2\u5b58\u5728")
        user = UserRecord(
            user_id=      "USR-"+uuid.uuid4().hex[:8].upper(),
            username=     username,
            display_name= display_name or username,
            email=        email,
            role=         role,
            permissions=  _default_perms(role),
            is_active=    True,
            created_by=   created_by,
            created_at=   datetime.now(),
            updated_at=   datetime.now(),
        )
        hashed, salt = _hash_pw(password)
        self._passwd[user.user_id]  = (hashed, salt)
        self._users[user.user_id]   = user
        self._by_name[username]     = user.user_id
        self.log_audit(created_by or "system", "create_user",
                       "user", user.user_id, f"created {username}")
        return user

    def get_user(self, user_id: str) -> Optional[UserRecord]:
        return self._users.get(user_id)

    def get_user_by_name(self, username: str) -> Optional[UserRecord]:
        uid = self._by_name.get(username)
        return self._users.get(uid) if uid else None

    def list_users(self, active_only: bool = False) -> List[UserRecord]:
        items = list(self._users.values())
        if active_only: items = [u for u in items if u.is_active]
        return sorted(items, key=lambda u: u.username)

    def update_user(self, user: UserRecord) -> None:
        user.updated_at = datetime.now()
        self._users[user.user_id] = user

    def delete_user(self, user_id: str, operator: str = "") -> bool:
        user = self._users.pop(user_id, None)
        if not user: return False
        self._by_name.pop(user.username, None)
        self._passwd.pop(user_id, None)
        self._tokens.revoke_all(user_id)
        self.log_audit(operator or "system", "delete_user",
                       "user", user_id, f"deleted {user.username}")
        return True

    def disable_user(self, user_id: str, operator: str = "") -> bool:
        user = self._users.get(user_id)
        if not user: return False
        user.is_active = False; user.updated_at = datetime.now()
        self._tokens.revoke_all(user_id)
        self.log_audit(operator, "disable_user", "user", user_id,
                       f"disabled {user.username}")
        return True

    def enable_user(self, user_id: str, operator: str = "") -> bool:
        user = self._users.get(user_id)
        if not user: return False
        user.is_active = True; user.updated_at = datetime.now()
        self.log_audit(operator, "enable_user", "user", user_id,
                       f"enabled {user.username}")
        return True

    def reset_password(self, user_id: str, new_password: str,
                       operator: str = "") -> bool:
        if user_id not in self._users: return False
        hashed, salt = _hash_pw(new_password)
        self._passwd[user_id] = (hashed, salt)
        self._tokens.revoke_all(user_id)
        self.log_audit(operator, "reset_password", "user", user_id)
        return True

    def authenticate(self, username: str, password: str,
                     ip_address: str = ""):
        user = self.get_user_by_name(username)
        if not user or not user.is_active:
            self._fire(username, "login", False)
            self.log_audit(username, "login", "auth", "",
                           "not found/disabled", ip_address, False)
            return None
        hashed, salt = self._passwd.get(user.user_id, ("", ""))
        if not _verify_pw(password, hashed, salt):
            self._fire(username, "login", False)
            self.log_audit(username, "login", "auth", user.user_id,
                           "wrong password", ip_address, False)
            return None
        user.last_login = datetime.now()
        token = self._tokens.issue(user.user_id, username, user.role)
        self._fire(username, "login", True)
        self.log_audit(username, "login", "auth", user.user_id,
                       f"ok token={token.token_id[:12]}", ip_address, True)
        return token

    def logout(self, token_id: str) -> bool:
        rec = self._tokens.verify(token_id)
        if rec:
            self._tokens.revoke(token_id)
            self.log_audit(rec.username, "logout", "auth", rec.user_id)
            self._fire(rec.username, "logout", True)
            return True
        return False

    def verify_token(self, token_id: str):
        rec = self._tokens.verify(token_id)
        return self._users.get(rec.user_id) if rec else None

    def check_permission(self, user_id: str, resource: str,
                         action: PermissionAction) -> bool:
        user = self._users.get(user_id)
        if not user or not user.is_active: return False
        if user.role == UserRole.ADMIN: return True
        for perm in user.permissions:
            if perm.resource in (resource, "*") and perm.allows(action):
                return True
        return False

    def grant_permission(self, user_id: str, resource: str,
                         actions: List[PermissionAction],
                         operator: str = "") -> bool:
        user = self._users.get(user_id)
        if not user: return False
        existing = next((p for p in user.permissions
                         if p.resource == resource), None)
        if existing:
            for a in actions:
                if a not in existing.actions: existing.actions.append(a)
        else:
            user.permissions.append(Permission(
                perm_id="PERM-"+uuid.uuid4().hex[:6].upper(),
                resource=resource, actions=list(actions)))
        user.updated_at = datetime.now()
        self.log_audit(operator, "grant_permission", "user",
                       user_id, f"grant {resource}")
        return True

    def revoke_permission(self, user_id: str, resource: str,
                          operator: str = "") -> bool:
        user = self._users.get(user_id)
        if not user: return False
        user.permissions = [p for p in user.permissions
                            if p.resource != resource]
        user.updated_at  = datetime.now()
        self.log_audit(operator, "revoke_permission", "user",
                       user_id, f"revoke {resource}")
        return True

    def assign_role(self, user_id: str, role: UserRole,
                    operator: str = "") -> bool:
        user = self._users.get(user_id)
        if not user: return False
        user.role        = role
        user.permissions = _default_perms(role)
        user.updated_at  = datetime.now()
        self.log_audit(operator, "assign_role", "user",
                       user_id, f"role -> {role.value}")
        return True

    def create_role(self, name: str, role_type: UserRole = UserRole.VIEWER,
                    description: str = "",
                    permissions: List[Permission] = None) -> RoleRecord:
        role = RoleRecord(
            role_id=    "ROLE-"+uuid.uuid4().hex[:6].upper(),
            name=       name,
            role_type=  role_type,
            permissions=permissions or _default_perms(role_type),
            description=description,
            created_at= datetime.now(),
        )
        self._roles[role.role_id] = role
        return role

    def list_roles(self) -> List[RoleRecord]:
        return list(self._roles.values())

    def log_audit(self, actor: str, action: str, resource: str,
                  resource_id: str = "", detail: str = "",
                  ip_address: str = "", success: bool = True) -> AuditEntry:
        entry = AuditEntry(
            entry_id=    "AUD-"+uuid.uuid4().hex[:8].upper(),
            actor=       actor, action=action, resource=resource,
            resource_id= resource_id, detail=detail,
            ip_address=  ip_address, success=success,
            timestamp=   datetime.now(),
        )
        self._audits.appendleft(entry)
        return entry

    def list_audits(self, actor: Optional[str] = None,
                    resource: Optional[str] = None,
                    action: Optional[str] = None,
                    success: Optional[bool] = None,
                    limit: int = 200) -> List[AuditEntry]:
        items = list(self._audits)
        if actor:    items = [e for e in items if e.actor    == actor]
        if resource: items = [e for e in items if e.resource == resource]
        if action:   items = [e for e in items if e.action   == action]
        if success is not None:
            items = [e for e in items if e.success == success]
        return items[:limit]

    def make_api_auth_fn(self, resource: str = "*",
                         action: PermissionAction = PermissionAction.READ):
        def auth_fn(req) -> bool:
            auth = (req.headers or {}).get("Authorization", "")
            tid  = auth[7:] if auth.startswith("Bearer ") else auth
            if not tid: return False
            rec = self._tokens.verify(tid)
            if not rec: return False
            return self.check_permission(rec.user_id, resource, action)
        return auth_fn

    def stats(self) -> dict:
        return {
            "users":        len(self._users),
            "active_users": sum(1 for u in self._users.values() if u.is_active),
            "roles":        len(self._roles),
            "audit_logs":   len(self._audits),
            "tokens":       self._tokens.stats(),
        }
