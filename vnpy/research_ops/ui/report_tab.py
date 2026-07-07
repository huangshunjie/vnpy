"""
research_ops/ui/report_tab.py  Phase 6 - Report System
"""
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
    ReportType.RESEARCH:  "\U0001f9ea",
    ReportType.BACKTEST:  "\U0001f4c8",
    ReportType.FACTOR:    "\U0001f4d0",
    ReportType.MODEL:     "\U0001f916",
    ReportType.RISK:      "\u26a0",
    ReportType.DAILY:     "\U0001f4c5",
    ReportType.WEEKLY:    "\U0001f5d3",
    ReportType.CUSTOM:    "\U0001f4dd",
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
        m = re.match(r"^(#{1,6})\s+(.*)", line)
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
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
        line = re.sub(r"\*(.+?)\*",   r"<i>\1</i>", line)
        line = re.sub(r"`(.+?)`",        r"<code style='background:#f0f0f0;padding:1px 4px;border-radius:2px;'>\1</code>", line)
        line = re.sub(r"\[(.+?)\]\((.+?)\)", r"<a href='\2'>\1</a>", line)
        # list item
        if re.match(r"^[\-\*]\s+", line):
            line = "<li>" + line[2:] + "</li>"
        else:
            line = "<p style='margin:4px 0;'>" + line + "</p>"
        out.append(line)
    if in_code:
        out.append("</pre>")
    out.append("</body></html>")
    return "\n".join(out)


# =================================================================
# ReportDialog
# =================================================================

class ReportDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\u7f16\u8f91\u62a5\u544a" if self._editing
            else "\u65b0\u5efa\u62a5\u544a")
        self.setMinimumWidth(500)
        self._init_ui()
        if self._editing:
            self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u62a5\u544a\u4fe1\u606f")
        form = QFormLayout(grp)
        self._title = QLineEdit()
        self._title.setPlaceholderText("\u62a5\u544a\u6807\u9898")
        form.addRow("\u6807\u9898 *", self._title)
        self._type = QComboBox()
        for rt in ReportType:
            icon = RPT_TYPE_ICON.get(rt, "")
            self._type.addItem(icon + "  " + rt.value, rt)
        form.addRow("\u7c7b\u578b", self._type)
        self._author = QLineEdit()
        form.addRow("\u4f5c\u8005", self._author)
        self._summary = QTextEdit(); self._summary.setFixedHeight(64)
        self._summary.setPlaceholderText("\u6446\u8981 / \u6982\u8981")
        form.addRow("\u6458\u8981", self._summary)
        self._tags = QLineEdit()
        self._tags.setPlaceholderText("\u9017\u53f7\u5206\u9694")
        form.addRow("\u6807\u7b7e", self._tags)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
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
            "\u7f16\u8f91\u6a21\u677f" if self._editing
            else "\u65b0\u5efa\u6a21\u677f")
        self.setMinimumWidth(560)
        self.setMinimumHeight(460)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        top  = QHBoxLayout()
        form_grp = QGroupBox("\u6a21\u677f\u4fe1\u606f")
        form = QFormLayout(form_grp)
        self._name = QLineEdit()
        form.addRow("\u540d\u79f0 *", self._name)
        self._type = QComboBox()
        for rt in ReportType:
            self._type.addItem(RPT_TYPE_ICON.get(rt,"") + "  " + rt.value, rt)
        form.addRow("\u9002\u7528\u7c7b\u578b", self._type)
        self._desc = QLineEdit()
        form.addRow("\u63cf\u8ff0", self._desc)
        top.addWidget(form_grp)
        root.addLayout(top)
        content_grp = QGroupBox("\u6a21\u677f\u5185\u5bb9 (Markdown)")
        cl = QVBoxLayout(content_grp)
        self._content = QTextEdit()
        self._content.setFont(QFont("Consolas", 10))
        self._content.setPlaceholderText(
            "# \u62a5\u544a\u6807\u9898\n\n## \u6458\u8981\n\n## \u7814\u7a76\u80cc\u666f\n\n## \u65b9\u6cd5\n\n## \u7ed3\u679c\n\n## \u7ed3\u8bba")
        cl.addWidget(self._content)
        root.addWidget(content_grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
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
            "\u7f16\u8f91\u7ae0\u8282" if self._editing
            else "\u6dfb\u52a0\u7ae0\u8282")
        self.setMinimumWidth(560)
        self.setMinimumHeight(420)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        form = QFormLayout()
        self._title = QLineEdit()
        self._title.setPlaceholderText("\u7ae0\u8282\u6807\u9898")
        form.addRow("\u6807\u9898 *", self._title)
        self._order = QSpinBox()
        self._order.setRange(0, 999)
        form.addRow("\u987a\u5e8f", self._order)
        root.addLayout(form)
        content_grp = QGroupBox("\u5185\u5bb9 (Markdown)")
        cl = QVBoxLayout(content_grp)
        self._content = QTextEdit()
        self._content.setFont(QFont("Consolas", 10))
        cl.addWidget(self._content)
        root.addWidget(content_grp, 1)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u786e\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
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


class ReportList(QWidget):
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
        for rt in ReportType:
            icon = RPT_TYPE_ICON.get(rt, "")
            self._combo.addItem(icon + " " + rt.value, rt)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels([
            "\u6807\u9898", "\u7c7b\u578b", "\u72b6\u6001"])
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
        for ev in (EVENT_RO_RPT_CREATED, EVENT_RO_RPT_UPDATED,
                   EVENT_RO_RPT_DELETED, EVENT_RO_RPT_PUBLISHED,
                   EVENT_RO_RPT_RENDERED):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()
    def _on_filter(self, _):   self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_reports()
        if self._filter:
            items = [r for r in items if r.report_type == self._filter]
        if self._keyword:
            items = [r for r in items
                     if self._keyword in r.title.lower()
                     or self._keyword in (r.author or "").lower()
                     or any(self._keyword in t for t in r.tags)]
        self._table.setRowCount(0)
        for rpt in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(rpt.title))
            icon  = RPT_TYPE_ICON.get(rpt.report_type, "")
            color = RPT_TYPE_COLOR.get(rpt.report_type, "#6c757d")
            ti    = QTableWidgetItem(icon + " " + rpt.report_type.value)
            ti.setForeground(QBrush(QColor(color)))
            self._table.setItem(r, 1, ti)
            if rpt.is_published:
                si = QTableWidgetItem("\u2705 \u5df2\u53d1\u5e03")
                si.setForeground(QBrush(QColor("#198754")))
            else:
                si = QTableWidgetItem("\u270f \u8349\u7a3f")
                si.setForeground(QBrush(QColor("#6c757d")))
            self._table.setItem(r, 2, si)
            for c in range(3):
                self._table.item(r, c).setData(ROLE_ID, rpt.report_id)

    def _on_click(self, item):
        self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        rid = item.data(ROLE_ID)
        rpt = self._engine.get_report(rid)
        if not rpt: return
        menu = QMenu(self)
        if rpt.is_published:
            a_pub = menu.addAction("\u274c  \u53d6\u6d88\u53d1\u5e03")
        else:
            a_pub = menu.addAction("\U0001f4e4  \u53d1\u5e03")
        menu.addSeparator()
        a_del = menu.addAction("\U0001f5d1  \u5220\u9664")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_pub:
            if rpt.is_published:
                self._engine.unpublish_report(rid)
            else:
                self._engine.publish_report(rid)
            self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\u786e\u8ba4",
                "\u5220\u9664\u62a5\u544a\u300c" + rpt.title + "\u300d\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_report(rid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class MarkdownEditor(QWidget):
    content_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        tb = QHBoxLayout(); tb.setSpacing(4); tb.setContentsMargins(4,4,4,4)
        for label, ins in [("H1","# "),("H2","## "),("H3","### "),
                            ("**B**","**"),("*I*","*"),("`C`","`"),
                            ("---","\n---\n"),("List","- ")]:
            btn = QPushButton(label); btn.setFixedSize(36,22)
            btn.setStyleSheet("font-size:11px;")
            btn.clicked.connect(lambda _, i=ins: self._insert(i))
            tb.addWidget(btn)
        tb.addStretch()
        root.addLayout(tb)
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color:#dee2e6;"); root.addWidget(sep)
        sp = QSplitter(Qt.Horizontal)
        self._editor = QTextEdit()
        self._editor.setFont(QFont("Consolas", 10))
        self._editor.setStyleSheet(
            "QTextEdit{background:#1e1e2e;color:#cdd6f4;border:none;padding:8px;}")
        self._editor.textChanged.connect(self._on_change)
        sp.addWidget(self._editor)
        self._preview = QTextBrowser()
        self._preview.setStyleSheet("QTextBrowser{background:#fff;border:none;padding:12px;}")
        self._preview.setOpenExternalLinks(True)
        sp.addWidget(self._preview)
        sp.setSizes([500, 500])
        root.addWidget(sp, 1)

    def _insert(self, text: str):
        cur = self._editor.textCursor(); cur.insertText(text)
        self._editor.setTextCursor(cur); self._editor.setFocus()

    def _on_change(self):
        md = self._editor.toPlainText()
        self._preview.setHtml(_md_to_html(md))
        self.content_changed.emit(md)

    def set_content(self, md: str):
        self._editor.blockSignals(True)
        self._editor.setPlainText(md)
        self._editor.blockSignals(False)
        self._preview.setHtml(_md_to_html(md))

    def get_content(self) -> str:
        return self._editor.toPlainText()

    def clear(self):
        self._editor.clear(); self._preview.clear()


class ReportDetail(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id: Optional[str] = None
        self._cur_sec_id: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        self.setDocumentMode(True)

        # ── Tab1: overview ────────────────────────────────────────
        ov = QWidget(); ov_l = QVBoxLayout(ov)
        hdr = QHBoxLayout()
        self._title = QLabel("\u8bf7\u9009\u62e9\u62a5\u544a")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._pub_badge = QLabel("")
        self._pub_badge.setFixedHeight(22)
        self._pub_badge.setStyleSheet("padding:2px 10px;border-radius:10px;font-size:12px;")
        hdr.addWidget(self._pub_badge)
        ov_l.addLayout(hdr)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._bar)
        cr = QHBoxLayout()
        self._c_secs  = self._card("\u7ae0\u8282\u6570","0")
        self._c_views = self._card("\u6d4f\u89c8\u6570","0")
        self._c_type  = self._card("\u7c7b\u578b","\u2014","#4a6cf7")
        for c in (self._c_secs, self._c_views, self._c_type):
            cr.addWidget(c)
        ov_l.addLayout(cr)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\u5c5e\u6027","\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        ov_l.addWidget(self._info)
        self.addTab(ov, "\U0001f4cb  \u6982\u89c8")

        # ── Tab2: sections editor ─────────────────────────────────
        sec_w = QWidget(); sec_l = QVBoxLayout(sec_w)
        sec_tb = QHBoxLayout()
        self._btn_add_sec  = QPushButton("\u2795 \u7ae0\u8282")
        self._btn_edit_sec = QPushButton("\u270f \u7f16\u8f91")
        self._btn_del_sec  = QPushButton("\U0001f5d1 \u5220\u9664")
        for b in (self._btn_add_sec, self._btn_edit_sec, self._btn_del_sec):
            b.setFixedHeight(26); sec_tb.addWidget(b)
        sec_tb.addStretch(); sec_l.addLayout(sec_tb)
        sec_sp = QSplitter(Qt.Vertical)
        self._sec_table = QTableWidget(0, 3)
        self._sec_table.setHorizontalHeaderLabels(
            ["\u987a\u5e8f","\u6807\u9898","\u9884\u89c8"])
        self._sec_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._sec_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._sec_table.setAlternatingRowColors(True)
        self._sec_table.verticalHeader().setVisible(False)
        self._sec_table.setFixedHeight(160)
        self._sec_table.itemClicked.connect(self._on_sec_click)
        sec_sp.addWidget(self._sec_table)
        self._sec_editor = MarkdownEditor()
        self._sec_editor.content_changed.connect(self._on_sec_content_change)
        sec_sp.addWidget(self._sec_editor)
        sec_sp.setSizes([160, 400])
        sec_l.addWidget(sec_sp, 1)
        self.addTab(sec_w, "\U0001f4dd  \u7ae0\u8282")

        # ── Tab3: full preview ────────────────────────────────────
        pv_w = QWidget(); pv_l = QVBoxLayout(pv_w)
        pv_tb = QHBoxLayout()
        self._btn_refresh = QPushButton("\U0001f504 \u5237\u65b0")
        self._btn_refresh.setFixedHeight(26)
        self._btn_refresh.clicked.connect(self._do_render)
        pv_tb.addWidget(self._btn_refresh); pv_tb.addStretch()
        pv_l.addLayout(pv_tb)
        self._browser = QTextBrowser()
        self._browser.setStyleSheet(
            "QTextBrowser{background:#fff;border:1px solid #dee2e6;"
            "border-radius:4px;padding:16px;}")
        self._browser.setOpenExternalLinks(True)
        pv_l.addWidget(self._browser, 1)
        self.addTab(pv_w, "\U0001f5fa  \u9884\u89c8")

        self._btn_add_sec.clicked.connect(self._on_add_sec)
        self._btn_edit_sec.clicked.connect(self._on_edit_sec)
        self._btn_del_sec.clicked.connect(self._on_del_sec)

    @staticmethod
    def _card(label, value, color="#1a1f36"):
        card = QFrame(); card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(
            "QFrame{background:#fff;border:1px solid #dee2e6;"
            "border-radius:8px;padding:6px;}")
        lay = QVBoxLayout(card); lay.setSpacing(2)
        lbl = QLabel(label); lbl.setStyleSheet("color:#6c757d;font-size:11px;")
        lay.addWidget(lbl)
        val = QLabel(value)
        val.setStyleSheet("font-size:20px;font-weight:bold;color:"+color+";")
        val.setAlignment(Qt.AlignCenter)
        lay.addWidget(val); card._val = val; return card

    def load(self, rpt_id: str):
        self._id = rpt_id
        rpt = self._engine.get_report(rpt_id)
        if not rpt: return
        self._load_overview(rpt)
        self._load_sections(rpt)
        self._do_render()

    def clear_panel(self):
        self._id = None; self._cur_sec_id = None
        self._title.setText("\u8bf7\u9009\u62e9\u62a5\u544a")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        self._pub_badge.setText(""); self._pub_badge.setStyleSheet("")
        for c in (self._c_secs, self._c_views, self._c_type):
            c._val.setText("\u2014")
        self._info.setRowCount(0)
        self._sec_table.setRowCount(0)
        self._sec_editor.clear(); self._browser.clear()

    def _load_overview(self, rpt: ReportRecord):
        self._title.setText(rpt.title)
        color = RPT_TYPE_COLOR.get(rpt.report_type, "#6c757d")
        self._bar.setStyleSheet("background:"+color+";border-radius:2px;")
        if rpt.is_published:
            self._pub_badge.setText("\u2705 \u5df2\u53d1\u5e03")
            self._pub_badge.setStyleSheet(
                "padding:2px 10px;border-radius:10px;"
                "background:#d1e7dd;color:#198754;"
                "font-size:12px;border:1px solid #a3cfbb;")
        else:
            self._pub_badge.setText("\u270f \u8349\u7a3f")
            self._pub_badge.setStyleSheet(
                "padding:2px 10px;border-radius:10px;"
                "background:#f8f9fa;color:#6c757d;"
                "font-size:12px;border:1px solid #dee2e6;")
        icon = RPT_TYPE_ICON.get(rpt.report_type,"")
        self._c_secs._val.setText(str(len(rpt.sections)))
        self._c_views._val.setText(str(rpt.view_count or 0))
        self._c_type._val.setText(icon+" "+rpt.report_type.value)
        self._c_type._val.setStyleSheet(
            "font-size:14px;font-weight:bold;color:"+color+";")
        self._info.setRowCount(0)
        pub_at = rpt.published_at.strftime("%Y-%m-%d %H:%M") if rpt.published_at else "\u2014"
        for k, v in [
            ("ID", rpt.report_id[:16]),("\u6807\u9898", rpt.title),
            ("\u7c7b\u578b", rpt.report_type.value),
            ("\u4f5c\u8005", rpt.author or "\u2014"),
            ("\u6458\u8981", (rpt.summary or "\u2014")[:80]),
            ("\u6807\u7b7e", ", ".join(rpt.tags) if rpt.tags else "\u2014"),
            ("\u53d1\u5e03\u65f6\u95f4", pub_at),
            ("\u521b\u5efa", rpt.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))

    def _load_sections(self, rpt: ReportRecord):
        self._sec_table.setRowCount(0)
        for sec in sorted(rpt.sections, key=lambda s: s.order):
            r = self._sec_table.rowCount(); self._sec_table.insertRow(r)
            oi = QTableWidgetItem(str(sec.order)); oi.setTextAlignment(Qt.AlignCenter)
            self._sec_table.setItem(r, 0, oi)
            self._sec_table.setItem(r, 1, QTableWidgetItem(sec.title))
            prev = (sec.content or "")[:60].replace("\n"," ")
            self._sec_table.setItem(r, 2, QTableWidgetItem(prev))
            for c in range(3):
                self._sec_table.item(r, c).setData(ROLE_ID, sec.section_id)

    def _on_sec_click(self, item):
        self._cur_sec_id = item.data(ROLE_ID)
        if not self._id: return
        rpt = self._engine.get_report(self._id)
        if not rpt: return
        sec = next((s for s in rpt.sections if s.section_id == self._cur_sec_id), None)
        if sec:
            self._sec_editor.content_changed.disconnect()
            self._sec_editor.set_content(sec.content or "")
            self._sec_editor.content_changed.connect(self._on_sec_content_change)

    def _on_sec_content_change(self, md: str):
        if not self._id or not self._cur_sec_id: return
        self._engine.update_section(self._id, self._cur_sec_id, content=md)

    def _on_add_sec(self):
        if not self._id: return
        dlg = SectionDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            sec = self._engine.add_section(
                self._id, title=dlg.get_title(),
                content=dlg.get_content(), order=dlg.get_order())
            if sec:
                rpt = self._engine.get_report(self._id)
                self._load_sections(rpt)
                self._c_secs._val.setText(str(len(rpt.sections)))

    def _on_edit_sec(self):
        if not self._id or not self._cur_sec_id: return
        rpt = self._engine.get_report(self._id)
        if not rpt: return
        sec = next((s for s in rpt.sections if s.section_id == self._cur_sec_id), None)
        if not sec: return
        dlg = SectionDialog(parent=self, record=sec)
        if dlg.exec() == QDialog.Accepted:
            self._engine.update_section(
                self._id, sec.section_id,
                title=dlg.get_title(), content=dlg.get_content())
            self._load_sections(self._engine.get_report(self._id))

    def _on_del_sec(self):
        if not self._id or not self._cur_sec_id: return
        rpt = self._engine.get_report(self._id)
        if not rpt: return
        sec = next((s for s in rpt.sections if s.section_id == self._cur_sec_id), None)
        if not sec: return
        if QMessageBox.question(
            self, "\u786e\u8ba4",
            "\u5220\u9664\u7ae0\u8282\u300c"+sec.title+"\u300d\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._engine.remove_section(self._id, sec.section_id)
            self._cur_sec_id = None
            self._load_sections(self._engine.get_report(self._id))
            self._sec_editor.clear()

    def _do_render(self):
        if not self._id: return
        md = self._engine.render_markdown(self._id)
        self._browser.setHtml(_md_to_html(md))


class TemplatePanel(QWidget):
    apply_requested = Signal(str)   # template_id

    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout()
        self._btn_new = QPushButton("+ \u65b0\u5efa\u6a21\u677f")
        self._btn_apply = QPushButton("\u2b07 \u5e94\u7528\u5230\u62a5\u544a")
        self._btn_del = QPushButton("\U0001f5d1 \u5220\u9664")
        for b in (self._btn_new, self._btn_apply, self._btn_del):
            b.setFixedHeight(26); tb.addWidget(b)
        tb.addStretch(); root.addLayout(tb)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(
            ["\u540d\u79f0","\u9002\u7528\u7c7b\u578b","\u63cf\u8ff0"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setFixedHeight(160)
        root.addWidget(self._table)

        prev_grp = QGroupBox("\u6a21\u677f\u5185\u5bb9\u9884\u89c8")
        prev_l = QVBoxLayout(prev_grp)
        self._prev = QTextEdit()
        self._prev.setReadOnly(True)
        self._prev.setFont(QFont("Consolas", 9))
        self._prev.setStyleSheet(
            "background:#f8f9fa;border:1px solid #dee2e6;border-radius:4px;")
        self._prev.setFixedHeight(120)
        prev_l.addWidget(self._prev)
        root.addWidget(prev_grp)

        self._table.itemClicked.connect(self._on_click)
        self._btn_new.clicked.connect(self._on_new)
        self._btn_apply.clicked.connect(self._on_apply)
        self._btn_del.clicked.connect(self._on_del)

    def _refresh(self):
        self._table.setRowCount(0)
        for tmpl in self._engine.list_templates():
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(tmpl.name))
            color = RPT_TYPE_COLOR.get(tmpl.report_type, "#6c757d")
            ti = QTableWidgetItem(
                RPT_TYPE_ICON.get(tmpl.report_type,"") + " " + tmpl.report_type.value)
            ti.setForeground(QBrush(QColor(color)))
            self._table.setItem(r, 1, ti)
            self._table.setItem(r, 2, QTableWidgetItem(tmpl.description or ""))
            for c in range(3):
                self._table.item(r, c).setData(ROLE_ID, tmpl.template_id)

    def _on_click(self, item):
        tid = item.data(ROLE_ID)
        tmpl = self._engine.get_template(tid)
        if tmpl:
            self._prev.setPlainText(tmpl.content or "")

    def _selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None

    def _on_new(self):
        dlg = TemplateDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self._engine.create_template(
                name=dlg.get_name(),
                content=dlg.get_content(),
                description=dlg.get_description(),
                report_type=dlg.get_report_type(),
            )
            self._refresh()

    def _on_apply(self):
        tid = self._selected_id()
        if not tid:
            QMessageBox.information(
                self, "\u63d0\u793a",
                "\u8bf7\u5148\u9009\u62e9\u4e00\u4e2a\u6a21\u677f")
            return
        self.apply_requested.emit(tid)

    def _on_del(self):
        tid = self._selected_id()
        if not tid: return
        tmpl = self._engine.get_template(tid)
        if not tmpl: return
        if QMessageBox.question(
            self, "\u786e\u8ba4",
            "\u5220\u9664\u6a21\u677f\u300c" + tmpl.name + "\u300d\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            # no delete_template in engine — just remove from list via update
            QMessageBox.information(
                self, "\u63d0\u793a",
                "\u5f53\u524d\u5f15\u64ce\u4e0d\u652f\u6301\u5220\u9664\u6a21\u677f\uff0c\u8bf7\u624b\u52a8\u6e05\u7406")


class ReportTab(QWidget):
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
        self._btn_new    = QPushButton("+ \u65b0\u5efa")
        self._btn_edit   = QPushButton("\u270f  \u7f16\u8f91")
        self._btn_pub    = QPushButton("\U0001f4e4  \u53d1\u5e03")
        self._btn_del    = QPushButton("\U0001f5d1  \u5220\u9664")
        for btn in (self._btn_new, self._btn_edit,
                    self._btn_pub, self._btn_del):
            btn.setFixedHeight(28); tb.addWidget(btn)
        sep = QFrame(); sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color:#dee2e6;"); tb.addWidget(sep)
        tb.addStretch()
        tb.addWidget(QLabel("\u641c\u7d22:"))
        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("\u6807\u9898 / \u4f5c\u8005 / \u6807\u7b7e...")
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
            "background:#e8f4fd;border:1px solid #9ec5fe;"
            "border-radius:4px;padding:4px 10px;"
            "color:#0d6efd;font-size:12px;")
        root.addWidget(self._stats_bar)

        # ── main area: sub-tabs (报告 / 模板) ─────────────────────
        self._sub = QTabWidget(); self._sub.setDocumentMode(True)

        # Tab1: 报告列表 + 详情
        rpt_w = QWidget(); rpt_l = QHBoxLayout(rpt_w)
        rpt_l.setContentsMargins(0,0,0,0)
        sp = QSplitter(Qt.Horizontal)
        self._rpt_list   = ReportList(self._engine)
        self._rpt_detail = ReportDetail(self._engine)
        sp.addWidget(self._rpt_list); sp.addWidget(self._rpt_detail)
        sp.setSizes([240, 960])
        sp.setStretchFactor(0,0); sp.setStretchFactor(1,1)
        rpt_l.addWidget(sp)
        self._sub.addTab(rpt_w, "\U0001f4dd  \u62a5\u544a")

        # Tab2: 模板管理
        self._tmpl_panel = TemplatePanel(self._engine)
        self._sub.addTab(self._tmpl_panel, "\U0001f4c4  \u6a21\u677f")

        root.addWidget(self._sub)

        # ── status bar ────────────────────────────────────────────
        self._status = QLabel("\u5c31\u7eea")
        self._status.setStyleSheet("color:#6c757d;font-size:11px;")
        root.addWidget(self._status)

        # ── connect ───────────────────────────────────────────────
        self._rpt_list.selected.connect(self._on_rpt_selected)
        self._tmpl_panel.apply_requested.connect(self._on_apply_template)

        self._btn_new.clicked.connect(self._on_new)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_pub.clicked.connect(self._on_publish)
        self._btn_del.clicked.connect(self._on_delete)
        self._btn_search.clicked.connect(self._on_search)
        self._btn_reset_s.clicked.connect(self._on_reset_search)
        self._search_box.returnPressed.connect(self._on_search)

        for ev in (EVENT_RO_RPT_CREATED, EVENT_RO_RPT_UPDATED,
                   EVENT_RO_RPT_DELETED, EVENT_RO_RPT_PUBLISHED,
                   EVENT_RO_RPT_RENDERED):
            self._engine.event_engine.register(ev, self._on_stats_event)

        self._refresh_stats()

    # ── helpers ───────────────────────────────────────────────────

    def _current_rpt_id(self) -> Optional[str]:
        return self._rpt_list.selected_id()

    # ── CRUD ──────────────────────────────────────────────────────

    def _on_new(self):
        dlg = ReportDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            rpt = self._engine.create_report(
                title       = dlg.get_title(),
                report_type = dlg.get_report_type(),
                author      = dlg.get_author(),
                summary     = dlg.get_summary(),
                tags        = dlg.get_tags(),
            )
            self._set_status("\u62a5\u544a\u300c" + rpt.title + "\u300d\u5df2\u521b\u5efa")
            self._refresh_stats()

    def _on_edit(self):
        rid = self._current_rpt_id()
        if not rid:
            self._set_status("\u8bf7\u5148\u9009\u62e9\u62a5\u544a"); return
        rpt = self._engine.get_report(rid)
        if not rpt: return
        dlg = ReportDialog(parent=self, record=rpt)
        if dlg.exec() == QDialog.Accepted:
            rpt.title       = dlg.get_title()
            rpt.report_type = dlg.get_report_type()
            rpt.author      = dlg.get_author()
            rpt.summary     = dlg.get_summary()
            rpt.tags        = dlg.get_tags()
            self._engine.update_report(rpt)
            self._rpt_detail.load(rid)
            self._set_status("\u62a5\u544a\u300c" + rpt.title + "\u300d\u5df2\u66f4\u65b0")

    def _on_publish(self):
        rid = self._current_rpt_id()
        if not rid:
            self._set_status("\u8bf7\u5148\u9009\u62e9\u62a5\u544a"); return
        rpt = self._engine.get_report(rid)
        if not rpt: return
        if rpt.is_published:
            self._engine.unpublish_report(rid)
            self._set_status("\u62a5\u544a\u300c" + rpt.title + "\u300d\u5df2\u53d6\u6d88\u53d1\u5e03")
        else:
            self._engine.publish_report(rid)
            self._set_status("\u62a5\u544a\u300c" + rpt.title + "\u300d\u5df2\u53d1\u5e03")
        self._rpt_detail.load(rid)
        self._refresh_stats()

    def _on_delete(self):
        rid = self._current_rpt_id()
        if not rid: return
        rpt = self._engine.get_report(rid)
        if not rpt: return
        if QMessageBox.question(
            self, "\u786e\u8ba4\u5220\u9664",
            "\u5220\u9664\u62a5\u544a\u300c" + rpt.title + "\u300d\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._engine.delete_report(rid)
            self._rpt_detail.clear_panel()
            self._set_status("\u62a5\u544a\u300c" + rpt.title + "\u300d\u5df2\u5220\u9664")
            self._refresh_stats()

    # ── template apply ────────────────────────────────────────────

    def _on_apply_template(self, tid: str):
        rid = self._current_rpt_id()
        if not rid:
            QMessageBox.information(
                self, "\u63d0\u793a",
                "\u8bf7\u5148\u5728\u300e\u62a5\u544a\u300f\u9875\u9009\u4e2d\u76ee\u6807\u62a5\u544a")
            return
        self._engine.apply_template(tid, rid)
        self._rpt_detail.load(rid)
        tmpl = self._engine.get_template(tid)
        tname = tmpl.name if tmpl else tid[:8]
        self._set_status("\u6a21\u677f\u300c" + tname + "\u300d\u5df2\u5e94\u7528")

    # ── search ────────────────────────────────────────────────────

    def _on_search(self):
        kw = self._search_box.text().strip()
        if not kw: return
        self._rpt_list.set_keyword(kw)
        results = self._engine.search_reports(kw)
        self._set_status(
            "\u641c\u7d22\u300c" + kw + "\u300d\uff1a\u627e\u5230 "
            + str(len(results)) + " \u4e2a\u62a5\u544a")

    def _on_reset_search(self):
        self._search_box.clear()
        self._rpt_list.set_keyword("")
        self._set_status("\u5c31\u7eea")

    # ── selection ─────────────────────────────────────────────────

    def _on_rpt_selected(self, rpt_id: str):
        self._rpt_detail.load(rpt_id)
        rpt = self._engine.get_report(rpt_id)
        if rpt:
            pub = " [\u5df2\u53d1\u5e03]" if rpt.is_published else " [\u8349\u7a3f]"
            self._set_status("\u62a5\u544a: " + rpt.title + pub)

    # ── stats ─────────────────────────────────────────────────────

    def _on_stats_event(self, _=None):
        self._refresh_stats()
        rid = self._current_rpt_id()
        if rid:
            self._rpt_detail.load(rid)

    def _refresh_stats(self):
        s = self._engine.stats()
        self._stats_bar.setText(
            "\u62a5\u544a\u603b\u6570: " + str(s.get("reports", 0))
            + "    \u5df2\u53d1\u5e03: " + str(s.get("published", 0))
            + "    \u8349\u7a3f: "         + str(s.get("drafts", 0))
            + "    \u6a21\u677f: "         + str(s.get("templates", 0)))

    def _set_status(self, msg: str):
        self._status.setText(msg)
