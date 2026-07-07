"""write_gov_main.py — GovernanceTab main class"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\governance_tab.py"
)

CODE = '''

class GovernanceTab(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # ── toolbar ───────────────────────────────────────────────
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_submit  = QPushButton("\\u2795  \\u63d0\\u4ea4\\u7533\\u8bf7")
        self._btn_approve = QPushButton("\\u2705  \\u5ba1\\u6279\\u901a\\u8fc7")
        self._btn_reject  = QPushButton("\\u274c  \\u62d2\\u7edd")
        self._btn_freeze  = QPushButton("\\U0001f512  \\u51bb\\u7ed3\\u8d44\\u4ea7")
        for btn in (self._btn_submit, self._btn_approve,
                    self._btn_reject, self._btn_freeze):
            btn.setFixedHeight(28); tb.addWidget(btn)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#dee2e6;"); tb.addWidget(sep)
        tb.addStretch()
        root.addLayout(tb)

        # ── stats bar ─────────────────────────────────────────────
        self._stats_bar = QLabel("\\u52a0\\u8f7d\\u4e2d...")
        self._stats_bar.setStyleSheet(
            "background:#fff3cd;border:1px solid #ffc107;"
            "border-radius:4px;padding:4px 10px;"
            "color:#856404;font-size:12px;")
        root.addWidget(self._stats_bar)

        # ── sub-tabs ──────────────────────────────────────────────
        self._sub = QTabWidget(); self._sub.setDocumentMode(True)

        # Tab1: approval list + detail
        appr_w = QWidget(); appr_l = QHBoxLayout(appr_w)
        appr_l.setContentsMargins(0, 0, 0, 0)
        sp = QSplitter(Qt.Horizontal)
        self._appr_list   = ApprovalList(self._engine)
        self._appr_detail = ApprovalDetail(self._engine)
        sp.addWidget(self._appr_list); sp.addWidget(self._appr_detail)
        sp.setSizes([280, 920])
        sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
        appr_l.addWidget(sp)
        self._sub.addTab(appr_w, "\\u2696\\ufe0f  \\u5ba1\\u6279\\u5de5\\u4f5c\\u6d41")

        # Tab2: freeze management
        self._freeze_panel = FreezePanel(self._engine)
        self._sub.addTab(self._freeze_panel, "\\U0001f512  \\u8d44\\u4ea7\\u51bb\\u7ed3")

        # Tab3: audit log
        self._audit_panel = AuditLogPanel(self._engine)
        self._sub.addTab(self._audit_panel, "\\U0001f4dc  \\u5ba1\\u8ba1\\u65e5\\u5fd7")

        root.addWidget(self._sub)

        # ── status bar ────────────────────────────────────────────
        self._status = QLabel("\\u5c31\\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        # ── connect ───────────────────────────────────────────────
        self._appr_list.selected.connect(self._on_appr_selected)

        self._btn_submit.clicked.connect(self._on_submit)
        self._btn_approve.clicked.connect(self._on_approve_toolbar)
        self._btn_reject.clicked.connect(self._on_reject_toolbar)
        self._btn_freeze.clicked.connect(self._on_freeze_toolbar)

        for ev in GOV_EVENTS:
            self._engine.event_engine.register(ev, self._on_gov_event)

        self._refresh_stats()

    # ── event ─────────────────────────────────────────────────────

    def _on_gov_event(self, _=None):
        self._refresh_stats()

    # ── selection ─────────────────────────────────────────────────

    def _on_appr_selected(self, req_id: str):
        self._appr_detail.load(req_id)
        req = self._engine.get_request(req_id)
        if req:
            self._set_status("\\u7533\\u8bf7: " + req.title
                             + "  [" + req.status.value + "]")

    # ── CRUD ──────────────────────────────────────────────────────

    def _on_submit(self):
        dlg = ApprovalDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            req = self._engine.submit_request(
                title=dlg.get_title(),
                target_type=dlg.get_target_type(),
                target_id=dlg.get_title(),         # use title as placeholder id
                target_name=dlg.get_target_name(),
                action=dlg.get_action(),
                description=dlg.get_description(),
                priority=dlg.get_priority(),
                requester=dlg.get_requester(),
            )
            self._set_status("\\u7533\\u8bf7\\u300c" + req.title + "\\u300d\\u5df2\\u63d0\\u4ea4")
            self._refresh_stats()

    def _on_approve_toolbar(self):
        rid = self._appr_list.selected_id()
        if not rid:
            self._set_status("\\u8bf7\\u5148\\u9009\\u62e9\\u7533\\u8bf7\\u6761\\u76ee"); return
        dlg = ReviewDialog(self, approve=True)
        if dlg.exec() == QDialog.Accepted:
            self._engine.approve(rid,
                approver=dlg.get_approver(),
                comment=dlg.get_comment())
            self._appr_detail.load(rid)
            self._set_status("\\u7533\\u8bf7\\u5df2\\u5ba1\\u6279\\u901a\\u8fc7")
            self._refresh_stats()

    def _on_reject_toolbar(self):
        rid = self._appr_list.selected_id()
        if not rid:
            self._set_status("\\u8bf7\\u5148\\u9009\\u62e9\\u7533\\u8bf7\\u6761\\u76ee"); return
        dlg = ReviewDialog(self, approve=False)
        if dlg.exec() == QDialog.Accepted:
            self._engine.reject(rid,
                approver=dlg.get_approver(),
                comment=dlg.get_comment())
            self._appr_detail.load(rid)
            self._set_status("\\u7533\\u8bf7\\u5df2\\u62d2\\u7edd")
            self._refresh_stats()

    def _on_freeze_toolbar(self):
        dlg = FreezeDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._engine.freeze(
                target_type=dlg.get_target_type(),
                target_id=dlg.get_target_id(),
                target_name=dlg.get_target_name(),
                version=dlg.get_version(),
                reason=dlg.get_reason(),
                frozen_by=dlg.get_frozen_by())
            self._set_status("\\u8d44\\u4ea7\\u5df2\\u51bb\\u7ed3")
            self._refresh_stats()

    # ── stats ─────────────────────────────────────────────────────

    def _refresh_stats(self):
        try:
            s = self._engine.stats()
        except Exception:
            return
        self._stats_bar.setText(
            "\\u5ba1\\u6279\\u7533\\u8bf7: " + str(s.get("total_requests", 0))
            + "    \\u5f85\\u5ba1\\u6279: " + str(s.get("pending", 0))
            + "    \\u5df2\\u901a\\u8fc7: " + str(s.get("approved", 0))
            + "    \\u5df2\\u62d2\\u7edd: " + str(s.get("rejected", 0))
            + "    \\u5df2\\u51bb\\u7ed3: " + str(s.get("active_freezes", 0))
            + "    \\u5ba1\\u8ba1\\u65e5\\u5fd7: " + str(s.get("audit_logs", 0)))

    def _set_status(self, msg: str):
        self._status.setText(msg)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("GovernanceTab main OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
