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
    NoteType.RESEARCH:   "\U0001f9ea",
    NoteType.EXPERIENCE: "\U0001f4a1",
    NoteType.FAILURE:    "\u274c",
    NoteType.INSIGHT:    "\u2728",
    NoteType.REFERENCE:  "\U0001f4da",
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
            "\u7f16\u8f91\u7b14\u8bb0" if self._editing
            else "\u65b0\u5efa\u7b14\u8bb0")
        self.setMinimumWidth(600)
        self.setMinimumHeight(480)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        meta = QGroupBox("\u57fa\u672c\u4fe1\u606f")
        form = QFormLayout(meta)
        self._title = QLineEdit()
        self._title.setPlaceholderText("\u7b14\u8bb0\u6807\u9898")
        form.addRow("\u6807\u9898 *", self._title)
        self._type = QComboBox()
        for nt in NoteType:
            self._type.addItem(NOTE_TYPE_ICON.get(nt,"") + "  " + nt.value, nt)
        form.addRow("\u7c7b\u578b", self._type)
        self._priority = QComboBox()
        for p in Priority:
            self._priority.addItem(p.value, p)
        form.addRow("\u4f18\u5148\u7ea7", self._priority)
        self._author = QLineEdit()
        form.addRow("\u4f5c\u8005", self._author)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)
        root.addWidget(meta)
        cg = QGroupBox("\u5185\u5bb9 (Markdown)")
        cl = QVBoxLayout(cg)
        self._content = QTextEdit()
        self._content.setFont(QFont("Consolas", 10))
        cl.addWidget(self._content)
        root.addWidget(cg, 1)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
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
            "\u7f16\u8f91\u7ecf\u9a8c\u5361\u7247" if self._editing
            else "\u65b0\u5efa\u7ecf\u9a8c\u5361\u7247")
        self.setMinimumWidth(580)
        self.setMinimumHeight(520)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u5361\u7247\u4fe1\u606f")
        form = QFormLayout(grp)
        self._title = QLineEdit()
        form.addRow("\u6807\u9898 *", self._title)
        self._author = QLineEdit()
        form.addRow("\u4f5c\u8005", self._author)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)
        root.addWidget(grp)
        for attr, label in [("_context","\u80cc\u666f / Context"),
                             ("_insight","\u6d1e\u5bdf / Insight"),
                             ("_lesson", "\u6559\u8bad / Lesson")]:
            sg = QGroupBox(label); sl = QVBoxLayout(sg)
            te = QTextEdit(); te.setFixedHeight(72)
            te.setFont(QFont("Consolas", 10))
            sl.addWidget(te); setattr(self, attr, te)
            root.addWidget(sg)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
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
            "\u7f16\u8f91\u5931\u8d25\u6848\u4f8b" if self._editing
            else "\u65b0\u5efa\u5931\u8d25\u6848\u4f8b")
        self.setMinimumWidth(580)
        self.setMinimumHeight(560)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u57fa\u672c\u4fe1\u606f")
        form = QFormLayout(grp)
        self._title = QLineEdit()
        form.addRow("\u6807\u9898 *", self._title)
        self._severity = QComboBox()
        for s in ["low","medium","high","critical"]:
            self._severity.addItem(s, s)
        form.addRow("\u4e25\u91cd\u7a0b\u5ea6", self._severity)
        self._author = QLineEdit()
        form.addRow("\u4f5c\u8005", self._author)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)
        root.addWidget(grp)
        for attr, label in [("_symptom",   "\u73b0\u8c61 / Symptom"),
                             ("_root",      "\u6839\u56e0 / Root Cause"),
                             ("_impact",    "\u5f71\u54cd / Impact"),
                             ("_resolution","\u89e3\u51b3\u65b9\u6848 / Resolution"),
                             ("_prevention","\u9884\u9632\u63aa\u65bd / Prevention")]:
            sg = QGroupBox(label); sl = QVBoxLayout(sg)
            te = QTextEdit(); te.setFixedHeight(60)
            te.setFont(QFont("Consolas", 10))
            sl.addWidget(te); setattr(self, attr, te)
            root.addWidget(sg)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
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


class NoteList(QWidget):
    selected = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._filter  = None
        self._keyword = ""
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        fb = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItem("\u5168\u90e8", None)
        for nt in NoteType:
            self._combo.addItem(NOTE_TYPE_ICON.get(nt,"")+" "+nt.value, nt)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\u6807\u9898","\u7c7b\u578b","\u4f18\u5148\u7ea7","\u72b6\u6001"])
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
        for ev in (EVENT_RO_KB_CREATED, EVENT_RO_KB_UPDATED,
                   EVENT_RO_KB_DELETED, EVENT_RO_KB_TAGGED):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()
    def _on_filter(self, _):   self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_notes()
        if self._filter:
            items = [n for n in items if n.note_type == self._filter]
        if self._keyword:
            items = [n for n in items
                     if self._keyword in n.title.lower()
                     or self._keyword in (n.content or "").lower()
                     or any(self._keyword in t for t in n.tags)]
        self._table.setRowCount(0)
        for nt in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(nt.title))
            tc = NOTE_TYPE_COLOR.get(nt.note_type, "#6c757d")
            ti = QTableWidgetItem(
                NOTE_TYPE_ICON.get(nt.note_type,"") + " " + nt.note_type.value)
            ti.setForeground(QBrush(QColor(tc)))
            self._table.setItem(r, 1, ti)
            pc = PRIORITY_COLOR.get(nt.priority, "#6c757d")
            pi = QTableWidgetItem(nt.priority.value)
            pi.setForeground(QBrush(QColor(pc)))
            self._table.setItem(r, 2, pi)
            if nt.is_archived:
                si = QTableWidgetItem("\U0001f4e6 \u5df2\u5f52\u6863")
                si.setForeground(QBrush(QColor("#adb5bd")))
            else:
                si = QTableWidgetItem("\u270f \u6d3b\u8dc3")
                si.setForeground(QBrush(QColor("#198754")))
            self._table.setItem(r, 3, si)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, nt.note_id)

    def _on_click(self, item): self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        nid = item.data(ROLE_ID)
        nt  = self._engine.get_note(nid)
        if not nt: return
        menu = QMenu(self)
        a_arch = menu.addAction("\U0001f4e6  \u5f52\u6863" if not nt.is_archived
                                else "\u21a9  \u53d6\u6d88\u5f52\u6863")
        menu.addSeparator()
        a_del  = menu.addAction("\U0001f5d1  \u5220\u9664")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_arch:
            self._engine.archive_note(nid); self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\u786e\u8ba4",
                "\u5220\u9664\u7b14\u8bb0\u300c" + nt.title + "\u300d\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_note(nid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class NoteDetail(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        self.setDocumentMode(True)

        # Tab1: info table
        ov = QWidget(); ov_l = QVBoxLayout(ov)
        hdr = QHBoxLayout()
        self._title = QLabel("\u8bf7\u9009\u62e9\u7b14\u8bb0")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._badge = QLabel("")
        self._badge.setFixedHeight(22)
        self._badge.setStyleSheet("padding:2px 10px;border-radius:10px;font-size:12px;")
        hdr.addWidget(self._badge)
        ov_l.addLayout(hdr)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._bar)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        self._info.setFixedHeight(180)
        ov_l.addWidget(self._info)
        self.addTab(ov, "\U0001f4cb  \u6982\u89c8")

        # Tab2: markdown editor
        ed = QWidget(); ed_l = QVBoxLayout(ed)
        self._editor = MarkdownEditor()
        self._editor.content_changed.connect(self._on_content_change)
        ed_l.addWidget(self._editor, 1)
        self.addTab(ed, "\U0001f4dd  \u7f16\u8f91")

        # Tab3: rendered preview
        pv = QWidget(); pv_l = QVBoxLayout(pv)
        self._browser = QTextBrowser()
        self._browser.setStyleSheet(
            "QTextBrowser{background:#fff;border:1px solid #dee2e6;"
            "border-radius:4px;padding:16px;}")
        self._browser.setOpenExternalLinks(True)
        pv_l.addWidget(self._browser, 1)
        self.addTab(pv, "\U0001f5fa  \u9884\u89c8")

    def load(self, note_id: str):
        self._id = note_id
        nt = self._engine.get_note(note_id)
        if not nt: return
        self._title.setText(nt.title)
        tc = NOTE_TYPE_COLOR.get(nt.note_type, "#6c757d")
        self._bar.setStyleSheet("background:" + tc + ";border-radius:2px;")
        pc = PRIORITY_COLOR.get(nt.priority, "#6c757d")
        self._badge.setText(nt.priority.value)
        self._badge.setStyleSheet(
            "padding:2px 10px;border-radius:10px;"
            "background:" + pc + "22;color:" + pc + ";"
            "font-size:12px;border:1px solid " + pc + "44;")
        self._info.setRowCount(0)
        for k, v in [
            ("ID", nt.note_id[:16]),("\u6807\u9898", nt.title),
            ("\u7c7b\u578b", nt.note_type.value),
            ("\u4f18\u5148\u7ea7", nt.priority.value),
            ("\u4f5c\u8005", nt.author or "\u2014"),
            ("\u6807\u7b7e", ", ".join(nt.tags) if nt.tags else "\u2014"),
            ("\u5df2\u5f52\u6863", "\u662f" if nt.is_archived else "\u5426"),
            ("\u521b\u5efa", nt.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        self._editor.content_changed.disconnect()
        self._editor.set_content(nt.content or "")
        self._editor.content_changed.connect(self._on_content_change)
        self._browser.setHtml(_md_to_html(nt.content or ""))

    def clear_panel(self):
        self._id = None
        self._title.setText("\u8bf7\u9009\u62e9\u7b14\u8bb0")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        self._badge.setText(""); self._badge.setStyleSheet("")
        self._info.setRowCount(0)
        self._editor.clear(); self._browser.clear()

    def _on_content_change(self, md: str):
        if not self._id: return
        nt = self._engine.get_note(self._id)
        if not nt: return
        nt.content = md
        self._engine.update_note(nt)
        self._browser.setHtml(_md_to_html(md))


class CardList(QWidget):
    selected = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._keyword = ""
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels([
            "\u6807\u9898","\u4f5c\u8005","\u6807\u7b7e"])
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
        for ev in (EVENT_RO_KB_CREATED, EVENT_RO_KB_UPDATED,
                   EVENT_RO_KB_DELETED, EVENT_RO_KB_TAGGED):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()

    def _refresh(self):
        items = self._engine.list_cards()
        if self._keyword:
            items = [c for c in items
                     if self._keyword in c.title.lower()
                     or self._keyword in (c.insight or "").lower()
                     or any(self._keyword in t for t in c.tags)]
        self._table.setRowCount(0)
        for cd in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(cd.title))
            self._table.setItem(r, 1, QTableWidgetItem(cd.author or ""))
            self._table.setItem(r, 2, QTableWidgetItem(", ".join(cd.tags)))
            for c in range(3):
                self._table.item(r, c).setData(ROLE_ID, cd.card_id)

    def _on_click(self, item): self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        cid = item.data(ROLE_ID)
        cd  = self._engine.get_card(cid)
        if not cd: return
        menu  = QMenu(self)
        a_del = menu.addAction("\U0001f5d1  \u5220\u9664")
        if menu.exec(self._table.viewport().mapToGlobal(pos)) == a_del:
            if QMessageBox.question(
                self, "\u786e\u8ba4",
                "\u5220\u9664\u5361\u7247\u300c" + cd.title + "\u300d\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_card(cid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class CardDetail(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        self._title = QLabel("\u8bf7\u9009\u62e9\u7ecf\u9a8c\u5361\u7247")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        root.addWidget(self._title)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        root.addWidget(self._bar)
        for attr, label, color in [
            ("_context_view","\U0001f4cc  \u80cc\u666f","#4a6cf7"),
            ("_insight_view","\U0001f4a1  \u6d1e\u5bdf","#198754"),
            ("_lesson_view", "\U0001f4d6  \u6559\u8bad","#fd7e14"),
        ]:
            grp = QGroupBox(label)
            grp.setStyleSheet("QGroupBox{font-weight:bold;color:"+color+";}")
            gl = QVBoxLayout(grp)
            te = QTextEdit(); te.setReadOnly(True)
            te.setFont(QFont("Consolas", 10)); te.setFixedHeight(90)
            gl.addWidget(te); setattr(self, attr, te); root.addWidget(grp)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        root.addWidget(self._info)

    def load(self, card_id: str):
        self._id = card_id
        cd = self._engine.get_card(card_id)
        if not cd: return
        self._title.setText("\U0001f4a1  " + cd.title)
        self._bar.setStyleSheet("background:#198754;border-radius:2px;")
        self._context_view.setPlainText(cd.context or "")
        self._insight_view.setPlainText(cd.insight or "")
        self._lesson_view.setPlainText(cd.lesson or "")
        self._info.setRowCount(0)
        for k, v in [
            ("ID", cd.card_id[:16]),("\u4f5c\u8005", cd.author or "\u2014"),
            ("\u6807\u7b7e", ", ".join(cd.tags) if cd.tags else "\u2014"),
            ("\u9002\u7528", ", ".join(cd.applicable_to) if cd.applicable_to else "\u2014"),
            ("\u521b\u5efa", cd.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))

    def clear_panel(self):
        self._id = None
        self._title.setText("\u8bf7\u9009\u62e9\u7ecf\u9a8c\u5361\u7247")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        for te in (self._context_view, self._insight_view, self._lesson_view):
            te.clear()
        self._info.setRowCount(0)


class FailureCaseList(QWidget):
    selected = Signal(str)

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine  = engine
        self._keyword = ""
        self._init_ui()
        self._register_events()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        fb = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItem("\u5168\u90e8", "all")
        self._combo.addItem("\u672a\u89e3\u51b3", "open")
        self._combo.addItem("\u5df2\u89e3\u51b3", "resolved")
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(lambda _: self._refresh())
        fb.addWidget(self._combo, 1); root.addLayout(fb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\u6807\u9898","\u4e25\u91cd\u7a0b\u5ea6","\u4f5c\u8005","\u72b6\u6001"])
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
        for ev in (EVENT_RO_KB_CREATED, EVENT_RO_KB_UPDATED,
                   EVENT_RO_KB_DELETED, EVENT_RO_KB_TAGGED):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()

    def _refresh(self):
        filt  = self._combo.currentData()
        items = self._engine.list_failure_cases()
        if filt == "open":     items = [c for c in items if not c.is_resolved]
        elif filt == "resolved": items = [c for c in items if c.is_resolved]
        if self._keyword:
            items = [c for c in items
                     if self._keyword in c.title.lower()
                     or self._keyword in (c.symptom or "").lower()]
        self._table.setRowCount(0)
        for fc in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(fc.title))
            sc = SEVERITY_COLOR.get(fc.severity, "#6c757d")
            si = QTableWidgetItem(fc.severity)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 1, si)
            self._table.setItem(r, 2, QTableWidgetItem(fc.author or ""))
            if fc.is_resolved:
                ri = QTableWidgetItem("\u2705 \u5df2\u89e3\u51b3")
                ri.setForeground(QBrush(QColor("#198754")))
            else:
                ri = QTableWidgetItem("\u274c \u672a\u89e3\u51b3")
                ri.setForeground(QBrush(QColor("#dc3545")))
            self._table.setItem(r, 3, ri)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, fc.case_id)

    def _on_click(self, item): self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        cid = item.data(ROLE_ID)
        fc  = self._engine.get_failure_case(cid)
        if not fc: return
        menu   = QMenu(self)
        a_res  = menu.addAction("\u2705  \u6807\u8bb0\u5df2\u89e3\u51b3")
        menu.addSeparator()
        a_del  = menu.addAction("\U0001f5d1  \u5220\u9664")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_res:
            self._engine.resolve_case(cid); self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\u786e\u8ba4",
                "\u5220\u9664\u6848\u4f8b\u300c" + fc.title + "\u300d\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_failure_case(cid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class FailureCaseDetail(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        hdr  = QHBoxLayout()
        self._title = QLabel("\u8bf7\u9009\u62e9\u5931\u8d25\u6848\u4f8b")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._res_badge = QLabel("")
        self._res_badge.setFixedHeight(22)
        self._res_badge.setStyleSheet(
            "padding:2px 10px;border-radius:10px;font-size:12px;")
        hdr.addWidget(self._res_badge); root.addLayout(hdr)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        root.addWidget(self._bar)
        for attr, label, color in [
            ("_symp_v",  "\U0001f6a8  \u73b0\u8c61",      "#dc3545"),
            ("_root_v",  "\U0001f50d  \u6839\u56e0",      "#fd7e14"),
            ("_imp_v",   "\U0001f4a5  \u5f71\u54cd",      "#9c27b0"),
            ("_res_v",   "\u2705  \u89e3\u51b3\u65b9\u6848","#198754"),
            ("_prev_v",  "\U0001f6e1  \u9884\u9632\u63aa\u65bd","#0d6efd"),
        ]:
            grp = QGroupBox(label)
            grp.setStyleSheet("QGroupBox{font-weight:bold;color:"+color+";}")
            gl  = QVBoxLayout(grp)
            te  = QTextEdit(); te.setReadOnly(True)
            te.setFont(QFont("Consolas", 10)); te.setFixedHeight(66)
            gl.addWidget(te); setattr(self, attr, te); root.addWidget(grp)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        root.addWidget(self._info)

    def load(self, case_id: str):
        self._id = case_id
        fc = self._engine.get_failure_case(case_id)
        if not fc: return
        self._title.setText("\u274c  " + fc.title)
        sc = SEVERITY_COLOR.get(fc.severity, "#6c757d")
        self._bar.setStyleSheet("background:" + sc + ";border-radius:2px;")
        if fc.is_resolved:
            self._res_badge.setText("\u2705 \u5df2\u89e3\u51b3")
            self._res_badge.setStyleSheet(
                "padding:2px 10px;border-radius:10px;"
                "background:#d1e7dd;color:#198754;"
                "font-size:12px;border:1px solid #a3cfbb;")
        else:
            self._res_badge.setText("\u274c \u672a\u89e3\u51b3")
            self._res_badge.setStyleSheet(
                "padding:2px 10px;border-radius:10px;"
                "background:#f8d7da;color:#dc3545;"
                "font-size:12px;border:1px solid #f1aeb5;")
        self._symp_v.setPlainText(fc.symptom or "")
        self._root_v.setPlainText(fc.root_cause or "")
        self._imp_v.setPlainText(fc.impact or "")
        self._res_v.setPlainText(fc.resolution or "")
        self._prev_v.setPlainText(fc.prevention or "")
        self._info.setRowCount(0)
        res_at = fc.resolved_at.strftime("%Y-%m-%d") if fc.resolved_at else "\u2014"
        for k, v in [
            ("ID", fc.case_id[:16]),
            ("\u4e25\u91cd\u7a0b\u5ea6", fc.severity),
            ("\u4f5c\u8005", fc.author or "\u2014"),
            ("\u6807\u7b7e", ", ".join(fc.tags) if fc.tags else "\u2014"),
            ("\u89e3\u51b3\u65f6\u95f4", res_at),
            ("\u521b\u5efa", fc.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))

    def clear_panel(self):
        self._id = None
        self._title.setText("\u8bf7\u9009\u62e9\u5931\u8d25\u6848\u4f8b")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        self._res_badge.setText(""); self._res_badge.setStyleSheet("")
        for te in (self._symp_v, self._root_v, self._imp_v,
                   self._res_v, self._prev_v):
            te.clear()
        self._info.setRowCount(0)


class SearchPanel(QWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)

        # search bar
        sb = QHBoxLayout()
        self._box = QLineEdit()
        self._box.setPlaceholderText(
            "\u5168\u6587\u641c\u7d22\u7b14\u8bb0 / \u5361\u7247 / \u6848\u4f8b...")
        self._box.setFixedHeight(30)
        self._btn = QPushButton("\U0001f50d  \u641c\u7d22")
        self._btn.setFixedHeight(30)
        self._btn.clicked.connect(self._do_search)
        self._box.returnPressed.connect(self._do_search)
        sb.addWidget(self._box, 1); sb.addWidget(self._btn)
        root.addLayout(sb)

        # results label
        self._lbl = QLabel("\u8f93\u5165\u5173\u952e\u8bcd\u5f00\u59cb\u641c\u7d22")
        self._lbl.setStyleSheet("color:#6c757d;font-size:12px;margin:4px 0;")
        root.addWidget(self._lbl)

        # results tabs
        self._tabs = QTabWidget(); self._tabs.setDocumentMode(True)

        self._note_tbl = self._make_table(
            ["\u6807\u9898","\u7c7b\u578b","\u4f5c\u8005","\u65e5\u671f"])
        self._tabs.addTab(self._note_tbl, "\U0001f9ea  \u7b14\u8bb0")

        self._card_tbl = self._make_table(
            ["\u6807\u9898","\u4f5c\u8005","\u6807\u7b7e"])
        self._tabs.addTab(self._card_tbl, "\U0001f4a1  \u7ecf\u9a8c\u5361")

        self._case_tbl = self._make_table(
            ["\u6807\u9898","\u4e25\u91cd\u7a0b\u5ea6","\u4f5c\u8005","\u72b6\u6001"])
        self._tabs.addTab(self._case_tbl, "\u274c  \u5931\u8d25\u6848\u4f8b")

        root.addWidget(self._tabs, 1)

    @staticmethod
    def _make_table(headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.verticalHeader().setVisible(False)
        return t

    def _do_search(self):
        kw = self._box.text().strip()
        if not kw: return
        results = self._engine.search_all(kw)
        notes = results.get("notes", [])
        cards = results.get("cards", [])
        cases = results.get("failure_cases", [])
        total = len(notes) + len(cards) + len(cases)
        self._lbl.setText(
            "\u300c" + kw + "\u300d\u5171\u627e\u5230 " + str(total)
            + " \u6761\u8bb0\u5f55\uff08\u7b14\u8bb0 " + str(len(notes))
            + " + \u5361\u7247 " + str(len(cards))
            + " + \u6848\u4f8b " + str(len(cases)) + "\uff09")

        self._note_tbl.setRowCount(0)
        for nt in notes:
            r = self._note_tbl.rowCount(); self._note_tbl.insertRow(r)
            self._note_tbl.setItem(r, 0, QTableWidgetItem(nt.title))
            tc = NOTE_TYPE_COLOR.get(nt.note_type, "#6c757d")
            ti = QTableWidgetItem(NOTE_TYPE_ICON.get(nt.note_type,"")+" "+nt.note_type.value)
            ti.setForeground(QBrush(QColor(tc)))
            self._note_tbl.setItem(r, 1, ti)
            self._note_tbl.setItem(r, 2, QTableWidgetItem(nt.author or ""))
            self._note_tbl.setItem(r, 3,
                QTableWidgetItem(nt.created_at.strftime("%Y-%m-%d")))

        self._card_tbl.setRowCount(0)
        for cd in cards:
            r = self._card_tbl.rowCount(); self._card_tbl.insertRow(r)
            self._card_tbl.setItem(r, 0, QTableWidgetItem(cd.title))
            self._card_tbl.setItem(r, 1, QTableWidgetItem(cd.author or ""))
            self._card_tbl.setItem(r, 2, QTableWidgetItem(", ".join(cd.tags)))

        self._case_tbl.setRowCount(0)
        for fc in cases:
            r = self._case_tbl.rowCount(); self._case_tbl.insertRow(r)
            self._case_tbl.setItem(r, 0, QTableWidgetItem(fc.title))
            sc = SEVERITY_COLOR.get(fc.severity, "#6c757d")
            si = QTableWidgetItem(fc.severity)
            si.setForeground(QBrush(QColor(sc)))
            self._case_tbl.setItem(r, 1, si)
            self._case_tbl.setItem(r, 2, QTableWidgetItem(fc.author or ""))
            ri = QTableWidgetItem(
                "\u2705 \u5df2\u89e3\u51b3" if fc.is_resolved
                else "\u274c \u672a\u89e3\u51b3")
            ri.setForeground(QBrush(QColor(
                "#198754" if fc.is_resolved else "#dc3545")))
            self._case_tbl.setItem(r, 3, ri)

        idx = (0 if notes else 1 if cards else 2)
        self._tabs.setCurrentIndex(idx)


class KnowledgeTab(QWidget):
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
        self._btn_new  = QPushButton("+ \u65b0\u5efa")
        self._btn_edit = QPushButton("\u270f  \u7f16\u8f91")
        self._btn_del  = QPushButton("\U0001f5d1  \u5220\u9664")
        for btn in (self._btn_new, self._btn_edit, self._btn_del):
            btn.setFixedHeight(28); tb.addWidget(btn)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#dee2e6;"); tb.addWidget(sep)
        tb.addStretch()
        tb.addWidget(QLabel("\u641c\u7d22:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\u6807\u9898 / \u5185\u5bb9 / \u6807\u7b7e...")
        self._search_box.setFixedWidth(180); self._search_box.setFixedHeight(28)
        tb.addWidget(self._search_box)
        self._btn_search = QPushButton("\u641c\u7d22")
        self._btn_search.setFixedSize(52, 28)
        self._btn_reset_s = QPushButton("\u91cd\u7f6e")
        self._btn_reset_s.setFixedSize(52, 28)
        tb.addWidget(self._btn_search); tb.addWidget(self._btn_reset_s)
        root.addLayout(tb)

        # ── stats bar ─────────────────────────────────────────────
        self._stats_bar = QLabel("\u52a0\u8f7d\u4e2d...")
        self._stats_bar.setStyleSheet(
            "background:#f0f4ff;border:1px solid #b0c4f8;"
            "border-radius:4px;padding:4px 10px;"
            "color:#4a6cf7;font-size:12px;")
        root.addWidget(self._stats_bar)

        # ── sub-tabs ──────────────────────────────────────────────
        self._sub = QTabWidget(); self._sub.setDocumentMode(True)

        def _make_split(lst, det):
            w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0)
            sp = QSplitter(Qt.Horizontal)
            sp.addWidget(lst); sp.addWidget(det)
            sp.setSizes([240, 960])
            sp.setStretchFactor(0,0); sp.setStretchFactor(1,1)
            l.addWidget(sp); return w

        self._note_list   = NoteList(self._engine)
        self._note_detail = NoteDetail(self._engine)
        self._sub.addTab(
            _make_split(self._note_list, self._note_detail),
            "\U0001f9ea  \u7b14\u8bb0")

        self._card_list   = CardList(self._engine)
        self._card_detail = CardDetail(self._engine)
        self._sub.addTab(
            _make_split(self._card_list, self._card_detail),
            "\U0001f4a1  \u7ecf\u9a8c\u5361")

        self._fc_list   = FailureCaseList(self._engine)
        self._fc_detail = FailureCaseDetail(self._engine)
        self._sub.addTab(
            _make_split(self._fc_list, self._fc_detail),
            "\u274c  \u5931\u8d25\u6848\u4f8b")

        self._search_panel = SearchPanel(self._engine)
        self._sub.addTab(self._search_panel, "\U0001f50d  \u641c\u7d22")

        root.addWidget(self._sub)

        # ── status bar ────────────────────────────────────────────
        self._status = QLabel("\u5c31\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        # ── connect ───────────────────────────────────────────────
        self._note_list.selected.connect(self._note_detail.load)
        self._note_list.selected.connect(
            lambda i: self._set_status("\u7b14\u8bb0: " + (
                self._engine.get_note(i).title
                if self._engine.get_note(i) else i)))
        self._card_list.selected.connect(self._card_detail.load)
        self._card_list.selected.connect(
            lambda i: self._set_status("\u7ecf\u9a8c\u5361: " + (
                self._engine.get_card(i).title
                if self._engine.get_card(i) else i)))
        self._fc_list.selected.connect(self._fc_detail.load)
        self._fc_list.selected.connect(
            lambda i: self._set_status("\u6848\u4f8b: " + (
                self._engine.get_failure_case(i).title
                if self._engine.get_failure_case(i) else i)))

        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_del.clicked.connect(self._on_delete)
        self._btn_search.clicked.connect(self._on_search)
        self._btn_reset_s.clicked.connect(self._on_reset_search)
        self._search_box.returnPressed.connect(self._on_search)

        for ev in (EVENT_RO_KB_CREATED, EVENT_RO_KB_UPDATED,
                   EVENT_RO_KB_DELETED, EVENT_RO_KB_TAGGED):
            self._engine.event_engine.register(ev, self._on_stats_event)

        self._refresh_stats()

    # ── helpers ───────────────────────────────────────────────────

    def _current_tab(self) -> int:
        return self._sub.currentIndex()

    def _selected_id(self):
        idx = self._current_tab()
        if idx == 0: return self._note_list.selected_id()
        if idx == 1: return self._card_list.selected_id()
        if idx == 2: return self._fc_list.selected_id()
        return None

    # ── CRUD ──────────────────────────────────────────────────────

    def _on_new(self):
        idx = self._current_tab()
        if idx == 0:
            dlg = NoteDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                nt = self._engine.create_note(
                    title=dlg.get_title(), content=dlg.get_content(),
                    note_type=dlg.get_note_type(), priority=dlg.get_priority(),
                    author=dlg.get_author(), tags=dlg.get_tags())
                self._set_status("\u7b14\u8bb0\u300c" + nt.title + "\u300d\u5df2\u521b\u5efa")
                self._refresh_stats()
        elif idx == 1:
            dlg = CardDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                cd = self._engine.create_card(
                    title=dlg.get_title(), context=dlg.get_context(),
                    insight=dlg.get_insight(), lesson=dlg.get_lesson(),
                    author=dlg.get_author(), tags=dlg.get_tags())
                self._set_status("\u7ecf\u9a8c\u5361\u300c" + cd.title + "\u300d\u5df2\u521b\u5efa")
                self._refresh_stats()
        elif idx == 2:
            dlg = FailureCaseDialog(parent=self)
            if dlg.exec() == QDialog.Accepted:
                fc = self._engine.create_failure_case(
                    title=dlg.get_title(),
                    symptom=dlg.get_symptom(),
                    root_cause=dlg.get_root_cause(),
                    impact=dlg.get_impact(),
                    resolution=dlg.get_resolution(),
                    prevention=dlg.get_prevention(),
                    severity=dlg.get_severity(),
                    author=dlg.get_author(),
                    tags=dlg.get_tags())
                self._set_status("\u6848\u4f8b\u300c" + fc.title + "\u300d\u5df2\u521b\u5efa")
                self._refresh_stats()
        else:
            self._set_status("\u8bf7\u5207\u6362\u5230\u5177\u4f53\u7c7b\u522b\u518d\u65b0\u5efa")

    def _on_edit(self):
        idx = self._current_tab()
        sel = self._selected_id()
        if not sel:
            self._set_status("\u8bf7\u5148\u9009\u62e9\u8981\u7f16\u8f91\u7684\u6761\u76ee")
            return
        if idx == 0:
            nt = self._engine.get_note(sel)
            if not nt: return
            dlg = NoteDialog(parent=self, record=nt)
            if dlg.exec() == QDialog.Accepted:
                nt.title     = dlg.get_title()
                nt.note_type = dlg.get_note_type()
                nt.priority  = dlg.get_priority()
                nt.author    = dlg.get_author()
                nt.tags      = dlg.get_tags()
                nt.content   = dlg.get_content()
                self._engine.update_note(nt)
                self._note_detail.load(sel)
                self._set_status("\u7b14\u8bb0\u300c" + nt.title + "\u300d\u5df2\u66f4\u65b0")
        elif idx == 1:
            cd = self._engine.get_card(sel)
            if not cd: return
            dlg = CardDialog(parent=self, record=cd)
            if dlg.exec() == QDialog.Accepted:
                cd.title   = dlg.get_title(); cd.author  = dlg.get_author()
                cd.tags    = dlg.get_tags()
                cd.context = dlg.get_context(); cd.insight = dlg.get_insight()
                cd.lesson  = dlg.get_lesson()
                self._engine.update_card(cd)
                self._card_detail.load(sel)
                self._set_status("\u7ecf\u9a8c\u5361\u300c" + cd.title + "\u300d\u5df2\u66f4\u65b0")
        elif idx == 2:
            fc = self._engine.get_failure_case(sel)
            if not fc: return
            dlg = FailureCaseDialog(parent=self, record=fc)
            if dlg.exec() == QDialog.Accepted:
                fc.title      = dlg.get_title(); fc.severity    = dlg.get_severity()
                fc.author     = dlg.get_author(); fc.tags       = dlg.get_tags()
                fc.symptom    = dlg.get_symptom(); fc.root_cause = dlg.get_root_cause()
                fc.impact     = dlg.get_impact(); fc.resolution  = dlg.get_resolution()
                fc.prevention = dlg.get_prevention()
                self._engine.update_failure_case(fc)
                self._fc_detail.load(sel)
                self._set_status("\u6848\u4f8b\u300c" + fc.title + "\u300d\u5df2\u66f4\u65b0")

    def _on_delete(self):
        idx = self._current_tab()
        sel = self._selected_id()
        if not sel: return
        labels   = {0:"\u7b14\u8bb0", 1:"\u7ecf\u9a8c\u5361", 2:"\u5931\u8d25\u6848\u4f8b"}
        getters  = {0:self._engine.get_note, 1:self._engine.get_card,
                    2:self._engine.get_failure_case}
        deleters = {0:self._engine.delete_note, 1:self._engine.delete_card,
                    2:self._engine.delete_failure_case}
        clears   = {0:self._note_detail.clear_panel,
                    1:self._card_detail.clear_panel,
                    2:self._fc_detail.clear_panel}
        if idx not in labels: return
        obj = getters[idx](sel)
        if not obj: return
        if QMessageBox.question(
            self, "\u786e\u8ba4\u5220\u9664",
            "\u5220\u9664" + labels[idx] + "\u300c" + obj.title + "\u300d\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            deleters[idx](sel)
            clears[idx]()
            self._set_status(labels[idx] + "\u300c" + obj.title + "\u300d\u5df2\u5220\u9664")
            self._refresh_stats()

    # ── search ────────────────────────────────────────────────────

    def _on_search(self):
        kw = self._search_box.text().strip()
        if not kw: return
        idx = self._current_tab()
        if idx == 0:   self._note_list.set_keyword(kw)
        elif idx == 1: self._card_list.set_keyword(kw)
        elif idx == 2: self._fc_list.set_keyword(kw)
        elif idx == 3:
            self._search_panel._box.setText(kw)
            self._search_panel._do_search()
        self._set_status("\u641c\u7d22\u300c" + kw + "\u300d")

    def _on_reset_search(self):
        self._search_box.clear()
        for lst in (self._note_list, self._card_list, self._fc_list):
            lst.set_keyword("")
        self._set_status("\u5c31\u7eea")

    # ── stats ─────────────────────────────────────────────────────

    def _on_stats_event(self, _=None):
        self._refresh_stats()

    def _refresh_stats(self):
        s = self._engine.stats()
        self._stats_bar.setText(
            "\u7b14\u8bb0: " + str(s.get("notes", 0))
            + "    \u5df2\u5f52\u6863: " + str(s.get("archived_notes", 0))
            + "    \u7ecf\u9a8c\u5361: " + str(s.get("cards", 0))
            + "    \u5931\u8d25\u6848\u4f8b: " + str(s.get("failure_cases", 0))
            + "    \u672a\u89e3\u51b3: " + str(s.get("open_cases", 0)))

    def _set_status(self, msg: str):
        self._status.setText(msg)
