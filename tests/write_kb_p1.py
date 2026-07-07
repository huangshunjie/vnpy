"""write_kb_p1.py — knowledge_tab.py Part1: imports + dialogs"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\knowledge_tab.py"
)

PART1 = '''\
"""
research_ops/ui/knowledge_tab.py  Phase 7 - Knowledge Base
"""
from __future__ import annotations
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QHeaderView, QAbstractItemView, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QMenu, QMessageBox, QFrame,
    QTableWidget, QTableWidgetItem, QTextBrowser,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QBrush

from ..main_engine import ResearchOpsEngine
from ..model.knowledge_model import KnowledgeNote, ExperienceCard, FailureCaseRecord
from ..constant import NoteType, Priority
from ..event import (
    EVENT_RO_KB_CREATED, EVENT_RO_KB_UPDATED,
    EVENT_RO_KB_DELETED, EVENT_RO_KB_TAGGED,
)
from .report_tab import _md_to_html, MarkdownEditor

# ── palettes ──────────────────────────────────────────────────────
NOTE_TYPE_COLOR = {
    NoteType.RESEARCH:   "#4a6cf7",
    NoteType.EXPERIENCE: "#198754",
    NoteType.FAILURE:    "#dc3545",
    NoteType.INSIGHT:    "#fd7e14",
    NoteType.REFERENCE:  "#6c757d",
}
NOTE_TYPE_ICON = {
    NoteType.RESEARCH:   "\\U0001f9ea",
    NoteType.EXPERIENCE: "\\U0001f4a1",
    NoteType.FAILURE:    "\\u274c",
    NoteType.INSIGHT:    "\\u2728",
    NoteType.REFERENCE:  "\\U0001f4da",
}
PRIORITY_COLOR = {
    Priority.LOW:    "#6c757d",
    Priority.MEDIUM: "#fd7e14",
    Priority.HIGH:   "#dc3545",
    Priority.URGENT: "#9c27b0",
}
SEVERITY_COLOR = {
    "low":      "#198754",
    "medium":   "#fd7e14",
    "high":     "#dc3545",
    "critical": "#9c27b0",
}
ROLE_ID = Qt.UserRole


# =================================================================
# NoteDialog
# =================================================================

class NoteDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\\u7f16\\u8f91\\u7b14\\u8bb0" if self._editing
            else "\\u65b0\\u5efa\\u7b14\\u8bb0")
        self.setMinimumWidth(600)
        self.setMinimumHeight(480)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        meta = QGroupBox("\\u57fa\\u672c\\u4fe1\\u606f")
        form = QFormLayout(meta)
        self._title = QLineEdit()
        self._title.setPlaceholderText("\\u7b14\\u8bb0\\u6807\\u9898")
        form.addRow("\\u6807\\u9898 *", self._title)
        self._type = QComboBox()
        for nt in NoteType:
            self._type.addItem(NOTE_TYPE_ICON.get(nt,"") + "  " + nt.value, nt)
        form.addRow("\\u7c7b\\u578b", self._type)
        self._priority = QComboBox()
        for p in Priority:
            self._priority.addItem(p.value, p)
        form.addRow("\\u4f18\\u5148\\u7ea7", self._priority)
        self._author = QLineEdit()
        form.addRow("\\u4f5c\\u8005", self._author)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\\u9017\\u53f7\\u5206\\u9694")
        form.addRow("\\u6807\\u7b7e", self._tags)
        root.addWidget(meta)
        cg = QGroupBox("\\u5185\\u5bb9 (Markdown)")
        cl = QVBoxLayout(cg)
        self._content = QTextEdit()
        self._content.setFont(QFont("Consolas", 10))
        cl.addWidget(self._content)
        root.addWidget(cg, 1)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u786e\\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._title.setText(r.title)
        self._type.setCurrentIndex(self._type.findData(r.note_type))
        self._priority.setCurrentIndex(self._priority.findData(r.priority))
        self._author.setText(r.author or "")
        self._tags.setText(", ".join(r.tags))
        self._content.setPlainText(r.content or "")

    def _on_ok(self):
        if not self._title.text().strip(): self._title.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_title(self)    -> str:       return self._title.text().strip()
    def get_note_type(self)-> NoteType:  return self._type.currentData()
    def get_priority(self) -> Priority:  return self._priority.currentData()
    def get_author(self)   -> str:       return self._author.text().strip()
    def get_tags(self)     -> List[str]: return self._split(self._tags.text())
    def get_content(self)  -> str:       return self._content.toPlainText()


# =================================================================
# CardDialog
# =================================================================

class CardDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\\u7f16\\u8f91\\u7ecf\\u9a8c\\u5361\\u7247" if self._editing
            else "\\u65b0\\u5efa\\u7ecf\\u9a8c\\u5361\\u7247")
        self.setMinimumWidth(580)
        self.setMinimumHeight(520)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u5361\\u7247\\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._title = QLineEdit()
        form.addRow("\\u6807\\u9898 *", self._title)
        self._author = QLineEdit()
        form.addRow("\\u4f5c\\u8005", self._author)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\\u9017\\u53f7\\u5206\\u9694")
        form.addRow("\\u6807\\u7b7e", self._tags)
        root.addWidget(grp)
        for attr, label in [("_context","\\u80cc\\u666f / Context"),
                             ("_insight","\\u6d1e\\u5bdf / Insight"),
                             ("_lesson", "\\u6559\\u8bad / Lesson")]:
            sg = QGroupBox(label); sl = QVBoxLayout(sg)
            te = QTextEdit(); te.setFixedHeight(72)
            te.setFont(QFont("Consolas", 10))
            sl.addWidget(te); setattr(self, attr, te)
            root.addWidget(sg)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u786e\\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._title.setText(r.title); self._author.setText(r.author or "")
        self._tags.setText(", ".join(r.tags))
        self._context.setPlainText(r.context or "")
        self._insight.setPlainText(r.insight or "")
        self._lesson.setPlainText(r.lesson or "")

    def _on_ok(self):
        if not self._title.text().strip(): self._title.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_title(self)   -> str:       return self._title.text().strip()
    def get_author(self)  -> str:       return self._author.text().strip()
    def get_tags(self)    -> List[str]: return self._split(self._tags.text())
    def get_context(self) -> str:       return self._context.toPlainText()
    def get_insight(self) -> str:       return self._insight.toPlainText()
    def get_lesson(self)  -> str:       return self._lesson.toPlainText()


# =================================================================
# FailureCaseDialog
# =================================================================

class FailureCaseDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\\u7f16\\u8f91\\u5931\\u8d25\\u6848\\u4f8b" if self._editing
            else "\\u65b0\\u5efa\\u5931\\u8d25\\u6848\\u4f8b")
        self.setMinimumWidth(580)
        self.setMinimumHeight(560)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u57fa\\u672c\\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._title = QLineEdit()
        form.addRow("\\u6807\\u9898 *", self._title)
        self._severity = QComboBox()
        for s in ["low","medium","high","critical"]:
            self._severity.addItem(s, s)
        form.addRow("\\u4e25\\u91cd\\u7a0b\\u5ea6", self._severity)
        self._author = QLineEdit()
        form.addRow("\\u4f5c\\u8005", self._author)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\\u9017\\u53f7\\u5206\\u9694")
        form.addRow("\\u6807\\u7b7e", self._tags)
        root.addWidget(grp)
        for attr, label in [("_symptom",   "\\u73b0\\u8c61 / Symptom"),
                             ("_root",      "\\u6839\\u56e0 / Root Cause"),
                             ("_impact",    "\\u5f71\\u54cd / Impact"),
                             ("_resolution","\\u89e3\\u51b3\\u65b9\\u6848 / Resolution"),
                             ("_prevention","\\u9884\\u9632\\u63aa\\u65bd / Prevention")]:
            sg = QGroupBox(label); sl = QVBoxLayout(sg)
            te = QTextEdit(); te.setFixedHeight(60)
            te.setFont(QFont("Consolas", 10))
            sl.addWidget(te); setattr(self, attr, te)
            root.addWidget(sg)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u786e\\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._title.setText(r.title)
        idx = self._severity.findData(r.severity)
        if idx >= 0: self._severity.setCurrentIndex(idx)
        self._author.setText(r.author or "")
        self._tags.setText(", ".join(r.tags))
        self._symptom.setPlainText(r.symptom or "")
        self._root.setPlainText(r.root_cause or "")
        self._impact.setPlainText(r.impact or "")
        self._resolution.setPlainText(r.resolution or "")
        self._prevention.setPlainText(r.prevention or "")

    def _on_ok(self):
        if not self._title.text().strip(): self._title.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_title(self)      -> str:       return self._title.text().strip()
    def get_severity(self)   -> str:       return self._severity.currentData()
    def get_author(self)     -> str:       return self._author.text().strip()
    def get_tags(self)       -> List[str]: return self._split(self._tags.text())
    def get_symptom(self)    -> str:       return self._symptom.toPlainText()
    def get_root_cause(self) -> str:       return self._root.toPlainText()
    def get_impact(self)     -> str:       return self._impact.toPlainText()
    def get_resolution(self) -> str:       return self._resolution.toPlainText()
    def get_prevention(self) -> str:       return self._prevention.toPlainText()
'''

ast.parse(PART1)
P.write_text(PART1, encoding="utf-8")
print("PART1 written OK, lines:", len(PART1.splitlines()), "size:", P.stat().st_size)
