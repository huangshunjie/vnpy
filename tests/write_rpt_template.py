"""write_rpt_template.py — TemplatePanel"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\report_tab.py"
)

CODE = """

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
        self._btn_new = QPushButton("+ \\u65b0\\u5efa\\u6a21\\u677f")
        self._btn_apply = QPushButton("\\u2b07 \\u5e94\\u7528\\u5230\\u62a5\\u544a")
        self._btn_del = QPushButton("\\U0001f5d1 \\u5220\\u9664")
        for b in (self._btn_new, self._btn_apply, self._btn_del):
            b.setFixedHeight(26); tb.addWidget(b)
        tb.addStretch(); root.addLayout(tb)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(
            ["\\u540d\\u79f0","\\u9002\\u7528\\u7c7b\\u578b","\\u63cf\\u8ff0"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setFixedHeight(160)
        root.addWidget(self._table)

        prev_grp = QGroupBox("\\u6a21\\u677f\\u5185\\u5bb9\\u9884\\u89c8")
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
                self, "\\u63d0\\u793a",
                "\\u8bf7\\u5148\\u9009\\u62e9\\u4e00\\u4e2a\\u6a21\\u677f")
            return
        self.apply_requested.emit(tid)

    def _on_del(self):
        tid = self._selected_id()
        if not tid: return
        tmpl = self._engine.get_template(tid)
        if not tmpl: return
        if QMessageBox.question(
            self, "\\u786e\\u8ba4",
            "\\u5220\\u9664\\u6a21\\u677f\\u300c" + tmpl.name + "\\u300d\\uff1f",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            # no delete_template in engine — just remove from list via update
            QMessageBox.information(
                self, "\\u63d0\\u793a",
                "\\u5f53\\u524d\\u5f15\\u64ce\\u4e0d\\u652f\\u6301\\u5220\\u9664\\u6a21\\u677f\\uff0c\\u8bf7\\u624b\\u52a8\\u6e05\\u7406")
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("TemplatePanel OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
