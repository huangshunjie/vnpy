"""write_pe_config_ui1.py — append JsonHighlighter + dialogs + ConfigList"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\config.py"
)

CODE = '''

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
        for m in re.finditer(r'"([^"\\\\]|\\\\.)*"\\s*:', text):
            self.setFormat(m.start(), m.end()-m.start(), self._fmt_key)
        for m in re.finditer(r':\\s*"([^"\\\\]|\\\\.)*"', text):
            self.setFormat(m.start()+1, m.end()-m.start()-1, self._fmt_str)
        for m in re.finditer(r'(?<![":])\\b-?\\d+\\.?\\d*\\b', text):
            self.setFormat(m.start(), m.end()-m.start(), self._fmt_num)
        for m in re.finditer(r'\\b(true|false)\\b', text):
            self.setFormat(m.start(), m.end()-m.start(), self._fmt_bool)
        for m in re.finditer(r'\\bnull\\b', text):
            self.setFormat(m.start(), m.end()-m.start(), self._fmt_null)


class CreateConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\\u521b\\u5efa\\u914d\\u7f6e\\u9879")
        self.setMinimumWidth(480)
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u57fa\\u672c\\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit(); self._name.setPlaceholderText("\\u914d\\u7f6e\\u540d\\u79f0")
        form.addRow("\\u540d\\u79f0 *", self._name)
        self._type = QComboBox()
        for t in ConfigType: self._type.addItem(t.value, t)
        form.addRow("\\u7c7b\\u578b", self._type)
        self._owner = QLineEdit()
        form.addRow("\\u8d23\\u4efb\\u4eba", self._owner)
        self._desc = QLineEdit()
        form.addRow("\\u63cf\\u8ff0", self._desc)
        self._tags = QLineEdit(); self._tags.setPlaceholderText("tag1,tag2")
        form.addRow("\\u6807\\u7b7e", self._tags)
        root.addWidget(grp)
        dg = QGroupBox("\\u521d\\u59cb\\u6570\\u636e (JSON)")
        dl = QVBoxLayout(dg)
        self._data_edit = QPlainTextEdit()
        self._data_edit.setPlaceholderText(\'{\\"key\\": \\"value\\"}\')
        self._data_edit.setFixedHeight(120)
        f = QFont("Consolas", 10); self._data_edit.setFont(f)
        _JsonHighlighter(self._data_edit.document())
        dl.addWidget(self._data_edit)
        root.addWidget(dg)
        ng = QGroupBox("\\u5907\\u6ce8")
        nl = QVBoxLayout(ng)
        self._note = QLineEdit()
        nl.addWidget(self._note)
        root.addWidget(ng)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u521b\\u5efa")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._name.text().strip(): self._name.setFocus(); return
        try:
            import json; json.loads(self._data_edit.toPlainText() or "{}")
        except Exception as e:
            QMessageBox.warning(self, "JSON \\u9519\\u8bef", str(e)); return
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
        self._btn_new = QPushButton("\\u2795 \\u65b0\\u5efa")
        self._btn_new.setFixedHeight(26)
        self._btn_new.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_new.clicked.connect(self._on_new)
        tb.addWidget(self._btn_new)
        self._type_combo = QComboBox(); self._type_combo.setFixedHeight(26)
        self._type_combo.addItem("\\u5168\\u90e8\\u7c7b\\u578b", None)
        for t in ConfigType: self._type_combo.addItem(t.value, t)
        self._type_combo.currentIndexChanged.connect(self._on_filter)
        tb.addWidget(self._type_combo, 1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("\\u641c\\u7d22...")
        self._search.setFixedHeight(26)
        self._search.textChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._search)
        root.addLayout(tb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\\u540d\\u79f0","\\u7c7b\\u578b","\\u8d23\\u4efb\\u4eba","\\u66f4\\u65b0\\u65f6\\u95f4"])
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
            lbl = c.name + (" \\U0001f512" if c.is_locked else "")
            self._table.setItem(r, 0, QTableWidgetItem(lbl))
            color = TYPE_COLOR.get(c.config_type, "#8c8c8c")
            ti = QTableWidgetItem(c.config_type.value)
            ti.setForeground(QBrush(QColor(color)))
            self._table.setItem(r, 1, ti)
            self._table.setItem(r, 2, QTableWidgetItem(c.owner or "\\u2014"))
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
            "\\U0001f513  \\u89e3\\u9501" if rec.is_locked else "\\U0001f512  \\u9501\\u5b9a")
        a_del  = menu.addAction("\\U0001f5d1  \\u5220\\u9664")
        act = menu.exec(self._table.viewport().mapToGlobal(pos))
        try:
            if act == a_lock:
                self._engine.config.unlock(cid) if rec.is_locked \
                    else self._engine.config.lock(cid)
            elif act == a_del:
                self._engine.config.delete_config(cid)
        except (ValueError, KeyError) as e:
            QMessageBox.warning(self, "\\u9519\\u8bef", str(e))
        self.refresh()
        if self._on_select and act == a_del: self._on_select(None)
        elif self._on_select: self._on_select(cid)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("Part1 OK, lines:", len(full.splitlines()))
