"""write_pe_security_ui2.py — append PermissionPanel + AuditPanel + SecurityTab"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\security.py"
)

CODE = '''

class PermissionPanel(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._uid    = None
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(6)

        hdr = QHBoxLayout()
        self._title = QLabel("\\u9009\\u62e9\\u7528\\u6237\\u67e5\\u770b\\u6743\\u9650")
        self._title.setStyleSheet("font-size:13px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._btn_save = QPushButton("\\U0001f4be  \\u4fdd\\u5b58\\u6743\\u9650")
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

        info_grp = QGroupBox("\\u89d2\\u8272\\u9ed8\\u8ba4\\u6743\\u9650\\u8bf4\\u660e")
        info_l   = QVBoxLayout(info_grp)
        self._info = QTextBrowser()
        self._info.setFixedHeight(80)
        self._info.setPlainText(
            "ADMIN: \\u5168\\u90e8\\u6743\\u9650\\n"
            "MANAGER: \\u90e8\\u7f72/\\u914d\\u7f6e/\\u4efb\\u52a1 \\u8bfb\\u5199 + \\u5ba1\\u6279\\n"
            "ANALYST: \\u914d\\u7f6e/\\u4efb\\u52a1/\\u5065\\u5eb7 \\u53ea\\u8bfb\\n"
            "TRADER:  \\u90e8\\u7f72 \\u53ef\\u6267\\u884c + \\u4efb\\u52a1 \\u8bfb\\u5199\\n"
            "VIEWER:  \\u5168\\u90e8\\u53ea\\u8bfb")
        info_l.addWidget(self._info)
        root.addWidget(info_grp, 1)

    def load(self, user_id: str):
        self._uid = user_id
        if not user_id or not self._engine:
            self._title.setText("\\u9009\\u62e9\\u7528\\u6237\\u67e5\\u770b\\u6743\\u9650")
            for cb in self._checkboxes.values(): cb.setChecked(False)
            return
        user = self._engine.security.get_user(user_id)
        if not user: return
        self._title.setText(
            f"{user.display_name} ({user.role.value}) \\u6743\\u9650\\u77e9\\u9635")
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
        self._actor_in.setPlaceholderText("\\u64cd\\u4f5c\\u4eba\\u8fc7\\u6ee4...")
        self._actor_in.setFixedHeight(26)
        self._actor_in.textChanged.connect(self.refresh)
        tb.addWidget(self._actor_in)
        self._res_in = QLineEdit()
        self._res_in.setPlaceholderText("\\u8d44\\u6e90\\u8fc7\\u6ee4...")
        self._res_in.setFixedHeight(26)
        self._res_in.textChanged.connect(self.refresh)
        tb.addWidget(self._res_in)
        self._success_combo = QComboBox(); self._success_combo.setFixedHeight(26)
        self._success_combo.addItem("\\u5168\\u90e8", None)
        self._success_combo.addItem("\\u6210\\u529f", True)
        self._success_combo.addItem("\\u5931\\u8d25", False)
        self._success_combo.currentIndexChanged.connect(self.refresh)
        tb.addWidget(self._success_combo)
        tb.addStretch()
        self._count_lbl = QLabel("0 \\u6761")
        self._count_lbl.setStyleSheet("font-size:11px;color:#8c8c8c;")
        tb.addWidget(self._count_lbl)
        root.addLayout(tb)
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            "\\u65f6\\u95f4","\\u64cd\\u4f5c\\u4eba","\\u64cd\\u4f5c","\\u8d44\\u6e90","\\u8be6\\u60c5","\\u7ed3\\u679c"])
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
            ok_lbl = "\\u2705" if log.success else "\\u274c"
            si = QTableWidgetItem(ok_lbl)
            si.setForeground(QBrush(QColor(
                "#52c41a" if log.success else "#ff4d4f")))
            self._table.setItem(r, 5, si)
        self._count_lbl.setText(f"{self._table.rowCount()} \\u6761")


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
        title = QLabel("\\U0001f512  Security & Permissions")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("font-size:11px;color:#8c8c8c;")
        hdr.addWidget(self._stats_lbl)
        btn = QPushButton("\\U0001f504 \\u5237\\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:12px;border:none;")
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
        self._sub.addTab(user_w, "\\U0001f465  \\u7528\\u6237\\u7ba1\\u7406")

        # audit tab
        self._audit_panel = AuditPanel(self._engine)
        self._sub.addTab(self._audit_panel, "\\U0001f4dc  \\u5ba1\\u8ba1\\u65e5\\u5fd7")

        root.addWidget(self._sub, 1)

        self._status = QLabel("\\u5c31\\u7eea")
        self._status.setStyleSheet("font-size:11px;color:#6c757d;")
        root.addWidget(self._status)

    def _on_user_selected(self, user_id: str):
        self._perm_panel.load(user_id)

    def _refresh(self):
        self._user_list.refresh()
        self._audit_panel.refresh()
        if self._engine:
            s = self._engine.security.stats()
            self._stats_lbl.setText(
                f"\\u7528\\u6237: {s.get('users',0)}"
                f"  \\u542f\\u7528: {s.get('active_users',0)}"
                f"  Token: {s.get('tokens',{}).get('active',0)}"
                f"  \\u5ba1\\u8ba1\\u6761\\u6570: {s.get('audit_logs',0)}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
'''

with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("SecurityTab OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
