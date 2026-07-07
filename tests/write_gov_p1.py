"""write_gov_p1.py — governance_tab.py Part1: imports + dialogs"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\governance_tab.py"
)

PART1 = '''\
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
        self.setWindowTitle("\\u63d0\\u4ea4\\u5ba1\\u6279\\u7533\\u8bf7")
        self.setMinimumWidth(480)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u7533\\u8bf7\\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._title = QLineEdit()
        self._title.setPlaceholderText("\\u7533\\u8bf7\\u6807\\u9898")
        form.addRow("\\u6807\\u9898 *", self._title)
        self._target_type = QLineEdit()
        self._target_type.setPlaceholderText("model / strategy / dataset ...")
        form.addRow("\\u8d44\\u4ea7\\u7c7b\\u578b *", self._target_type)
        self._target_name = QLineEdit()
        form.addRow("\\u8d44\\u4ea7\\u540d\\u79f0", self._target_name)
        self._action = QLineEdit()
        self._action.setPlaceholderText("deploy / retire / publish ...")
        form.addRow("\\u64cd\\u4f5c", self._action)
        self._priority = QComboBox()
        for p in Priority:
            self._priority.addItem(p.value, p)
        self._priority.setCurrentIndex(1)
        form.addRow("\\u4f18\\u5148\\u7ea7", self._priority)
        self._requester = QLineEdit()
        form.addRow("\\u7533\\u8bf7\\u4eba", self._requester)
        root.addWidget(grp)
        desc_grp = QGroupBox("\\u7533\\u8bf7\\u8bf4\\u660e")
        dl = QVBoxLayout(desc_grp)
        self._desc = QTextEdit(); self._desc.setFixedHeight(80)
        dl.addWidget(self._desc)
        root.addWidget(desc_grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u63d0\\u4ea4")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
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
            "\\u5ba1\\u6279\\u901a\\u8fc7" if approve else "\\u62d2\\u7edd\\u7533\\u8bf7")
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._approver = QLineEdit()
        form.addRow("\\u5ba1\\u6279\\u4eba *", self._approver)
        root.addLayout(form)
        cg = QGroupBox("\\u5907\\u6ce8 / \\u539f\\u56e0")
        cl = QVBoxLayout(cg)
        self._comment = QTextEdit(); self._comment.setFixedHeight(80)
        cl.addWidget(self._comment)
        root.addWidget(cg)
        lbl = "\\u786e\\u8ba4\\u901a\\u8fc7" if self._approve else "\\u786e\\u8ba4\\u62d2\\u7edd"
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText(lbl)
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
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
        self.setWindowTitle("\\u51bb\\u7ed3\\u8d44\\u4ea7")
        self.setMinimumWidth(420)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._target_type = QLineEdit()
        self._target_type.setPlaceholderText("model / strategy / dataset")
        form.addRow("\\u8d44\\u4ea7\\u7c7b\\u578b *", self._target_type)
        self._target_id = QLineEdit()
        form.addRow("\\u8d44\\u4ea7 ID *", self._target_id)
        self._target_name = QLineEdit()
        form.addRow("\\u8d44\\u4ea7\\u540d\\u79f0", self._target_name)
        self._version = QLineEdit()
        form.addRow("\\u7248\\u672c", self._version)
        self._frozen_by = QLineEdit()
        form.addRow("\\u64cd\\u4f5c\\u4eba *", self._frozen_by)
        root.addLayout(form)
        rg = QGroupBox("\\u51bb\\u7ed3\\u539f\\u56e0 *")
        rl = QVBoxLayout(rg)
        self._reason = QTextEdit(); self._reason.setFixedHeight(72)
        rl.addWidget(self._reason)
        root.addWidget(rg)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u51bb\\u7ed3")
        btns.button(QDialogButtonBox.Ok).setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
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
'''

ast.parse(PART1)
P.write_text(PART1, encoding="utf-8")
print("PART1 OK, lines:", len(PART1.splitlines()), "size:", P.stat().st_size)
