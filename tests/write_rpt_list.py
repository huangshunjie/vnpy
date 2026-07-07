"""write_rpt_list.py — ReportList"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\report_tab.py"
)

CODE = """

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
        self._combo.addItem("\\u5168\\u90e8", None)
        for rt in ReportType:
            icon = RPT_TYPE_ICON.get(rt, "")
            self._combo.addItem(icon + " " + rt.value, rt)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels([
            "\\u6807\\u9898", "\\u7c7b\\u578b", "\\u72b6\\u6001"])
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
                si = QTableWidgetItem("\\u2705 \\u5df2\\u53d1\\u5e03")
                si.setForeground(QBrush(QColor("#198754")))
            else:
                si = QTableWidgetItem("\\u270f \\u8349\\u7a3f")
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
            a_pub = menu.addAction("\\u274c  \\u53d6\\u6d88\\u53d1\\u5e03")
        else:
            a_pub = menu.addAction("\\U0001f4e4  \\u53d1\\u5e03")
        menu.addSeparator()
        a_del = menu.addAction("\\U0001f5d1  \\u5220\\u9664")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_pub:
            if rpt.is_published:
                self._engine.unpublish_report(rid)
            else:
                self._engine.publish_report(rid)
            self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\\u786e\\u8ba4",
                "\\u5220\\u9664\\u62a5\\u544a\\u300c" + rpt.title + "\\u300d\\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_report(rid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("ReportList OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
