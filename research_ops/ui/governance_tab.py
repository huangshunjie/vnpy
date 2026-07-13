"""
research_ops/ui/governance_tab.py  Phase 9 - Governance
"""
from __future__ import annotations
from typing import List, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QHeaderView, QAbstractItemView, QTabWidget,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QMenu, QMessageBox, QFrame,
    QTableWidget, QTableWidgetItem, QTextEdit,
    QTextBrowser,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QBrush

from ..main_engine import ResearchOpsEngine
from ..model.governance_model import ApprovalRequest, FreezeRecord, AuditLog
from ..constant import GovernanceStatus, Priority, AuditAction
from ..event import (
    EVENT_RO_GOV_SUBMITTED, EVENT_RO_GOV_APPROVED,
    EVENT_RO_GOV_REJECTED, EVENT_RO_GOV_FROZEN,
    EVENT_RO_GOV_RELEASED, EVENT_RO_AUDIT_LOGGED,
)

# ── colour tokens ─────────────────────────────────────────────────
STATUS_COLOR = {
    GovernanceStatus.PENDING:  "#fd7e14",
    GovernanceStatus.APPROVED: "#198754",
    GovernanceStatus.REJECTED: "#dc3545",
    GovernanceStatus.FROZEN:   "#4a6cf7",
    GovernanceStatus.RELEASED: "#6c757d",
}
STATUS_ICON = {
    GovernanceStatus.PENDING:  "⏳",
    GovernanceStatus.APPROVED: "✅",
    GovernanceStatus.REJECTED: "❌",
    GovernanceStatus.FROZEN:   "🔒",
    GovernanceStatus.RELEASED: "🔓",
}
PRIORITY_COLOR = {
    Priority.LOW:    "#6c757d",
    Priority.MEDIUM: "#fd7e14",
    Priority.HIGH:   "#dc3545",
    Priority.URGENT: "#9c27b0",
}
ROLE_ID = Qt.UserRole
GOV_EVENTS = [
    EVENT_RO_GOV_SUBMITTED, EVENT_RO_GOV_APPROVED,
    EVENT_RO_GOV_REJECTED, EVENT_RO_GOV_FROZEN,
    EVENT_RO_GOV_RELEASED, EVENT_RO_AUDIT_LOGGED,
]


# =================================================================
# ApprovalDialog
# =================================================================

class ApprovalDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u63d0\u4ea4\u5ba1\u6279\u7533\u8bf7")
        self.setMinimumWidth(480)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u7533\u8bf7\u4fe1\u606f")
        form = QFormLayout(grp)
        self._title = QLineEdit()
        self._title.setPlaceholderText("\u7533\u8bf7\u6807\u9898")
        form.addRow("\u6807\u9898 *", self._title)
        self._target_type = QLineEdit()
        self._target_type.setPlaceholderText("model / strategy / dataset ...")
        form.addRow("\u8d44\u4ea7\u7c7b\u578b *", self._target_type)
        self._target_name = QLineEdit()
        form.addRow("\u8d44\u4ea7\u540d\u79f0", self._target_name)
        self._action = QLineEdit()
        self._action.setPlaceholderText("deploy / retire / publish ...")
        form.addRow("\u64cd\u4f5c", self._action)
        self._priority = QComboBox()
        for p in Priority:
            self._priority.addItem(p.value, p)
        self._priority.setCurrentIndex(1)
        form.addRow("\u4f18\u5148\u7ea7", self._priority)
        self._requester = QLineEdit()
        form.addRow("\u7533\u8bf7\u4eba", self._requester)
        root.addWidget(grp)
        desc_grp = QGroupBox("\u7533\u8bf7\u8bf4\u660e")
        dl = QVBoxLayout(desc_grp)
        self._desc = QTextEdit(); self._desc.setFixedHeight(80)
        dl.addWidget(self._desc)
        root.addWidget(desc_grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u63d0\u4ea4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _on_ok(self):
        if not self._title.text().strip(): self._title.setFocus(); return
        if not self._target_type.text().strip(): self._target_type.setFocus(); return
        self.accept()

    def get_title(self)       -> str:     return self._title.text().strip()
    def get_target_type(self) -> str:     return self._target_type.text().strip()
    def get_target_name(self) -> str:     return self._target_name.text().strip()
    def get_action(self)      -> str:     return self._action.text().strip()
    def get_priority(self)    -> Priority: return self._priority.currentData()
    def get_requester(self)   -> str:     return self._requester.text().strip()
    def get_description(self) -> str:     return self._desc.toPlainText().strip()


# =================================================================
# ReviewDialog  — approve / reject with comment
# =================================================================

class ReviewDialog(QDialog):
    def __init__(self, parent=None, approve: bool = True):
        super().__init__(parent)
        self._approve = approve
        self.setWindowTitle(
            "\u5ba1\u6279\u901a\u8fc7" if approve else "\u62d2\u7edd\u7533\u8bf7")
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._approver = QLineEdit()
        form.addRow("\u5ba1\u6279\u4eba *", self._approver)
        root.addLayout(form)
        cg = QGroupBox("\u5907\u6ce8 / \u539f\u56e0")
        cl = QVBoxLayout(cg)
        self._comment = QTextEdit(); self._comment.setFixedHeight(80)
        cl.addWidget(self._comment)
        root.addWidget(cg)
        lbl = "\u786e\u8ba4\u901a\u8fc7" if self._approve else "\u786e\u8ba4\u62d2\u7edd"
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText(lbl)
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        if not self._approve:
            btns.button(QDialogButtonBox.Ok).setStyleSheet(
                "background:#dc3545;color:#fff;border-radius:4px;")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _on_ok(self):
        if not self._approver.text().strip(): self._approver.setFocus(); return
        self.accept()

    def get_approver(self) -> str: return self._approver.text().strip()
    def get_comment(self)  -> str: return self._comment.toPlainText().strip()


# =================================================================
# FreezeDialog
# =================================================================

class FreezeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u51bb\u7ed3\u8d44\u4ea7")
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._target_type = QLineEdit()
        self._target_type.setPlaceholderText("model / strategy / dataset")
        form.addRow("\u8d44\u4ea7\u7c7b\u578b *", self._target_type)
        self._target_id = QLineEdit()
        form.addRow("\u8d44\u4ea7 ID *", self._target_id)
        self._target_name = QLineEdit()
        form.addRow("\u8d44\u4ea7\u540d\u79f0", self._target_name)
        self._version = QLineEdit()
        form.addRow("\u7248\u672c", self._version)
        self._frozen_by = QLineEdit()
        form.addRow("\u64cd\u4f5c\u4eba *", self._frozen_by)
        root.addLayout(form)
        rg = QGroupBox("\u51bb\u7ed3\u539f\u56e0 *")
        rl = QVBoxLayout(rg)
        self._reason = QTextEdit(); self._reason.setFixedHeight(72)
        rl.addWidget(self._reason)
        root.addWidget(rg)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u51bb\u7ed3")
        btns.button(QDialogButtonBox.Ok).setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _on_ok(self):
        for w in (self._target_type, self._target_id, self._frozen_by):
            if not w.text().strip(): w.setFocus(); return
        if not self._reason.toPlainText().strip():
            self._reason.setFocus(); return
        self.accept()

    def get_target_type(self) -> str: return self._target_type.text().strip()
    def get_target_id(self)   -> str: return self._target_id.text().strip()
    def get_target_name(self) -> str: return self._target_name.text().strip()
    def get_version(self)     -> str: return self._version.text().strip()
    def get_frozen_by(self)   -> str: return self._frozen_by.text().strip()
    def get_reason(self)      -> str: return self._reason.toPlainText().strip()


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
        self._combo.addItem("\u5168\u90e8", "all")
        self._combo.addItem("\u5f85\u5ba1\u6279", "pending")
        self._combo.addItem("\u5df2\u901a\u8fc7", "approved")
        self._combo.addItem("\u5df2\u62d2\u7edd", "rejected")
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1); root.addLayout(fb)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\u6807\u9898","\u8d44\u4ea7\u7c7b\u578b","\u4f18\u5148\u7ea7","\u72b6\u6001"])
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
        a_app = menu.addAction("\u2705  \u5ba1\u6279\u901a\u8fc7")
        a_rej = menu.addAction("\u274c  \u62d2\u7edd")
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
        self._title = QLabel("\u8bf7\u9009\u62e9\u5ba1\u6279\u7533\u8bf7")
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
        self._btn_approve = QPushButton("\u2705  \u901a\u8fc7")
        self._btn_approve.setStyleSheet(
            "background:#198754;color:#fff;border-radius:4px;")
        self._btn_reject  = QPushButton("\u274c  \u62d2\u7edd")
        self._btn_reject.setStyleSheet(
            "background:#dc3545;color:#fff;border-radius:4px;")
        for b in (self._btn_approve, self._btn_reject):
            b.setFixedHeight(28); ab.addWidget(b)
        ab.addStretch(); root.addLayout(ab)

        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        self._info.setFixedHeight(200)
        root.addWidget(self._info)

        dg = QGroupBox("\u7533\u8bf7\u8bf4\u660e")
        dl = QVBoxLayout(dg)
        self._desc_view = QTextBrowser()
        self._desc_view.setFixedHeight(80)
        dl.addWidget(self._desc_view); root.addWidget(dg)

        cg = QGroupBox("\u5ba1\u6279\u5907\u6ce8")
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
        res_at = req.resolved_at.strftime("%Y-%m-%d %H:%M") if req.resolved_at else "\u2014"
        for k, v in [
            ("ID", req.request_id[:16]),
            ("\u8d44\u4ea7\u7c7b\u578b", req.target_type),
            ("\u8d44\u4ea7\u540d\u79f0", req.target_name or "\u2014"),
            ("\u64cd\u4f5c", req.action or "\u2014"),
            ("\u4f18\u5148\u7ea7", req.priority.value),
            ("\u7533\u8bf7\u4eba", req.requester or "\u2014"),
            ("\u5ba1\u6279\u4eba", req.approver or "\u2014"),
            ("\u89e3\u51b3\u65f6\u95f4", res_at),
            ("\u63d0\u4ea4\u65f6\u95f4", req.submitted_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        self._desc_view.setPlainText(req.description or "")
        self._comment_view.setPlainText(req.comment or "")

    def clear_panel(self):
        self._id = None
        self._title.setText("\u8bf7\u9009\u62e9\u5ba1\u6279\u7533\u8bf7")
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


class FreezePanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._show_all = False
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_freeze   = QPushButton("\U0001f512  \u51bb\u7ed3\u8d44\u4ea7")
        self._btn_unfreeze = QPushButton("\U0001f513  \u89e3\u51bb\u7ed3")
        self._chk_all      = QPushButton("\u663e\u793a\u5df2\u91ca\u653e")
        self._chk_all.setCheckable(True)
        for b in (self._btn_freeze, self._btn_unfreeze, self._chk_all):
            b.setFixedHeight(26); tb.addWidget(b)
        tb.addStretch(); root.addLayout(tb)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            "\u8d44\u4ea7\u7c7b\u578b","\u8d44\u4ea7\u540d\u79f0","\u7248\u672c",
            "\u51bb\u7ed3\u4eba","\u51bb\u7ed3\u65f6\u95f4","\u72b6\u6001"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

        # detail panel
        dg = QGroupBox("\u51bb\u7ed3\u8be6\u60c5")
        dl = QVBoxLayout(dg)
        self._detail = QTableWidget(0, 2)
        self._detail.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._detail.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._detail.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._detail.setAlternatingRowColors(True)
        self._detail.verticalHeader().setVisible(False)
        self._detail.setFixedHeight(140)
        dl.addWidget(self._detail)
        root.addWidget(dg)

        self._table.itemClicked.connect(self._on_click)
        self._btn_freeze.clicked.connect(self._on_freeze)
        self._btn_unfreeze.clicked.connect(self._on_unfreeze)
        self._chk_all.toggled.connect(self._on_toggle_all)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in GOV_EVENTS:
            ee.register(ev, lambda _: self._refresh())

    def _on_toggle_all(self, checked): self._show_all = checked; self._refresh()

    def _refresh(self):
        items = self._engine.list_freezes(active_only=not self._show_all)
        self._table.setRowCount(0)
        for fr in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(fr.target_type))
            self._table.setItem(r, 1, QTableWidgetItem(fr.target_name or fr.target_id[:12]))
            self._table.setItem(r, 2, QTableWidgetItem(fr.version or "\u2014"))
            self._table.setItem(r, 3, QTableWidgetItem(fr.frozen_by or "\u2014"))
            self._table.setItem(r, 4,
                QTableWidgetItem(fr.frozen_at.strftime("%Y-%m-%d %H:%M")))
            if fr.is_active:
                si = QTableWidgetItem("\U0001f512 \u5df2\u51bb\u7ed3")
                si.setForeground(QBrush(QColor("#4a6cf7")))
            else:
                si = QTableWidgetItem("\U0001f513 \u5df2\u91ca\u653e")
                si.setForeground(QBrush(QColor("#6c757d")))
            self._table.setItem(r, 5, si)
            for c in range(6):
                self._table.item(r, c).setData(ROLE_ID, fr.freeze_id)

    def _on_click(self, item):
        fid = item.data(ROLE_ID)
        frs = self._engine.list_freezes(active_only=False)
        fr  = next((f for f in frs if f.freeze_id == fid), None)
        if not fr: return
        self._detail.setRowCount(0)
        rel_at = fr.released_at.strftime("%Y-%m-%d %H:%M") if fr.released_at else "\u2014"
        for k, v in [
            ("ID", fr.freeze_id[:16]),
            ("\u8d44\u4ea7\u7c7b\u578b", fr.target_type),
            ("\u8d44\u4ea7 ID",    fr.target_id[:16]),
            ("\u51bb\u7ed3\u4eba", fr.frozen_by or "\u2014"),
            ("\u51bb\u7ed3\u65f6\u95f4", fr.frozen_at.strftime("%Y-%m-%d %H:%M")),
            ("\u91ca\u653e\u4eba", fr.released_by or "\u2014"),
            ("\u91ca\u653e\u65f6\u95f4", rel_at),
            ("\u51bb\u7ed3\u539f\u56e0", fr.reason or "\u2014"),
        ]:
            r = self._detail.rowCount(); self._detail.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._detail.setItem(r, 0, ki)
            self._detail.setItem(r, 1, QTableWidgetItem(str(v)))

    def _selected_freeze_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None

    def _on_freeze(self):
        dlg = FreezeDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._engine.freeze(
                target_type=dlg.get_target_type(),
                target_id=dlg.get_target_id(),
                target_name=dlg.get_target_name(),
                version=dlg.get_version(),
                reason=dlg.get_reason(),
                frozen_by=dlg.get_frozen_by())
            self._refresh()

    def _on_unfreeze(self):
        fid = self._selected_freeze_id()
        if not fid:
            QMessageBox.information(
                self, "\u63d0\u793a", "\u8bf7\u5148\u9009\u62e9\u8981\u89e3\u51bb\u7ed3\u7684\u8bb0\u5f55")
            return
        released_by, ok = self._prompt_user("\u89e3\u51bb\u7ed3\u64cd\u4f5c\u4eba:")
        if ok and released_by:
            self._engine.unfreeze(fid, released_by=released_by)
            self._refresh()

    @staticmethod
    def _prompt_user(prompt: str):
        from PySide6.QtWidgets import QInputDialog
        return QInputDialog.getText(None, "\u8f93\u5165", prompt)

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        fid = item.data(ROLE_ID)
        menu    = QMenu(self)
        a_thaw  = menu.addAction("\U0001f513  \u89e3\u51bb\u7ed3")
        if menu.exec(self._table.viewport().mapToGlobal(pos)) == a_thaw:
            released_by, ok = self._prompt_user("\u89e3\u51bb\u7ed3\u64cd\u4f5c\u4eba:")
            if ok and released_by:
                self._engine.unfreeze(fid, released_by=released_by)
                self._refresh()


class AuditLogPanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        fb = QHBoxLayout(); fb.setSpacing(6)
        self._actor_box = QLineEdit()
        self._actor_box.setPlaceholderText("\u64cd\u4f5c\u4eba\u8fc7\u6ee4")
        self._actor_box.setFixedHeight(26)
        fb.addWidget(self._actor_box, 1)
        self._type_box = QLineEdit()
        self._type_box.setPlaceholderText("\u8d44\u4ea7\u7c7b\u578b\u8fc7\u6ee4")
        self._type_box.setFixedHeight(26)
        fb.addWidget(self._type_box, 1)
        self._btn_filter = QPushButton("\u8fc7\u6ee4")
        self._btn_filter.setFixedHeight(26)
        self._btn_filter.clicked.connect(self._refresh)
        fb.addWidget(self._btn_filter)
        self._btn_clear = QPushButton("\u91cd\u7f6e")
        self._btn_clear.setFixedHeight(26)
        self._btn_clear.clicked.connect(self._on_clear_filter)
        fb.addWidget(self._btn_clear)
        root.addLayout(fb)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels([
            "\u65f6\u95f4","\u64cd\u4f5c\u4eba","\u64cd\u4f5c",
            "\u8d44\u4ea7\u7c7b\u578b","\u8d44\u4ea7\u540d\u79f0"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.itemClicked.connect(self._on_click)
        root.addWidget(self._table)

        dg = QGroupBox("\u65e5\u5fd7\u8be6\u60c5")
        dl = QVBoxLayout(dg)
        self._detail = QTableWidget(0, 2)
        self._detail.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._detail.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._detail.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._detail.setAlternatingRowColors(True)
        self._detail.verticalHeader().setVisible(False)
        self._detail.setFixedHeight(140)
        dl.addWidget(self._detail)
        root.addWidget(dg)

    def _register_events(self):
        ee = self._engine.event_engine
        for ev in GOV_EVENTS:
            ee.register(ev, lambda _: self._refresh())

    def _on_clear_filter(self):
        self._actor_box.clear(); self._type_box.clear(); self._refresh()

    def _refresh(self):
        actor = self._actor_box.text().strip() or None
        ttype = self._type_box.text().strip() or None
        logs  = self._engine.list_audit_logs(
            actor=actor, target_type=ttype, limit=200)
        self._table.setRowCount(0)
        for lg in logs:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0,
                QTableWidgetItem(lg.timestamp.strftime("%Y-%m-%d %H:%M:%S")))
            self._table.setItem(r, 1, QTableWidgetItem(lg.actor or ""))
            ai = QTableWidgetItem(lg.action.value if hasattr(lg.action, "value")
                                  else str(lg.action))
            ai.setForeground(QBrush(QColor("#4a6cf7")))
            self._table.setItem(r, 2, ai)
            self._table.setItem(r, 3, QTableWidgetItem(lg.target_type or ""))
            self._table.setItem(r, 4, QTableWidgetItem(lg.target_name or ""))
            for c in range(5):
                self._table.item(r, c).setData(ROLE_ID, lg.log_id)

    def _on_click(self, item):
        lid  = item.data(ROLE_ID)
        logs = self._engine.list_audit_logs(limit=200)
        lg   = next((l for l in logs if l.log_id == lid), None)
        if not lg: return
        self._detail.setRowCount(0)
        for k, v in [
            ("ID", lg.log_id[:16]),
            ("\u64cd\u4f5c\u4eba", lg.actor or "\u2014"),
            ("\u64cd\u4f5c", lg.action.value if hasattr(lg.action,"value") else str(lg.action)),
            ("\u8d44\u4ea7\u7c7b\u578b", lg.target_type or "\u2014"),
            ("\u8d44\u4ea7 ID", lg.target_id[:16] if lg.target_id else "\u2014"),
            ("\u8d44\u4ea7\u540d\u79f0", lg.target_name or "\u2014"),
            ("IP", lg.ip_address or "\u2014"),
            ("\u5907\u6ce8", lg.note or "\u2014"),
            ("\u65f6\u95f4", lg.timestamp.strftime("%Y-%m-%d %H:%M:%S")),
        ]:
            r = self._detail.rowCount(); self._detail.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._detail.setItem(r, 0, ki)
            self._detail.setItem(r, 1, QTableWidgetItem(str(v)))


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
        self._btn_submit  = QPushButton("\u2795  \u63d0\u4ea4\u7533\u8bf7")
        self._btn_approve = QPushButton("\u2705  \u5ba1\u6279\u901a\u8fc7")
        self._btn_reject  = QPushButton("\u274c  \u62d2\u7edd")
        self._btn_freeze  = QPushButton("\U0001f512  \u51bb\u7ed3\u8d44\u4ea7")
        for btn in (self._btn_submit, self._btn_approve,
                    self._btn_reject, self._btn_freeze):
            btn.setFixedHeight(28); tb.addWidget(btn)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#dee2e6;"); tb.addWidget(sep)
        tb.addStretch()
        root.addLayout(tb)

        # ── stats bar ─────────────────────────────────────────────
        self._stats_bar = QLabel("\u52a0\u8f7d\u4e2d...")
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
        self._sub.addTab(appr_w, "\u2696\ufe0f  \u5ba1\u6279\u5de5\u4f5c\u6d41")

        # Tab2: freeze management
        self._freeze_panel = FreezePanel(self._engine)
        self._sub.addTab(self._freeze_panel, "\U0001f512  \u8d44\u4ea7\u51bb\u7ed3")

        # Tab3: audit log
        self._audit_panel = AuditLogPanel(self._engine)
        self._sub.addTab(self._audit_panel, "\U0001f4dc  \u5ba1\u8ba1\u65e5\u5fd7")

        root.addWidget(self._sub)

        # ── status bar ────────────────────────────────────────────
        self._status = QLabel("\u5c31\u7eea")
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
            self._set_status("\u7533\u8bf7: " + req.title
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
            self._set_status("\u7533\u8bf7\u300c" + req.title + "\u300d\u5df2\u63d0\u4ea4")
            self._refresh_stats()

    def _on_approve_toolbar(self):
        rid = self._appr_list.selected_id()
        if not rid:
            self._set_status("\u8bf7\u5148\u9009\u62e9\u7533\u8bf7\u6761\u76ee"); return
        dlg = ReviewDialog(self, approve=True)
        if dlg.exec() == QDialog.Accepted:
            self._engine.approve(rid,
                approver=dlg.get_approver(),
                comment=dlg.get_comment())
            self._appr_detail.load(rid)
            self._set_status("\u7533\u8bf7\u5df2\u5ba1\u6279\u901a\u8fc7")
            self._refresh_stats()

    def _on_reject_toolbar(self):
        rid = self._appr_list.selected_id()
        if not rid:
            self._set_status("\u8bf7\u5148\u9009\u62e9\u7533\u8bf7\u6761\u76ee"); return
        dlg = ReviewDialog(self, approve=False)
        if dlg.exec() == QDialog.Accepted:
            self._engine.reject(rid,
                approver=dlg.get_approver(),
                comment=dlg.get_comment())
            self._appr_detail.load(rid)
            self._set_status("\u7533\u8bf7\u5df2\u62d2\u7edd")
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
            self._set_status("\u8d44\u4ea7\u5df2\u51bb\u7ed3")
            self._refresh_stats()

    # ── stats ─────────────────────────────────────────────────────

    def _refresh_stats(self):
        try:
            s = self._engine.stats()
        except Exception:
            return
        self._stats_bar.setText(
            "\u5ba1\u6279\u7533\u8bf7: " + str(s.get("total_requests", 0))
            + "    \u5f85\u5ba1\u6279: " + str(s.get("pending", 0))
            + "    \u5df2\u901a\u8fc7: " + str(s.get("approved", 0))
            + "    \u5df2\u62d2\u7edd: " + str(s.get("rejected", 0))
            + "    \u5df2\u51bb\u7ed3: " + str(s.get("active_freezes", 0))
            + "    \u5ba1\u8ba1\u65e5\u5fd7: " + str(s.get("audit_logs", 0)))

    def _set_status(self, msg: str):
        self._status.setText(msg)
