"""write_pe_security2.py — append SecurityEngine auth + permission + audit"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\engine\security_engine.py"
)

PART2 = '''
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
'''

with open(P, "a", encoding="utf-8") as f:
    f.write(PART2)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("SecurityEngine OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
