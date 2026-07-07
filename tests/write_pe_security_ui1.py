"""write_pe_security_ui1.py — append dialogs + UserList"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\security.py"
)

CODE = '''

class CreateUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\\u521b\\u5efa\\u7528\\u6237")
        self.setMinimumWidth(400)
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u7528\\u6237\\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._uname = QLineEdit(); self._uname.setPlaceholderText("alice")
        form.addRow("\\u7528\\u6237\\u540d *", self._uname)
        self._pwd   = QLineEdit(); self._pwd.setEchoMode(QLineEdit.Password)
        self._pwd.setPlaceholderText("\\u5bc6\\u7801")
        form.addRow("\\u5bc6\\u7801 *", self._pwd)
        self._dname = QLineEdit()
        form.addRow("\\u663e\\u793a\\u540d\\u79f0", self._dname)
        self._email = QLineEdit()
        form.addRow("\\u90ae\\u7b71", self._email)
        self._role  = QComboBox()
        for r in UserRole:
            self._role.addItem(ROLE_ICON.get(r,"")+" "+r.value, r)
        form.addRow("\\u89d2\\u8272", self._role)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u521b\\u5efa")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._uname.text().strip(): self._uname.setFocus(); return
        if not self._pwd.text().strip():   self._pwd.setFocus();   return
        self.accept()

    def get_username(self)    -> str:      return self._uname.text().strip()
    def get_password(self)    -> str:      return self._pwd.text()
    def get_display_name(self) -> str:     return self._dname.text().strip()
    def get_email(self)       -> str:      return self._email.text().strip()
    def get_role(self)        -> UserRole: return self._role.currentData()


class ResetPasswordDialog(QDialog):
    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"\\u91cd\\u7f6e\\u5bc6\\u7801: {username}")
        self.setMinimumWidth(360)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._pwd  = QLineEdit(); self._pwd.setEchoMode(QLineEdit.Password)
        form.addRow("\\u65b0\\u5bc6\\u7801 *", self._pwd)
        self._pwd2 = QLineEdit(); self._pwd2.setEchoMode(QLineEdit.Password)
        form.addRow("\\u786e\\u8ba4\\u5bc6\\u7801 *", self._pwd2)
        root.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u91cd\\u7f6e")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._pwd.text():  self._pwd.setFocus(); return
        if self._pwd.text() != self._pwd2.text():
            QMessageBox.warning(self, "\\u9519\\u8bef", "\\u4e24\\u6b21\\u5bc6\\u7801\\u4e0d\\u4e00\\u81f4")
            return
        self.accept()

    def get_password(self) -> str: return self._pwd.text()


class AssignRoleDialog(QDialog):
    def __init__(self, current_role: UserRole, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\\u4fee\\u6539\\u89d2\\u8272")
        self.setMinimumWidth(320)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._role = QComboBox()
        for r in UserRole:
            self._role.addItem(ROLE_ICON.get(r,"")+" "+r.value, r)
        idx = self._role.findData(current_role)
        if idx >= 0: self._role.setCurrentIndex(idx)
        form.addRow("\\u89d2\\u8272", self._role)
        root.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u4fee\\u6539")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def get_role(self) -> UserRole: return self._role.currentData()


class UserList(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._on_select = None
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_new = QPushButton("\\u2795 \\u65b0\\u5efa\\u7528\\u6237")
        self._btn_new.setFixedHeight(26)
        self._btn_new.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_new.clicked.connect(self._on_new)
        tb.addWidget(self._btn_new)
        self._role_combo = QComboBox(); self._role_combo.setFixedHeight(26)
        self._role_combo.addItem("\\u5168\\u90e8\\u89d2\\u8272", None)
        for r in UserRole:
            self._role_combo.addItem(ROLE_ICON.get(r,"")+" "+r.value, r)
        self._role_combo.currentIndexChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._role_combo, 1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("\\u641c\\u7d22\\u7528\\u6237\\u540d...")
        self._search.setFixedHeight(26)
        self._search.textChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._search)
        root.addLayout(tb)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "\\u7528\\u6237\\u540d","\\u663e\\u793a\\u540d\\u79f0","\\u89d2\\u8272","\\u72b6\\u6001","\\u6700\\u540e\\u767b\\u5f55"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.itemClicked.connect(self._on_click)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

    def set_select_callback(self, cb): self._on_select = cb

    def refresh(self):
        if not self._engine: return
        role_filter = self._role_combo.currentData()
        kw          = self._search.text().strip().lower()
        users = self._engine.security.list_users()
        if role_filter: users = [u for u in users if u.role == role_filter]
        if kw: users = [u for u in users
                        if kw in u.username.lower() or kw in u.display_name.lower()]
        self._table.setRowCount(0)
        for u in users:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(u.username))
            self._table.setItem(r, 1, QTableWidgetItem(u.display_name))
            color = ROLE_COLOR.get(u.role, "#8c8c8c")
            icon  = ROLE_ICON.get(u.role, "")
            ri = QTableWidgetItem(icon+" "+u.role.value)
            ri.setForeground(QBrush(QColor(color)))
            self._table.setItem(r, 2, ri)
            active_lbl = "\\u2705 \\u542f\\u7528" if u.is_active else "\\u274c \\u7981\\u7528"
            ac = QTableWidgetItem(active_lbl)
            ac.setForeground(QBrush(QColor("#52c41a" if u.is_active else "#ff4d4f")))
            self._table.setItem(r, 3, ac)
            ll = u.last_login.strftime("%m-%d %H:%M") if u.last_login else "\\u2014"
            self._table.setItem(r, 4, QTableWidgetItem(ll))
            for c in range(5):
                self._table.item(r, c).setData(ROLE_ID_USER, u.user_id)

    def _on_click(self, item):
        if self._on_select: self._on_select(item.data(ROLE_ID_USER))

    def _on_new(self):
        if not self._engine: return
        dlg = CreateUserDialog(self)
        if dlg.exec() == QDialog.Accepted:
            try:
                self._engine.security.create_user(
                    username=dlg.get_username(),
                    password=dlg.get_password(),
                    display_name=dlg.get_display_name(),
                    email=dlg.get_email(),
                    role=dlg.get_role())
                self.refresh()
            except ValueError as e:
                QMessageBox.warning(self, "\\u9519\\u8bef", str(e))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        uid  = item.data(ROLE_ID_USER)
        user = self._engine.security.get_user(uid)
        if not user: return
        menu = QMenu(self)
        a_role  = menu.addAction("\\U0001f3ab  \\u4fee\\u6539\\u89d2\\u8272")
        a_pwd   = menu.addAction("\\U0001f511  \\u91cd\\u7f6e\\u5bc6\\u7801")
        menu.addSeparator()
        a_tog   = menu.addAction(
            "\\u274c  \\u7981\\u7528" if user.is_active else "\\u2705  \\u542f\\u7528")
        a_del   = menu.addAction("\\U0001f5d1  \\u5220\\u9664")
        act = menu.exec(self._table.viewport().mapToGlobal(pos))
        se = self._engine.security
        try:
            if act == a_role:
                dlg = AssignRoleDialog(user.role, self)
                if dlg.exec() == QDialog.Accepted:
                    se.assign_role(uid, dlg.get_role(), operator="admin")
            elif act == a_pwd:
                dlg = ResetPasswordDialog(user.username, self)
                if dlg.exec() == QDialog.Accepted:
                    se.reset_password(uid, dlg.get_password(), operator="admin")
            elif act == a_tog:
                se.disable_user(uid) if user.is_active else se.enable_user(uid)
            elif act == a_del:
                if QMessageBox.question(
                    self, "\\u786e\\u8ba4\\u5220\\u9664",
                    f"\\u786e\\u8ba4\\u5220\\u9664\\u7528\\u6237 {user.username!r}?",
                    QMessageBox.Yes | QMessageBox.No
                ) == QMessageBox.Yes:
                    se.delete_user(uid, operator="admin")
        except Exception as e:
            QMessageBox.warning(self, "\\u9519\\u8bef", str(e))
        self.refresh()
        if self._on_select and act != a_del: self._on_select(uid)
'''

with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("Part1 OK, lines:", len(full.splitlines()))
