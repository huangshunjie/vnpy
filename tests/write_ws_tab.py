"""workspace_tab_writer.py — 整个写入 workspace_tab.py"""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\workspace_tab.py"
)

CONTENT = r'''"""
research_ops/ui/workspace_tab.py  — Phase 2 完整实现
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QMenu, QMessageBox, QColorDialog,
    QFrame, QTableWidget, QTableWidgetItem, QInputDialog,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QBrush

from vnpy.event import Event
from ..main_engine import ResearchOpsEngine
from ..model.workspace_model import WorkspaceRecord, ProjectRecord, FolderRecord
from ..constant import ProjectStatus, WorkspaceStatus
from ..event import (
    EVENT_RO_WS_CREATED, EVENT_RO_WS_UPDATED,
    EVENT_RO_WS_DELETED, EVENT_RO_WS_SWITCHED,
    EVENT_RO_PRJ_CREATED, EVENT_RO_PRJ_UPDATED,
    EVENT_RO_PRJ_DELETED, EVENT_RO_PRJ_STARRED,
    EVENT_RO_PRJ_UNSTARRED,
)

STATUS_COLORS = {
    ProjectStatus.ACTIVE:    "#198754",
    ProjectStatus.PAUSED:    "#fd7e14",
    ProjectStatus.COMPLETED: "#0d6efd",
    ProjectStatus.ARCHIVED:  "#6c757d",
}
STATUS_LABELS = {
    ProjectStatus.ACTIVE:    "\u6d3b\u8dc3",
    ProjectStatus.PAUSED:    "\u6682\u505c",
    ProjectStatus.COMPLETED: "\u5df2\u5b8c\u6210",
    ProjectStatus.ARCHIVED:  "\u5df2\u5f52\u6863",
}
NODE_WS      = "workspace"
NODE_PROJECT = "project"
NODE_FOLDER  = "folder"
NODE_STARRED = "starred_root"
ROLE_ID   = Qt.UserRole
ROLE_TYPE = Qt.UserRole + 1


# =================================================================
# WorkspaceDialog
# =================================================================

class WorkspaceDialog(QDialog):
    def __init__(self, parent=None, record: Optional[WorkspaceRecord] = None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\u7f16\u8f91\u5de5\u4f5c\u533a" if self._editing
            else "\u65b0\u5efa\u5de5\u4f5c\u533a"
        )
        self.setMinimumWidth(460)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u5de5\u4f5c\u533a\u4fe1\u606f")
        form = QFormLayout(grp)

        self._name = QLineEdit()
        self._name.setPlaceholderText("\u5de5\u4f5c\u533a\u540d\u79f0\uff08\u5fc5\u586b\uff09")
        form.addRow("\u540d\u79f0 *", self._name)

        self._desc = QTextEdit()
        self._desc.setFixedHeight(60)
        self._desc.setPlaceholderText("\u5de5\u4f5c\u533a\u63cf\u8ff0")
        form.addRow("\u63cf\u8ff0", self._desc)

        self._root = QLineEdit()
        self._root.setPlaceholderText("\u672c\u5730\u6839\u76ee\u5f55\u8def\u5f84\uff08\u53ef\u9009\uff09")
        form.addRow("\u6839\u76ee\u5f55", self._root)

        self._members = QLineEdit()
        self._members.setPlaceholderText("\u6210\u5458\uff0c\u9017\u53f7\u5206\u9694")
        form.addRow("\u6210\u5458", self._members)

        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\u6807\u7b7e\uff0c\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)

        root.addWidget(grp)
        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name)
        self._desc.setPlainText(r.description)
        self._root.setText(r.root_path)
        self._members.setText(", ".join(r.members))
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip():
            self._name.setFocus()
            return
        self.accept()

    def _split(self, t: str) -> List[str]:
        return [x.strip() for x in t.split(",") if x.strip()]

    def get_name(self)        -> str:       return self._name.text().strip()
    def get_description(self) -> str:       return self._desc.toPlainText().strip()
    def get_root_path(self)   -> str:       return self._root.text().strip()
    def get_members(self)     -> List[str]: return self._split(self._members.text())
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())


# =================================================================
# ProjectDialog
# =================================================================

class ProjectDialog(QDialog):
    def __init__(
        self, parent=None,
        record: Optional[ProjectRecord] = None,
        workspace_id: str = "",
    ):
        super().__init__(parent)
        self._record       = record
        self._workspace_id = workspace_id
        self._editing      = record is not None
        self._color        = (record.color if record else "#4a6cf7")
        self.setWindowTitle(
            "\u7f16\u8f91\u9879\u76ee" if self._editing
            else "\u65b0\u5efa\u9879\u76ee"
        )
        self.setMinimumWidth(460)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u9879\u76ee\u4fe1\u606f")
        form = QFormLayout(grp)

        self._name = QLineEdit()
        self._name.setPlaceholderText("\u9879\u76ee\u540d\u79f0\uff08\u5fc5\u586b\uff09")
        form.addRow("\u540d\u79f0 *", self._name)

        self._desc = QTextEdit()
        self._desc.setFixedHeight(60)
        self._desc.setPlaceholderText("\u9879\u76ee\u63cf\u8ff0")
        form.addRow("\u63cf\u8ff0", self._desc)

        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\u6807\u7b7e\uff0c\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)

        color_w = QWidget()
        color_l = QHBoxLayout(color_w)
        color_l.setContentsMargins(0, 0, 0, 0)
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(32, 22)
        self._color_btn.setStyleSheet(
            "background:%s; border-radius:4px; border:1px solid #ccc;" % self._color)
        self._color_btn.clicked.connect(self._pick_color)
        self._color_lbl = QLabel(self._color)
        color_l.addWidget(self._color_btn)
        color_l.addWidget(self._color_lbl)
        color_l.addStretch()
        form.addRow("\u989c\u8272", color_w)

        root.addWidget(grp)
        btns = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name)
        self._desc.setPlainText(r.description)
        self._tags.setText(", ".join(r.tags))
        self._set_color(r.color)

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self,
                                  "\u9009\u62e9\u9879\u76ee\u989c\u8272")
        if c.isValid():
            self._set_color(c.name())

    def _set_color(self, hex_color: str):
        self._color = hex_color
        self._color_btn.setStyleSheet(
            "background:%s; border-radius:4px; border:1px solid #ccc;" % hex_color)
        self._color_lbl.setText(hex_color)

    def _on_ok(self):
        if not self._name.text().strip():
            self._name.setFocus()
            return
        self.accept()

    def _split(self, t: str) -> List[str]:
        return [x.strip() for x in t.split(",") if x.strip()]

    def get_name(self)         -> str:       return self._name.text().strip()
    def get_description(self)  -> str:       return self._desc.toPlainText().strip()
    def get_tags(self)         -> List[str]: return self._split(self._tags.text())
    def get_color(self)        -> str:       return self._color
    def get_workspace_id(self) -> str:       return self._workspace_id
'''

P.write_text(CONTENT, encoding="utf-8")
import ast
try:
    ast.parse(CONTENT)
    print("block1 syntax OK, size:", P.stat().st_size)
except SyntaxError as e:
    print("SyntaxError at line", e.lineno, ":", e.msg)
