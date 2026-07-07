"""write_pl_p1.py — pipeline_tab.py Part1: imports + constants + dialogs"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\pipeline_tab.py"
)

PART1 = """\
\"\"\"
research_ops/ui/pipeline_tab.py  Phase 5 - Pipeline System
\"\"\"
from __future__ import annotations
from typing import List, Optional, Dict, Tuple
import math

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QMenu, QMessageBox, QFrame,
    QTableWidget, QTableWidgetItem, QScrollArea,
    QSizePolicy, QSpinBox,
)
from PySide6.QtCore import Qt, Signal, QPoint, QRect, QSize, QRectF
from PySide6.QtGui import (
    QColor, QFont, QBrush, QPainter, QPen,
    QPainterPath, QMouseEvent,
)

from vnpy.event import Event
from ..main_engine import ResearchOpsEngine
from ..model.pipeline_model import PipelineRecord, DAGNode, PipelineRunRecord
from ..constant import PipelineStatus, NodeStatus, NodeType, TriggerType
from ..event import (
    EVENT_RO_PL_CREATED, EVENT_RO_PL_UPDATED,
    EVENT_RO_PL_DELETED, EVENT_RO_PL_STARTED,
    EVENT_RO_PL_COMPLETED, EVENT_RO_PL_FAILED,
    EVENT_RO_PL_PAUSED, EVENT_RO_PL_RESET,
    EVENT_RO_NODE_STARTED, EVENT_RO_NODE_COMPLETED,
    EVENT_RO_NODE_FAILED, EVENT_RO_NODE_SKIPPED,
)

# ── palettes ──────────────────────────────────────────────────────
PL_STATUS_COLOR = {
    PipelineStatus.IDLE:      "#6c757d",
    PipelineStatus.RUNNING:   "#198754",
    PipelineStatus.COMPLETED: "#0d6efd",
    PipelineStatus.FAILED:    "#dc3545",
    PipelineStatus.PAUSED:    "#fd7e14",
}
NODE_STATUS_COLOR = {
    NodeStatus.IDLE:      "#adb5bd",
    NodeStatus.PENDING:   "#6c757d",
    NodeStatus.RUNNING:   "#198754",
    NodeStatus.COMPLETED: "#0d6efd",
    NodeStatus.FAILED:    "#dc3545",
    NodeStatus.SKIPPED:   "#fd7e14",
}
NODE_TYPE_COLOR = {
    NodeType.DATA_LOAD:    "#4a6cf7",
    NodeType.FEATURE_CALC: "#198754",
    NodeType.MODEL_TRAIN:  "#9c27b0",
    NodeType.BACKTEST:     "#fd7e14",
    NodeType.VALIDATION:   "#0d6efd",
    NodeType.REPORT:       "#17a2b8",
    NodeType.NOTIFY:       "#6f42c1",
    NodeType.CUSTOM:       "#6c757d",
}
NODE_TYPE_ICON = {
    NodeType.DATA_LOAD:    "\\U0001f4be",
    NodeType.FEATURE_CALC: "\\U0001f4d0",
    NodeType.MODEL_TRAIN:  "\\U0001f916",
    NodeType.BACKTEST:     "\\U0001f4c8",
    NodeType.VALIDATION:   "\\u2705",
    NodeType.REPORT:       "\\U0001f4dd",
    NodeType.NOTIFY:       "\\U0001f514",
    NodeType.CUSTOM:       "\\u2699",
}
ROLE_ID   = Qt.UserRole
ROLE_TYPE = Qt.UserRole + 1


# =================================================================
# PipelineDialog
# =================================================================

class PipelineDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\\u7f16\\u8f91 Pipeline" if self._editing
            else "\\u65b0\\u5efa Pipeline")
        self.setMinimumWidth(460)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("Pipeline \\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        self._name.setPlaceholderText("Pipeline \\u540d\\u79f0")
        form.addRow("\\u540d\\u79f0 *", self._name)
        self._desc = QTextEdit(); self._desc.setFixedHeight(52)
        form.addRow("\\u63cf\\u8ff0", self._desc)
        self._author = QLineEdit()
        form.addRow("\\u4f5c\\u8005", self._author)
        self._schedule = QLineEdit()
        self._schedule.setPlaceholderText("cron \\u8868\\u8fbe\\u5f0f\\uff0c\\u5982 0 9 * * 1-5")
        form.addRow("\\u8c03\\u5ea6", self._schedule)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\\u9017\\u53f7\\u5206\\u9694")
        form.addRow("\\u6807\\u7b7e", self._tags)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u786e\\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name)
        self._desc.setPlainText(r.description)
        self._author.setText(r.author or "")
        self._schedule.setText(r.schedule or "")
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip():
            self._name.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_name(self)        -> str:       return self._name.text().strip()
    def get_description(self) -> str:       return self._desc.toPlainText().strip()
    def get_author(self)      -> str:       return self._author.text().strip()
    def get_schedule(self)    -> str:       return self._schedule.text().strip()
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())


# =================================================================
# NodeDialog
# =================================================================

class NodeDialog(QDialog):
    def __init__(self, parent=None, pipeline_id: str = "",
                 existing_nodes: Optional[List[DAGNode]] = None):
        super().__init__(parent)
        self._pipeline_id  = pipeline_id
        self._existing     = existing_nodes or []
        self.setWindowTitle("\\u6dfb\\u52a0\\u8282\\u70b9")
        self.setMinimumWidth(460)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u8282\\u70b9\\u4fe1\\u606f")
        form = QFormLayout(grp)

        self._name = QLineEdit()
        self._name.setPlaceholderText("\\u8282\\u70b9\\u540d\\u79f0")
        form.addRow("\\u540d\\u79f0 *", self._name)

        self._type = QComboBox()
        for nt in NodeType:
            icon = NODE_TYPE_ICON.get(nt, "")
            self._type.addItem(icon + "  " + nt.value, nt)
        form.addRow("\\u7c7b\\u578b", self._type)

        self._timeout = QSpinBox()
        self._timeout.setRange(1, 86400)
        self._timeout.setValue(3600)
        self._timeout.setSuffix(" \\u79d2")
        form.addRow("\\u8d85\\u65f6", self._timeout)

        self._retries = QSpinBox()
        self._retries.setRange(0, 10)
        self._retries.setValue(3)
        form.addRow("\\u6700\\u5927\\u91cd\\u8bd5", self._retries)

        # depends_on checkboxes built from existing nodes
        if self._existing:
            dep_grp = QGroupBox("\\u524d\\u7f6e\\u8282\\u70b9\\uff08\\u4f9d\\u8d56\\uff09")
            dep_l   = QVBoxLayout(dep_grp)
            from PySide6.QtWidgets import QCheckBox
            self._dep_checks: List[Tuple[str, object]] = []
            for nd in self._existing:
                cb = QCheckBox(NODE_TYPE_ICON.get(nd.node_type, "") + "  " + nd.name)
                dep_l.addWidget(cb)
                self._dep_checks.append((nd.node_id, cb))
            root.addWidget(grp)
            root.addWidget(dep_grp)
        else:
            self._dep_checks = []
            root.addWidget(grp)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u6dfb\\u52a0")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _on_ok(self):
        if not self._name.text().strip():
            self._name.setFocus(); return
        self.accept()

    def get_name(self)        -> str:        return self._name.text().strip()
    def get_node_type(self)   -> NodeType:   return self._type.currentData()
    def get_timeout(self)     -> int:        return self._timeout.value()
    def get_max_retries(self) -> int:        return self._retries.value()
    def get_depends_on(self)  -> List[str]:
        return [nid for nid, cb in self._dep_checks if cb.isChecked()]
"""

ast.parse(PART1)
P.write_text(PART1, encoding="utf-8")
print("PART1 written OK, lines:", len(PART1.splitlines()), "size:", P.stat().st_size)
