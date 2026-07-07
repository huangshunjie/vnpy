"""write_gov_approval.py — ApprovalList + ApprovalDetail"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\governance_tab.py"
)

CODE = '''

class ApprovalList(QWidget):
    selected = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._filter  = "all"
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        fb = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItem("\\u5168\\u90e8", "all")
        self._combo.addItem("\\u5f85\\u5ba1\\u6279", "pending")
        self._combo.addItem("\\u5df2\\u901a\\u8fc7", "approved")
        self._combo.addItem("\\u5df2\\u62d2\\u7edd", "rejected")
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1); root.addLayout(fb)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\\u6807\\u9898","\\u8d44\\u4ea7\\u7c7b\\u578b","\\u4f18\\u5148\\u7ea7","\\u72b6\\u6001"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.itemClicked.connect(self._on_click)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in GOV_EVENTS:
            ee.register(ev, lambda _: self._refresh())

    def _on_filter(self, _): self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_requests()
        if self._filter == "pending":
            items = [r for r in items if r.status == GovernanceStatus.PENDING]
        elif self._filter == "approved":
            items = [r for r in items if r.status == GovernanceStatus.APPROVED]
        elif self._filter == "rejected":
            items = [r for r in items if r.status == GovernanceStatus.REJECTED]
        self._table.setRowCount(0)
        for req in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(req.title))
            self._table.setItem(r, 1, QTableWidgetItem(req.target_type))
            pc = PRIORITY_COLOR.get(req.priority, "#6c757d")
            pi = QTableWidgetItem(req.priority.value)
            pi.setForeground(QBrush(QColor(pc)))
            self._table.setItem(r, 2, pi)
            sc = STATUS_COLOR.get(req.status, "#6c757d")
            si = QTableWidgetItem(
                STATUS_ICON.get(req.status,"") + " " + req.status.value)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 3, si)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, req.request_id)

    def _on_click(self, item): self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        rid = item.data(ROLE_ID)
        req = self._engine.get_request(rid)
        if not req: return
        menu  = QMenu(self)
        a_app = menu.addAction("\\u2705  \\u5ba1\\u6279\\u901a\\u8fc7")
        a_rej = menu.addAction("\\u274c  \\u62d2\\u7edd")
        menu.addSeparator()
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_app:
            dlg = ReviewDialog(self, approve=True)
            if dlg.exec() == QDialog.Accepted:
                self._engine.approve(rid,
                    approver=dlg.get_approver(),
                    comment=dlg.get_comment())
                self._refresh()
        elif action == a_rej:
            dlg = ReviewDialog(self, approve=False)
            if dlg.exec() == QDialog.Accepted:
                self._engine.reject(rid,
                    approver=dlg.get_approver(),
                    comment=dlg.get_comment())
                self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class ApprovalDetail(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        hdr  = QHBoxLayout()
        self._title = QLabel("\\u8bf7\\u9009\\u62e9\\u5ba1\\u6279\\u7533\\u8bf7")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._badge = QLabel("")
        self._badge.setFixedHeight(22)
        self._badge.setStyleSheet("padding:2px 10px;border-radius:10px;font-size:12px;")
        hdr.addWidget(self._badge); root.addLayout(hdr)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        root.addWidget(self._bar)

        # action buttons
        ab = QHBoxLayout()
        self._btn_approve = QPushButton("\\u2705  \\u901a\\u8fc7")
        self._btn_approve.setStyleSheet(
            "background:#198754;color:#fff;border-radius:4px;")
        self._btn_reject  = QPushButton("\\u274c  \\u62d2\\u7edd")
        self._btn_reject.setStyleSheet(
            "background:#dc3545;color:#fff;border-radius:4px;")
        for b in (self._btn_approve, self._btn_reject):
            b.setFixedHeight(28); ab.addWidget(b)
        ab.addStretch(); root.addLayout(ab)

        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\\u5c5e\\u6027","\\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        self._info.setFixedHeight(200)
        root.addWidget(self._info)

        dg = QGroupBox("\\u7533\\u8bf7\\u8bf4\\u660e")
        dl = QVBoxLayout(dg)
        self._desc_view = QTextBrowser()
        self._desc_view.setFixedHeight(80)
        dl.addWidget(self._desc_view); root.addWidget(dg)

        cg = QGroupBox("\\u5ba1\\u6279\\u5907\\u6ce8")
        cl = QVBoxLayout(cg)
        self._comment_view = QTextBrowser()
        self._comment_view.setFixedHeight(60)
        cl.addWidget(self._comment_view); root.addWidget(cg)
        root.addStretch()

        self._btn_approve.clicked.connect(self._on_approve)
        self._btn_reject.clicked.connect(self._on_reject)

    def load(self, req_id: str):
        self._id = req_id
        req = self._engine.get_request(req_id)
        if not req: return
        self._title.setText(req.title)
        sc = STATUS_COLOR.get(req.status, "#6c757d")
        self._bar.setStyleSheet("background:"+sc+";border-radius:2px;")
        icon = STATUS_ICON.get(req.status, "")
        self._badge.setText(icon + " " + req.status.value)
        self._badge.setStyleSheet(
            "padding:2px 10px;border-radius:10px;"
            "background:"+sc+"22;color:"+sc+";"
            "font-size:12px;border:1px solid "+sc+"44;")
        is_pending = req.status == GovernanceStatus.PENDING
        self._btn_approve.setEnabled(is_pending)
        self._btn_reject.setEnabled(is_pending)
        self._info.setRowCount(0)
        res_at = req.resolved_at.strftime("%Y-%m-%d %H:%M") if req.resolved_at else "\\u2014"
        for k, v in [
            ("ID", req.request_id[:16]),
            ("\\u8d44\\u4ea7\\u7c7b\\u578b", req.target_type),
            ("\\u8d44\\u4ea7\\u540d\\u79f0", req.target_name or "\\u2014"),
            ("\\u64cd\\u4f5c", req.action or "\\u2014"),
            ("\\u4f18\\u5148\\u7ea7", req.priority.value),
            ("\\u7533\\u8bf7\\u4eba", req.requester or "\\u2014"),
            ("\\u5ba1\\u6279\\u4eba", req.approver or "\\u2014"),
            ("\\u89e3\\u51b3\\u65f6\\u95f4", res_at),
            ("\\u63d0\\u4ea4\\u65f6\\u95f4", req.submitted_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        self._desc_view.setPlainText(req.description or "")
        self._comment_view.setPlainText(req.comment or "")

    def clear_panel(self):
        self._id = None
        self._title.setText("\\u8bf7\\u9009\\u62e9\\u5ba1\\u6279\\u7533\\u8bf7")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        self._badge.setText(""); self._badge.setStyleSheet("")
        self._btn_approve.setEnabled(False); self._btn_reject.setEnabled(False)
        self._info.setRowCount(0)
        self._desc_view.clear(); self._comment_view.clear()

    def _on_approve(self):
        if not self._id: return
        dlg = ReviewDialog(self, approve=True)
        if dlg.exec() == QDialog.Accepted:
            self._engine.approve(self._id,
                approver=dlg.get_approver(), comment=dlg.get_comment())
            self.load(self._id)

    def _on_reject(self):
        if not self._id: return
        dlg = ReviewDialog(self, approve=False)
        if dlg.exec() == QDialog.Accepted:
            self._engine.reject(self._id,
                approver=dlg.get_approver(), comment=dlg.get_comment())
            self.load(self._id)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("ApprovalList+Detail OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
