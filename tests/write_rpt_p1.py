"""write_rpt_p1.py — report_tab.py Part1: imports + dialogs"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\report_tab.py"
)

PART1 = """\
\"\"\"
research_ops/ui/report_tab.py  Phase 6 - Report System
\"\"\"
from __future__ import annotations
from typing import List, Optional, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLineEdit, QComboBox, QLabel,
    QTreeWidget, QTreeWidgetItem, QHeaderView,
    QAbstractItemView, QTabWidget, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QMenu, QMessageBox, QFrame,
    QTableWidget, QTableWidgetItem, QTextBrowser,
    QSpinBox, QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QBrush

from vnpy.event import Event
from ..main_engine import ResearchOpsEngine
from ..model.report_model import ReportRecord, ReportSection, ReportTemplate
from ..constant import ReportType, ReportFormat
from ..event import (
    EVENT_RO_RPT_CREATED, EVENT_RO_RPT_UPDATED,
    EVENT_RO_RPT_DELETED, EVENT_RO_RPT_PUBLISHED,
    EVENT_RO_RPT_RENDERED,
)

RPT_TYPE_ICON = {
    ReportType.RESEARCH:  "\\U0001f9ea",
    ReportType.BACKTEST:  "\\U0001f4c8",
    ReportType.FACTOR:    "\\U0001f4d0",
    ReportType.MODEL:     "\\U0001f916",
    ReportType.RISK:      "\\u26a0",
    ReportType.DAILY:     "\\U0001f4c5",
    ReportType.WEEKLY:    "\\U0001f5d3",
    ReportType.CUSTOM:    "\\U0001f4dd",
}
RPT_TYPE_COLOR = {
    ReportType.RESEARCH:  "#4a6cf7",
    ReportType.BACKTEST:  "#198754",
    ReportType.FACTOR:    "#9c27b0",
    ReportType.MODEL:     "#fd7e14",
    ReportType.RISK:      "#dc3545",
    ReportType.DAILY:     "#0d6efd",
    ReportType.WEEKLY:    "#17a2b8",
    ReportType.CUSTOM:    "#6c757d",
}
ROLE_ID = Qt.UserRole

# minimal markdown->html for preview (no external deps)
def _md_to_html(md: str) -> str:
    import re, html as _html
    lines = md.splitlines()
    out = ["<html><body style='font-family:sans-serif;max-width:860px;margin:20px;'>"]
    in_code = False
    for raw in lines:
        line = raw
        if line.startswith("```"):
            if in_code:
                out.append("</pre>"); in_code = False
            else:
                out.append("<pre style='background:#f8f9fa;padding:12px;border-radius:4px;overflow:auto;'>")
                in_code = True
            continue
        if in_code:
            out.append(_html.escape(line)); continue
        # headings
        m = re.match(r"^(#{1,6})\\s+(.*)", line)
        if m:
            lvl = len(m.group(1)); txt = m.group(2)
            color = "#4a6cf7" if lvl == 1 else "#1a1f36"
            out.append(f"<h{lvl} style='color:{color};'>{txt}</h{lvl}>")
            continue
        # horizontal rule
        if re.match(r"^---+$", line):
            out.append("<hr style='border:1px solid #dee2e6;'>"); continue
        # blank line
        if not line.strip():
            out.append("<br>"); continue
        # inline: bold, italic, code, links
        line = _html.escape(line)
        line = re.sub(r"\\*\\*(.+?)\\*\\*", r"<b>\\1</b>", line)
        line = re.sub(r"\\*(.+?)\\*",   r"<i>\\1</i>", line)
        line = re.sub(r"`(.+?)`",        r"<code style='background:#f0f0f0;padding:1px 4px;border-radius:2px;'>\\1</code>", line)
        line = re.sub(r"\\[(.+?)\\]\\((.+?)\\)", r"<a href='\\2'>\\1</a>", line)
        # list item
        if re.match(r"^[\\-\\*]\\s+", line):
            line = "<li>" + line[2:] + "</li>"
        else:
            line = "<p style='margin:4px 0;'>" + line + "</p>"
        out.append(line)
    if in_code:
        out.append("</pre>")
    out.append("</body></html>")
    return "\\n".join(out)


# =================================================================
# ReportDialog
# =================================================================

class ReportDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\\u7f16\\u8f91\\u62a5\\u544a" if self._editing
            else "\\u65b0\\u5efa\\u62a5\\u544a")
        self.setMinimumWidth(500)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u62a5\\u544a\\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._title = QLineEdit()
        self._title.setPlaceholderText("\\u62a5\\u544a\\u6807\\u9898")
        form.addRow("\\u6807\\u9898 *", self._title)
        self._type = QComboBox()
        for rt in ReportType:
            icon = RPT_TYPE_ICON.get(rt, "")
            self._type.addItem(icon + "  " + rt.value, rt)
        form.addRow("\\u7c7b\\u578b", self._type)
        self._author = QLineEdit()
        form.addRow("\\u4f5c\\u8005", self._author)
        self._summary = QTextEdit(); self._summary.setFixedHeight(64)
        self._summary.setPlaceholderText("\\u6446\\u8981 / \\u6982\\u8981")
        form.addRow("\\u6458\\u8981", self._summary)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\\u9017\\u53f7\\u5206\\u9694")
        form.addRow("\\u6807\\u7b7e", self._tags)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u786e\\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._title.setText(r.title)
        idx = self._type.findData(r.report_type)
        if idx >= 0: self._type.setCurrentIndex(idx)
        self._author.setText(r.author or "")
        self._summary.setPlainText(r.summary or "")
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._title.text().strip():
            self._title.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_title(self)       -> str:       return self._title.text().strip()
    def get_report_type(self) -> ReportType: return self._type.currentData()
    def get_author(self)      -> str:       return self._author.text().strip()
    def get_summary(self)     -> str:       return self._summary.toPlainText().strip()
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())


# =================================================================
# TemplateDialog
# =================================================================

class TemplateDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\\u7f16\\u8f91\\u6a21\\u677f" if self._editing
            else "\\u65b0\\u5efa\\u6a21\\u677f")
        self.setMinimumWidth(560)
        self.setMinimumHeight(460)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        top  = QHBoxLayout()
        form_grp = QGroupBox("\\u6a21\\u677f\\u4fe1\\u606f")
        form = QFormLayout(form_grp)
        self._name = QLineEdit()
        form.addRow("\\u540d\\u79f0 *", self._name)
        self._type = QComboBox()
        for rt in ReportType:
            self._type.addItem(RPT_TYPE_ICON.get(rt,"") + "  " + rt.value, rt)
        form.addRow("\\u9002\\u7528\\u7c7b\\u578b", self._type)
        self._desc = QLineEdit()
        form.addRow("\\u63cf\\u8ff0", self._desc)
        top.addWidget(form_grp)
        root.addLayout(top)
        content_grp = QGroupBox("\\u6a21\\u677f\\u5185\\u5bb9 (Markdown)")
        cl = QVBoxLayout(content_grp)
        self._content = QTextEdit()
        self._content.setFont(QFont("Consolas", 10))
        self._content.setPlaceholderText(
            "# \\u62a5\\u544a\\u6807\\u9898\\n\\n## \\u6458\\u8981\\n\\n## \\u7814\\u7a76\\u80cc\\u666f\\n\\n## \\u65b9\\u6cd5\\n\\n## \\u7ed3\\u679c\\n\\n## \\u7ed3\\u8bba")
        cl.addWidget(self._content)
        root.addWidget(content_grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u786e\\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name)
        idx = self._type.findData(r.report_type)
        if idx >= 0: self._type.setCurrentIndex(idx)
        self._desc.setText(r.description or "")
        self._content.setPlainText(r.content or "")

    def _on_ok(self):
        if not self._name.text().strip():
            self._name.setFocus(); return
        self.accept()

    def get_name(self)        -> str:        return self._name.text().strip()
    def get_report_type(self) -> ReportType: return self._type.currentData()
    def get_description(self) -> str:        return self._desc.text().strip()
    def get_content(self)     -> str:        return self._content.toPlainText()


# =================================================================
# SectionDialog
# =================================================================

class SectionDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\\u7f16\\u8f91\\u7ae0\\u8282" if self._editing
            else "\\u6dfb\\u52a0\\u7ae0\\u8282")
        self.setMinimumWidth(560)
        self.setMinimumHeight(420)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._title = QLineEdit()
        self._title.setPlaceholderText("\\u7ae0\\u8282\\u6807\\u9898")
        form.addRow("\\u6807\\u9898 *", self._title)
        self._order = QSpinBox()
        self._order.setRange(0, 999)
        form.addRow("\\u987a\\u5e8f", self._order)
        root.addLayout(form)
        content_grp = QGroupBox("\\u5185\\u5bb9 (Markdown)")
        cl = QVBoxLayout(content_grp)
        self._content = QTextEdit()
        self._content.setFont(QFont("Consolas", 10))
        cl.addWidget(self._content)
        root.addWidget(content_grp, 1)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u786e\\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._title.setText(r.title)
        self._order.setValue(r.order)
        self._content.setPlainText(r.content or "")

    def _on_ok(self):
        if not self._title.text().strip():
            self._title.setFocus(); return
        self.accept()

    def get_title(self)   -> str: return self._title.text().strip()
    def get_order(self)   -> int: return self._order.value()
    def get_content(self) -> str: return self._content.toPlainText()
"""

ast.parse(PART1)
P.write_text(PART1, encoding="utf-8")
print("PART1 written OK, lines:", len(PART1.splitlines()), "size:", P.stat().st_size)
