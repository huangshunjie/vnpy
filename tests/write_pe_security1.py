"""write_pe_security_engine.py — append RBAC helpers + SecurityEngine"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\engine\security_engine.py"
)

PART1 = '''

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
            raise ValueError(f"\\u7528\\u6237\\u540d {username!r} \\u5df2\\u5b58\\u5728")
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
'''

ast.parse(PART1)
with open(P, "a", encoding="utf-8") as f:
    f.write(PART1)
print("Part1 OK")
