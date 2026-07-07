"""write_pl_list.py — PipelineList"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\pipeline_tab.py"
)

CODE = """

class PipelineList(QWidget):
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
        for st in PipelineStatus:
            self._combo.addItem(st.value, st)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\\u540d\\u79f0", "\\u72b6\\u6001", "\\u8282\\u70b9", "\\u8fd0\\u884c\\u6b21\\u6570"])
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
        for ev in (EVENT_RO_PL_CREATED, EVENT_RO_PL_UPDATED,
                   EVENT_RO_PL_DELETED, EVENT_RO_PL_STARTED,
                   EVENT_RO_PL_COMPLETED, EVENT_RO_PL_FAILED,
                   EVENT_RO_PL_PAUSED,   EVENT_RO_PL_RESET):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()
    def _on_filter(self, _):   self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_pipelines()
        if self._filter:
            items = [p for p in items if p.status == self._filter]
        if self._keyword:
            items = [p for p in items if self._keyword in p.name.lower()
                     or any(self._keyword in t for t in p.tags)]
        self._table.setRowCount(0)
        for pl in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(pl.name))
            sc  = PL_STATUS_COLOR.get(pl.status, "#6c757d")
            si  = QTableWidgetItem(pl.status.value)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 1, si)
            ni  = QTableWidgetItem(str(len(pl.nodes)))
            ni.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(r, 2, ni)
            ri  = QTableWidgetItem(str(pl.run_count))
            ri.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(r, 3, ri)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, pl.pipeline_id)

    def _on_click(self, item):
        self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        pid = item.data(ROLE_ID)
        pl  = self._engine.get_pipeline(pid)
        if not pl: return
        menu = QMenu(self)
        a_start  = menu.addAction("\\u25b6  \\u8fd0\\u884c")
        a_pause  = menu.addAction("\\u23f8  \\u6682\\u505c")
        a_reset  = menu.addAction("\\U0001f504  \\u91cd\\u7f6e")
        menu.addSeparator()
        a_del    = menu.addAction("\\U0001f5d1  \\u5220\\u9664")
        action   = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_start:
            self._engine.start_pipeline(pid); self._refresh()
        elif action == a_pause:
            self._engine.pause_pipeline(pid); self._refresh()
        elif action == a_reset:
            self._engine.reset_pipeline(pid); self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\\u786e\\u8ba4",
                "\\u5220\\u9664 Pipeline \\u300c" + pl.name + "\\u300d\\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_pipeline(pid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("PipelineList OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
