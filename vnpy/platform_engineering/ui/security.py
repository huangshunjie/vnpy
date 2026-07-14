"""
platform_engineering/ui/security.py
SecurityTab — Phase 8
用户管理 + 角色权限矩阵 + 审计日志
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QTabWidget, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QLineEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QCheckBox, QMenu, QMessageBox,
    QTextBrowser,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush

if TYPE_CHECKING:
    from ..engine_main import PlatformEngine

from ..constant import UserRole, PermissionAction
from ..model.permission import UserRecord, Permission

ROLE_COLOR = {
    UserRole.ADMIN:   "#ff4d4f",
    UserRole.MANAGER: "#faad14",
    UserRole.ANALYST: "#1890ff",
    UserRole.TRADER:  "#722ed1",
    UserRole.VIEWER:  "#8c8c8c",
}
ROLE_ICON = {
    UserRole.ADMIN:   "👑",
    UserRole.MANAGER: "🔧",
    UserRole.ANALYST: "🔬",
    UserRole.TRADER:  "📈",
    UserRole.VIEWER:  "👁",
}
RESOURCES = ["*", "deployment", "config", "task", "health", "api"]
ROLE_ID_ROLE  = Qt.UserRole
ROLE_ID_USER  = Qt.UserRole + 1


class CreateUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u521b\u5efa\u7528\u6237")
        self.setMinimumWidth(400)
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u7528\u6237\u4fe1\u606f")
        form = QFormLayout(grp)
        self._uname = QLineEdit(); self._uname.setPlaceholderText("alice")
        form.addRow("\u7528\u6237\u540d *", self._uname)
        self._pwd   = QLineEdit(); self._pwd.setEchoMode(QLineEdit.Password)
        self._pwd.setPlaceholderText("\u5bc6\u7801")
        form.addRow("\u5bc6\u7801 *", self._pwd)
        self._dname = QLineEdit()
        form.addRow("\u663e\u793a\u540d\u79f0", self._dname)
        self._email = QLineEdit()
        form.addRow("\u90ae\u7b71", self._email)
        self._role  = QComboBox()
        for r in UserRole:
            self._role.addItem(ROLE_ICON.get(r,"")+" "+r.value, r)
        form.addRow("\u89d2\u8272", self._role)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u521b\u5efa")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
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
        self.setWindowTitle(f"\u91cd\u7f6e\u5bc6\u7801: {username}")
        self.setMinimumWidth(360)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._pwd  = QLineEdit(); self._pwd.setEchoMode(QLineEdit.Password)
        form.addRow("\u65b0\u5bc6\u7801 *", self._pwd)
        self._pwd2 = QLineEdit(); self._pwd2.setEchoMode(QLineEdit.Password)
        form.addRow("\u786e\u8ba4\u5bc6\u7801 *", self._pwd2)
        root.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u91cd\u7f6e")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._pwd.text():  self._pwd.setFocus(); return
        if self._pwd.text() != self._pwd2.text():
            QMessageBox.warning(self, "\u9519\u8bef", "\u4e24\u6b21\u5bc6\u7801\u4e0d\u4e00\u81f4")
            return
        self.accept()

    def get_password(self) -> str: return self._pwd.text()


class AssignRoleDialog(QDialog):
    def __init__(self, current_role: UserRole, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u4fee\u6539\u89d2\u8272")
        self.setMinimumWidth(320)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._role = QComboBox()
        for r in UserRole:
            self._role.addItem(ROLE_ICON.get(r,"")+" "+r.value, r)
        idx = self._role.findData(current_role)
        if idx >= 0: self._role.setCurrentIndex(idx)
        form.addRow("\u89d2\u8272", self._role)
        root.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u4fee\u6539")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
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
        self._btn_new = QPushButton("\u2795 \u65b0\u5efa\u7528\u6237")
        self._btn_new.setFixedHeight(26)
        self._btn_new.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_new.clicked.connect(self._on_new)
        tb.addWidget(self._btn_new)
        self._role_combo = QComboBox(); self._role_combo.setFixedHeight(26)
        self._role_combo.addItem("\u5168\u90e8\u89d2\u8272", None)
        for r in UserRole:
            self._role_combo.addItem(ROLE_ICON.get(r,"")+" "+r.value, r)
        self._role_combo.currentIndexChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._role_combo, 1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("\u641c\u7d22\u7528\u6237\u540d...")
        self._search.setFixedHeight(26)
        self._search.textChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._search)
        root.addLayout(tb)
        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "\u7528\u6237\u540d","\u663e\u793a\u540d\u79f0","\u89d2\u8272","\u72b6\u6001","\u6700\u540e\u767b\u5f55"])
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
            active_lbl = "\u2705 \u542f\u7528" if u.is_active else "\u274c \u7981\u7528"
            ac = QTableWidgetItem(active_lbl)
            ac.setForeground(QBrush(QColor("#52c41a" if u.is_active else "#ff4d4f")))
            self._table.setItem(r, 3, ac)
            ll = u.last_login.strftime("%m-%d %H:%M") if u.last_login else "\u2014"
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
                QMessageBox.warning(self, "\u9519\u8bef", str(e))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        uid  = item.data(ROLE_ID_USER)
        user = self._engine.security.get_user(uid)
        if not user: return
        menu = QMenu(self)
        a_role  = menu.addAction("\U0001f3ab  \u4fee\u6539\u89d2\u8272")
        a_pwd   = menu.addAction("\U0001f511  \u91cd\u7f6e\u5bc6\u7801")
        menu.addSeparator()
        a_tog   = menu.addAction(
            "\u274c  \u7981\u7528" if user.is_active else "\u2705  \u542f\u7528")
        a_del   = menu.addAction("\U0001f5d1  \u5220\u9664")
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
                    self, "\u786e\u8ba4\u5220\u9664",
                    f"\u786e\u8ba4\u5220\u9664\u7528\u6237 {user.username!r}?",
                    QMessageBox.Yes | QMessageBox.No
                ) == QMessageBox.Yes:
                    se.delete_user(uid, operator="admin")
        except Exception as e:
            QMessageBox.warning(self, "\u9519\u8bef", str(e))
        self.refresh()
        if self._on_select and act != a_del: self._on_select(uid)


class PermissionPanel(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._uid    = None
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(6)

        hdr = QHBoxLayout()
        self._title = QLabel("\u9009\u62e9\u7528\u6237\u67e5\u770b\u6743\u9650")
        self._title.setStyleSheet("font-size:14px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._btn_save = QPushButton("\U0001f4be  \u4fdd\u5b58\u6743\u9650")
        self._btn_save.setFixedHeight(26)
        self._btn_save.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_save.clicked.connect(self._on_save)
        hdr.addWidget(self._btn_save)
        root.addLayout(hdr)

        self._matrix = QTableWidget(len(RESOURCES), len(PermissionAction))
        self._matrix.setVerticalHeaderLabels(RESOURCES)
        self._matrix.setHorizontalHeaderLabels(
            [a.value for a in PermissionAction])
        self._matrix.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._matrix.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._matrix.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._matrix.setFixedHeight(220)
        self._checkboxes = {}
        for ri, res in enumerate(RESOURCES):
            for ci, act in enumerate(PermissionAction):
                cb = QCheckBox()
                cb.setStyleSheet("margin-left:14px;")
                cell = QWidget()
                cl = QHBoxLayout(cell); cl.setContentsMargins(0,0,0,0)
                cl.addWidget(cb)
                self._matrix.setCellWidget(ri, ci, cell)
                self._checkboxes[(res, act)] = cb
        root.addWidget(self._matrix)

        info_grp = QGroupBox("\u89d2\u8272\u9ed8\u8ba4\u6743\u9650\u8bf4\u660e")
        info_l   = QVBoxLayout(info_grp)
        self._info = QTextBrowser()
        self._info.setFixedHeight(80)
        self._info.setPlainText(
            "ADMIN: \u5168\u90e8\u6743\u9650\n"
            "MANAGER: \u90e8\u7f72/\u914d\u7f6e/\u4efb\u52a1 \u8bfb\u5199 + \u5ba1\u6279\n"
            "ANALYST: \u914d\u7f6e/\u4efb\u52a1/\u5065\u5eb7 \u53ea\u8bfb\n"
            "TRADER:  \u90e8\u7f72 \u53ef\u6267\u884c + \u4efb\u52a1 \u8bfb\u5199\n"
            "VIEWER:  \u5168\u90e8\u53ea\u8bfb")
        info_l.addWidget(self._info)
        root.addWidget(info_grp, 1)

    def load(self, user_id: str):
        self._uid = user_id
        if not user_id or not self._engine:
            self._title.setText("\u9009\u62e9\u7528\u6237\u67e5\u770b\u6743\u9650")
            for cb in self._checkboxes.values(): cb.setChecked(False)
            return
        user = self._engine.security.get_user(user_id)
        if not user: return
        self._title.setText(
            f"{user.display_name} ({user.role.value}) \u6743\u9650\u77e9\u9635")
        for (res, act), cb in self._checkboxes.items():
            has = self._engine.security.check_permission(user_id, res, act)
            cb.setChecked(has)

    def _on_save(self):
        if not self._uid or not self._engine: return
        se = self._engine.security
        for res in RESOURCES:
            checked_actions = [
                act for act in PermissionAction
                if self._checkboxes[(res, act)].isChecked()]
            if checked_actions:
                se.grant_permission(self._uid, res, checked_actions,
                                    operator="admin")
            else:
                se.revoke_permission(self._uid, res, operator="admin")
        self.load(self._uid)


class AuditPanel(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._actor_in = QLineEdit()
        self._actor_in.setPlaceholderText("\u64cd\u4f5c\u4eba\u8fc7\u6ee4...")
        self._actor_in.setFixedHeight(26)
        self._actor_in.textChanged.connect(self.refresh)
        tb.addWidget(self._actor_in)
        self._res_in = QLineEdit()
        self._res_in.setPlaceholderText("\u8d44\u6e90\u8fc7\u6ee4...")
        self._res_in.setFixedHeight(26)
        self._res_in.textChanged.connect(self.refresh)
        tb.addWidget(self._res_in)
        self._success_combo = QComboBox(); self._success_combo.setFixedHeight(26)
        self._success_combo.addItem("\u5168\u90e8", None)
        self._success_combo.addItem("\u6210\u529f", True)
        self._success_combo.addItem("\u5931\u8d25", False)
        self._success_combo.currentIndexChanged.connect(self.refresh)
        tb.addWidget(self._success_combo)
        tb.addStretch()
        self._count_lbl = QLabel("0 \u6761")
        self._count_lbl.setStyleSheet("font-size:14px;color:#8c8c8c;")
        tb.addWidget(self._count_lbl)
        root.addLayout(tb)
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            "\u65f6\u95f4","\u64cd\u4f5c\u4eba","\u64cd\u4f5c","\u8d44\u6e90","\u8be6\u60c5","\u7ed3\u679c"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        root.addWidget(self._table)

    def refresh(self):
        if not self._engine: return
        actor   = self._actor_in.text().strip() or None
        res     = self._res_in.text().strip() or None
        success = self._success_combo.currentData()
        logs = self._engine.security.list_audits(
            actor=actor, resource=res,
            success=success, limit=200)
        self._table.setRowCount(0)
        for log in logs:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0,
                QTableWidgetItem(log.timestamp.strftime("%m-%d %H:%M:%S")))
            self._table.setItem(r, 1, QTableWidgetItem(log.actor))
            self._table.setItem(r, 2, QTableWidgetItem(log.action))
            self._table.setItem(r, 3, QTableWidgetItem(log.resource))
            self._table.setItem(r, 4, QTableWidgetItem(log.detail[:40]))
            ok_lbl = "\u2705" if log.success else "\u274c"
            si = QTableWidgetItem(ok_lbl)
            si.setForeground(QBrush(QColor(
                "#52c41a" if log.success else "#ff4d4f")))
            self._table.setItem(r, 5, si)
        self._count_lbl.setText(f"{self._table.rowCount()} \u6761")


class SecurityTab(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(5_000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12); root.setSpacing(8)
        hdr = QHBoxLayout()
        title = QLabel("\U0001f512  Security & Permissions")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("font-size:14px;color:#8c8c8c;")
        hdr.addWidget(self._stats_lbl)
        btn = QPushButton("\U0001f504 \u5237\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:14px;border:none;")
        btn.clicked.connect(self._refresh)
        hdr.addWidget(btn)
        root.addLayout(hdr)

        self._sub = QTabWidget(); self._sub.setDocumentMode(True)

        # user management tab
        user_w = QWidget()
        user_l = QHBoxLayout(user_w); user_l.setContentsMargins(0, 4, 0, 0)
        sp = QSplitter(Qt.Horizontal)
        self._user_list   = UserList(self._engine)
        self._perm_panel  = PermissionPanel(self._engine)
        self._user_list.set_select_callback(self._on_user_selected)
        sp.addWidget(self._user_list)
        sp.addWidget(self._perm_panel)
        sp.setSizes([320, 880]); sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
        user_l.addWidget(sp)
        self._sub.addTab(user_w, "\U0001f465  \u7528\u6237\u7ba1\u7406")

        # audit tab
        self._audit_panel = AuditPanel(self._engine)
        self._sub.addTab(self._audit_panel, "\U0001f4dc  \u5ba1\u8ba1\u65e5\u5fd7")

        root.addWidget(self._sub, 1)

        self._status = QLabel("\u5c31\u7eea")
        self._status.setStyleSheet("font-size:14px;color:#6c757d;")
        root.addWidget(self._status)

    def _on_user_selected(self, user_id: str):
        self._perm_panel.load(user_id)

    def _refresh(self):
        self._user_list.refresh()
        self._audit_panel.refresh()
        if self._engine:
            s = self._engine.security.stats()
            self._stats_lbl.setText(
                f"\u7528\u6237: {s.get('users',0)}"
                f"  \u542f\u7528: {s.get('active_users',0)}"
                f"  Token: {s.get('tokens',{}).get('active',0)}"
                f"  \u5ba1\u8ba1\u6761\u6570: {s.get('audit_logs',0)}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
