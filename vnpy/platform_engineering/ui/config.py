"""
platform_engineering/ui/config.py
ConfigTab — Phase 6
配置列表 + JSON 编辑器 + 版本历史 + Diff 视图
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QLineEdit,
    QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QTextEdit, QPlainTextEdit,
    QMenu, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush, QFont, QSyntaxHighlighter, QTextCharFormat

if TYPE_CHECKING:
    from ..engine_main import PlatformEngine

from ..constant import ConfigType

TYPE_COLOR = {
    ConfigType.STRATEGY:  "#4a6cf7",
    ConfigType.RISK:      "#ff4d4f",
    ConfigType.EXECUTION: "#faad14",
    ConfigType.DATA:      "#1890ff",
    ConfigType.SYSTEM:    "#722ed1",
}
ROLE_ID  = Qt.UserRole
ROLE_VER = Qt.UserRole + 1


class _JsonHighlighter(QSyntaxHighlighter):
    """简单 JSON 语法高亮。"""
    def __init__(self, doc):
        super().__init__(doc)
        self._fmt_key  = QTextCharFormat(); self._fmt_key.setForeground(QColor("#4a6cf7"))
        self._fmt_str  = QTextCharFormat(); self._fmt_str.setForeground(QColor("#52c41a"))
        self._fmt_num  = QTextCharFormat(); self._fmt_num.setForeground(QColor("#fa8c16"))
        self._fmt_bool = QTextCharFormat(); self._fmt_bool.setForeground(QColor("#eb2f96"))
        self._fmt_null = QTextCharFormat(); self._fmt_null.setForeground(QColor("#8c8c8c"))

    def highlightBlock(self, text: str):
        import re
        for m in re.finditer(r'"([^"\\]|\\.)*"\s*:', text):
            self.setFormat(m.start(), m.end()-m.start(), self._fmt_key)
        for m in re.finditer(r':\s*"([^"\\]|\\.)*"', text):
            self.setFormat(m.start()+1, m.end()-m.start()-1, self._fmt_str)
        for m in re.finditer(r'(?<![":])\b-?\d+\.?\d*\b', text):
            self.setFormat(m.start(), m.end()-m.start(), self._fmt_num)
        for m in re.finditer(r'\b(true|false)\b', text):
            self.setFormat(m.start(), m.end()-m.start(), self._fmt_bool)
        for m in re.finditer(r'\bnull\b', text):
            self.setFormat(m.start(), m.end()-m.start(), self._fmt_null)


class CreateConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\u521b\u5efa\u914d\u7f6e\u9879")
        self.setMinimumWidth(480)
        root = QVBoxLayout(self)
        grp  = QGroupBox("\u57fa\u672c\u4fe1\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit(); self._name.setPlaceholderText("\u914d\u7f6e\u540d\u79f0")
        form.addRow("\u540d\u79f0 *", self._name)
        self._type = QComboBox()
        for t in ConfigType: self._type.addItem(t.value, t)
        form.addRow("\u7c7b\u578b", self._type)
        self._owner = QLineEdit()
        form.addRow("\u8d23\u4efb\u4eba", self._owner)
        self._desc = QLineEdit()
        form.addRow("\u63cf\u8ff0", self._desc)
        self._tags = QLineEdit(); self._tags.setPlaceholderText("tag1,tag2")
        form.addRow("\u6807\u7b7e", self._tags)
        root.addWidget(grp)
        dg = QGroupBox("\u521d\u59cb\u6570\u636e (JSON)")
        dl = QVBoxLayout(dg)
        self._data_edit = QPlainTextEdit()
        self._data_edit.setPlaceholderText('{\"key\": \"value\"}')
        self._data_edit.setFixedHeight(120)
        f = QFont("Consolas", 10); self._data_edit.setFont(f)
        _JsonHighlighter(self._data_edit.document())
        dl.addWidget(self._data_edit)
        root.addWidget(dg)
        ng = QGroupBox("\u5907\u6ce8")
        nl = QVBoxLayout(ng)
        self._note = QLineEdit()
        nl.addWidget(self._note)
        root.addWidget(ng)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\u521b\u5efa")
        btns.button(QDialogButtonBox.Cancel).setText("\u53d6\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._name.text().strip(): self._name.setFocus(); return
        try:
            import json; json.loads(self._data_edit.toPlainText() or "{}")
        except Exception as e:
            QMessageBox.warning(self, "JSON \u9519\u8bef", str(e)); return
        self.accept()

    def get_name(self)    -> str:        return self._name.text().strip()
    def get_type(self)    -> ConfigType: return self._type.currentData()
    def get_owner(self)   -> str:        return self._owner.text().strip()
    def get_desc(self)    -> str:        return self._desc.text().strip()
    def get_tags(self):
        r = self._tags.text().strip()
        return [t.strip() for t in r.split(",") if t.strip()] if r else []
    def get_note(self)    -> str:        return self._note.text().strip()
    def get_data(self)    -> dict:
        import json; return json.loads(self._data_edit.toPlainText() or "{}")


class ConfigList(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._on_select = None
        self._type_filter = None
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_new = QPushButton("\u2795 \u65b0\u5efa")
        self._btn_new.setFixedHeight(26)
        self._btn_new.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_new.clicked.connect(self._on_new)
        tb.addWidget(self._btn_new)
        self._type_combo = QComboBox(); self._type_combo.setFixedHeight(26)
        self._type_combo.addItem("\u5168\u90e8\u7c7b\u578b", None)
        for t in ConfigType: self._type_combo.addItem(t.value, t)
        self._type_combo.currentIndexChanged.connect(self._on_filter)
        tb.addWidget(self._type_combo, 1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("\u641c\u7d22...")
        self._search.setFixedHeight(26)
        self._search.textChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._search)
        root.addLayout(tb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\u540d\u79f0","\u7c7b\u578b","\u8d23\u4efb\u4eba","\u66f4\u65b0\u65f6\u95f4"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setContextMenuPolicy(Qt.CustomContextMenu)
        self._table.itemClicked.connect(self._on_click)
        self._table.customContextMenuRequested.connect(self._on_ctx)
        root.addWidget(self._table)

    def set_select_callback(self, cb): self._on_select = cb

    def refresh(self):
        if not self._engine: return
        kw    = self._search.text().strip().lower()
        items = (self._engine.config.search_configs(kw) if kw
                 else self._engine.config.list_configs(config_type=self._type_filter))
        self._table.setRowCount(0)
        for c in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            lbl = c.name + (" \U0001f512" if c.is_locked else "")
            self._table.setItem(r, 0, QTableWidgetItem(lbl))
            color = TYPE_COLOR.get(c.config_type, "#8c8c8c")
            ti = QTableWidgetItem(c.config_type.value)
            ti.setForeground(QBrush(QColor(color)))
            self._table.setItem(r, 1, ti)
            self._table.setItem(r, 2, QTableWidgetItem(c.owner or "\u2014"))
            self._table.setItem(r, 3,
                QTableWidgetItem(c.updated_at.strftime("%m-%d %H:%M")))
            for col in range(4):
                self._table.item(r, col).setData(ROLE_ID, c.config_id)

    def _on_filter(self, _):
        self._type_filter = self._type_combo.currentData(); self.refresh()

    def _on_click(self, item):
        if self._on_select: self._on_select(item.data(ROLE_ID))

    def _on_new(self):
        if not self._engine: return
        dlg = CreateConfigDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._engine.config.create_config(
                name=dlg.get_name(), config_type=dlg.get_type(),
                data=dlg.get_data(), description=dlg.get_desc(),
                owner=dlg.get_owner(), tags=dlg.get_tags(),
                note=dlg.get_note())
            self.refresh()

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        cid = item.data(ROLE_ID)
        rec = self._engine.config.get_config(cid)
        if not rec: return
        menu = QMenu(self)
        a_lock = menu.addAction(
            "\U0001f513  \u89e3\u9501" if rec.is_locked else "\U0001f512  \u9501\u5b9a")
        a_del  = menu.addAction("\U0001f5d1  \u5220\u9664")
        act = menu.exec(self._table.viewport().mapToGlobal(pos))
        try:
            if act == a_lock:
                self._engine.config.unlock(cid) if rec.is_locked                     else self._engine.config.lock(cid)
            elif act == a_del:
                self._engine.config.delete_config(cid)
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self, "\u9519\u8bef", str(e))
        self.refresh()
        if self._on_select and act == a_del: self._on_select(None)
        elif self._on_select: self._on_select(cid)


class DetailPanel(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine; self._cid = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 0, 0, 0); root.setSpacing(8)
        hdr = QHBoxLayout()
        self._title = QLabel("\u8bf7\u9009\u62e9\u914d\u7f6e\u9879")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._badge = QLabel("")
        self._badge.setStyleSheet("font-size:14px;padding:2px 10px;border-radius:10px;")
        hdr.addWidget(self._badge)
        root.addLayout(hdr)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        root.addWidget(self._bar)

        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_save = QPushButton("\U0001f4be  \u4fdd\u5b58")
        self._btn_save.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_save.setFixedHeight(28); self._btn_save.clicked.connect(self._on_save)
        tb.addWidget(self._btn_save)
        self._btn_fmt = QPushButton("\u2728  \u683c\u5f0f\u5316")
        self._btn_fmt.setFixedHeight(28); self._btn_fmt.clicked.connect(self._on_fmt)
        tb.addWidget(self._btn_fmt)
        self._btn_lock = QPushButton("\U0001f512  \u9501\u5b9a")
        self._btn_lock.setFixedHeight(28); self._btn_lock.clicked.connect(self._on_lock)
        tb.addWidget(self._btn_lock)
        self._btn_export = QPushButton("\U0001f4e4  \u5bfc\u51fa")
        self._btn_export.setFixedHeight(28); self._btn_export.clicked.connect(self._on_export)
        tb.addWidget(self._btn_export)
        tb.addStretch()
        self._meta = QLabel("")
        self._meta.setStyleSheet("font-size:14px;color:#8c8c8c;")
        tb.addWidget(self._meta)
        root.addLayout(tb)

        self._sub = QTabWidget(); self._sub.setDocumentMode(True)
        # editor tab
        ew = QWidget(); el = QVBoxLayout(ew); el.setContentsMargins(0,4,0,0)
        self._note_in = QLineEdit()
        self._note_in.setPlaceholderText("\u4fee\u6539\u5907\u6ce8...")
        self._note_in.setFixedHeight(26); el.addWidget(self._note_in)
        self._editor = QPlainTextEdit()
        f = QFont("Consolas", 10); self._editor.setFont(f)
        _JsonHighlighter(self._editor.document())
        el.addWidget(self._editor)
        self._sub.addTab(ew, "\U0001f4dd  \u7f16\u8f91\u5668")
        # version tab
        vw = QWidget(); vl = QVBoxLayout(vw); vl.setContentsMargins(0,4,0,0)
        self._ver_tbl = QTableWidget(0, 4)
        self._ver_tbl.setHorizontalHeaderLabels(["\u7248\u672c","\u5907\u6ce8","\u4f5c\u8005","\u65f6\u95f4"])
        self._ver_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._ver_tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ver_tbl.setAlternatingRowColors(True)
        self._ver_tbl.verticalHeader().setVisible(False)
        self._ver_tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._ver_tbl.setContextMenuPolicy(Qt.CustomContextMenu)
        self._ver_tbl.customContextMenuRequested.connect(self._on_ver_ctx)
        vl.addWidget(self._ver_tbl)
        self._sub.addTab(vw, "\U0001f553  \u7248\u672c\u5386\u53f2")
        # diff tab
        dw = QWidget(); dl = QVBoxLayout(dw); dl.setContentsMargins(0,4,0,0)
        dh = QHBoxLayout()
        dh.addWidget(QLabel("A:"))
        self._da = QComboBox(); dh.addWidget(self._da, 1)
        dh.addWidget(QLabel("B:"))
        self._db = QComboBox(); dh.addWidget(self._db, 1)
        bdf = QPushButton("\u5bf9\u6bd4")
        bdf.setFixedHeight(26)
        bdf.setStyleSheet("background:#722ed1;color:#fff;border-radius:4px;border:none;")
        bdf.clicked.connect(self._on_diff); dh.addWidget(bdf)
        dl.addLayout(dh)
        self._diff_view = QPlainTextEdit(); self._diff_view.setReadOnly(True)
        df = QFont("Consolas", 10); self._diff_view.setFont(df)
        dl.addWidget(self._diff_view)
        self._sub.addTab(dw, "\U0001f50d  Diff")
        root.addWidget(self._sub, 1)

    def load(self, cid):
        self._cid = cid
        if not cid:
            self._title.setText("\u8bf7\u9009\u62e9\u914d\u7f6e\u9879"); return
        rec = self._engine.config.get_config(cid)
        if rec: self._render(rec)

    def _render(self, rec):
        import json
        color = TYPE_COLOR.get(rec.config_type, "#4a6cf7")
        self._title.setText(rec.name + (" \U0001f512" if rec.is_locked else ""))
        self._bar.setStyleSheet(f"background:{color};border-radius:2px;")
        self._badge.setText(rec.config_type.value)
        self._badge.setStyleSheet(
            f"font-size:14px;padding:2px 10px;border-radius:10px;"
            f"background:{color}22;color:{color};border:1px solid {color}44;")
        self._btn_save.setEnabled(not rec.is_locked)
        self._btn_lock.setText("\U0001f513  \u89e3\u9501" if rec.is_locked
                               else "\U0001f512  \u9501\u5b9a")
        self._meta.setText(
            f"\u8d23\u4efb\u4eba: {rec.owner or '\u2014'}"
            f"  \u7248\u672c: {len(rec.versions)}"
            f"  \u66f4\u65b0: {rec.updated_at.strftime('%H:%M:%S')}")
        self._editor.setPlainText(
            json.dumps(rec.current_data, ensure_ascii=False, indent=2))
        self._ver_tbl.setRowCount(0)
        self._da.clear(); self._db.clear()
        for ver in reversed(rec.versions):
            r = self._ver_tbl.rowCount(); self._ver_tbl.insertRow(r)
            self._ver_tbl.setItem(r, 0, QTableWidgetItem(ver.version_tag))
            self._ver_tbl.setItem(r, 1, QTableWidgetItem(ver.note))
            self._ver_tbl.setItem(r, 2, QTableWidgetItem(ver.created_by or "\u2014"))
            self._ver_tbl.setItem(r, 3,
                QTableWidgetItem(ver.created_at.strftime("%m-%d %H:%M")))
            for c in range(4):
                self._ver_tbl.item(r, c).setData(ROLE_VER, ver.version_id)
            lbl = f"{ver.version_tag} ({ver.created_at.strftime('%m-%d')})"
            self._da.addItem(lbl, ver.version_id)
            self._db.addItem(lbl, ver.version_id)
        if self._db.count() >= 2:
            self._da.setCurrentIndex(min(1, self._da.count()-1))
            self._db.setCurrentIndex(0)

    def _on_ver_ctx(self, pos):
        item = self._ver_tbl.itemAt(pos)
        if not item or not self._cid: return
        vid  = item.data(ROLE_VER)
        menu = QMenu(self)
        a_rb   = menu.addAction("\u21a9  \u56de\u6eda\u5230\u6b64\u7248\u672c")
        a_diff = menu.addAction("\U0001f50d  \u4e0e\u5f53\u524d\u7248\u672c Diff")
        act = menu.exec(self._ver_tbl.viewport().mapToGlobal(pos))
        try:
            if act == a_rb:
                self._engine.config.rollback_config(self._cid, vid)
                self.load(self._cid)
            elif act == a_diff:
                entries, summary = self._engine.config.diff_with_current(self._cid, vid)
                self._show_diff(entries, summary); self._sub.setCurrentIndex(2)
        except Exception as e:
            QMessageBox.warning(self, "\u9519\u8bef", str(e))

    def _on_save(self):
        if not self._cid: return
        import json
        try: data = json.loads(self._editor.toPlainText())
        except Exception as e:
            QMessageBox.warning(self, "JSON \u9519\u8bef", str(e)); return
        note = self._note_in.text().strip() or "\u66f4\u65b0\u914d\u7f6e"
        try:
            self._engine.config.update_config(self._cid, data, note=note)
            self._note_in.clear(); self.load(self._cid)
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self, "\u9519\u8bef", str(e))

    def _on_fmt(self):
        import json
        try:
            obj = json.loads(self._editor.toPlainText())
            self._editor.setPlainText(json.dumps(obj, ensure_ascii=False, indent=2))
        except Exception: pass

    def _on_lock(self):
        if not self._cid: return
        rec = self._engine.config.get_config(self._cid)
        try:
            self._engine.config.unlock(self._cid) if rec.is_locked                 else self._engine.config.lock(self._cid)
            self.load(self._cid)
        except Exception as e:
            QMessageBox.warning(self, "\u9519\u8bef", str(e))

    def _on_export(self):
        if not self._cid: return
        try:
            js = self._engine.config.export_config(self._cid)
            dlg = QDialog(self); dlg.setWindowTitle("\u5bfc\u51fa JSON")
            dlg.setMinimumSize(500, 360)
            vl = QVBoxLayout(dlg)
            te = QPlainTextEdit(js); te.setReadOnly(True)
            te.setFont(QFont("Consolas", 10)); vl.addWidget(te)
            btns = QDialogButtonBox(QDialogButtonBox.Close)
            btns.rejected.connect(dlg.reject); vl.addWidget(btns)
            dlg.exec()
        except Exception as e:
            QMessageBox.warning(self, "\u9519\u8bef", str(e))

    def _on_diff(self):
        if not self._cid: return
        va = self._da.currentData(); vb = self._db.currentData()
        if not va or not vb or va == vb:
            self._diff_view.setPlainText("\u8bf7\u9009\u62e9\u4e0d\u540c\u7248\u672c"); return
        entries, summary = self._engine.config.diff_versions(self._cid, va, vb)
        self._show_diff(entries, summary)

    def _show_diff(self, entries, summary):
        lines = [f"\u5dee\u5f02\u6c47\u603b: {summary}", ""]
        lines += [str(e) for e in entries]
        self._diff_view.setPlainText("\n".join(lines) if entries else "\u65e0\u5dee\u5f02")


class ConfigTab(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(5_000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()
        self._refresh()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12); root.setSpacing(8)
        hdr = QHBoxLayout()
        title = QLabel("\U0001f5c2\ufe0f  Configuration Management")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("font-size:14px;color:#8c8c8c;")
        hdr.addWidget(self._stats_lbl)
        btn = QPushButton("\U0001f504 \u5237\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:14px;border:none;")
        btn.clicked.connect(self._refresh)
        hdr.addWidget(btn)
        root.addLayout(hdr)

        sp = QSplitter(Qt.Horizontal)
        self._config_list  = ConfigList(self._engine)
        self._detail_panel = DetailPanel(self._engine)
        self._config_list.set_select_callback(self._on_selected)
        sp.addWidget(self._config_list)
        sp.addWidget(self._detail_panel)
        sp.setSizes([280, 920])
        sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
        root.addWidget(sp, 1)

        self._status = QLabel("\u5c31\u7eea")
        self._status.setStyleSheet("font-size:14px;color:#6c757d;")
        root.addWidget(self._status)

    def _on_selected(self, config_id):
        self._detail_panel.load(config_id)

    def _refresh(self):
        self._config_list.refresh()
        if self._engine:
            s = self._engine.config.stats()
            self._stats_lbl.setText(
                f"\u603b\u8ba1: {s.get('total',0)}"
                f"  \u5df2\u9501\u5b9a: {s.get('locked',0)}"
                f"  \u7248\u672c\u6570: {s.get('total_versions',0)}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
