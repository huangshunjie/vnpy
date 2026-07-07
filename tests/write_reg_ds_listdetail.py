"""write_reg_ds_listdetail.py — DatasetList + DatasetDetail"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\registry_tab.py"
)

CODE = """

class DatasetList(QWidget):
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
        for st in DatasetStatus:
            self._combo.addItem(st.value, st)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\\u540d\\u79f0","\\u7248\\u672c","\\u72b6\\u6001","\\u884c\\u6570"])
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
        for ev in (EVENT_RO_DS_CREATED, EVENT_RO_DS_UPDATED, EVENT_RO_DS_DELETED):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()
    def _on_filter(self, _):   self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_datasets()
        if self._filter:
            items = [d for d in items if d.status == self._filter]
        if self._keyword:
            items = [d for d in items if self._keyword in d.name.lower()]
        self._table.setRowCount(0)
        for ds in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(ds.name))
            self._table.setItem(r, 1, QTableWidgetItem(ds.version))
            sc   = DS_STATUS_COLOR.get(ds.status, "#6c757d")
            si   = QTableWidgetItem(ds.status.value)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 2, si)
            ri = QTableWidgetItem(str(ds.row_count or 0))
            ri.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(r, 3, ri)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, ds.dataset_id)

    def _on_click(self, item):
        self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        did = item.data(ROLE_ID)
        ds  = self._engine.get_dataset(did)
        if not ds: return
        menu = QMenu(self)
        a_ready = menu.addAction("\\u2705  \\u6807\\u4e3a Ready")
        a_dep   = menu.addAction("\\u26a0  \\u6807\\u4e3a Deprecated")
        menu.addSeparator()
        a_del   = menu.addAction("\\U0001f5d1  \\u5220\\u9664")
        action  = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_ready:
            self._engine.set_dataset_ready(did); self._refresh()
        elif action == a_dep:
            ds.status = DatasetStatus.DEPRECATED
            self._engine.update_dataset(ds); self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\\u786e\\u8ba4",
                "\\u5220\\u9664\\u6570\\u636e\\u96c6\\u300c" + ds.name + "\\u300d\\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_dataset(did); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class DatasetDetail(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id = None
        self._init_ui()

    def _init_ui(self):
        self.setDocumentMode(True)

        # Tab1: overview
        ov = QWidget(); ov_l = QVBoxLayout(ov)
        self._title = QLabel("\\u8bf7\\u9009\\u62e9\\u6570\\u636e\\u96c6")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        ov_l.addWidget(self._title)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._bar)
        cr = QHBoxLayout()
        self._c_rows = _make_stat_card("\\u884c\\u6570", "0")
        self._c_size = _make_stat_card("\\u5927\\u5c0f(MB)", "0")
        self._c_qual = _make_stat_card("\\u8d28\\u91cf\\u5206", "0")
        self._c_ver  = _make_stat_card("\\u7248\\u672c\\u6570", "0")
        for c in (self._c_rows, self._c_size, self._c_qual, self._c_ver):
            cr.addWidget(c)
        ov_l.addLayout(cr)
        self._info = QTableWidget(0, 2)
        self._info.setHorizontalHeaderLabels(["\\u5c5e\\u6027","\\u503c"])
        self._info.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._info.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._info.setAlternatingRowColors(True)
        self._info.verticalHeader().setVisible(False)
        ov_l.addWidget(self._info)
        self.addTab(ov, "\\U0001f4cb  \\u6982\\u89c8")

        # Tab2: versions
        vt = QWidget(); vt_l = QVBoxLayout(vt)
        self._ver_table = QTableWidget(0, 3)
        self._ver_table.setHorizontalHeaderLabels(
            ["\\u7248\\u672c","\\u884c\\u6570","\\u65f6\\u95f4"])
        self._ver_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._ver_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ver_table.setAlternatingRowColors(True)
        self._ver_table.verticalHeader().setVisible(False)
        vt_l.addWidget(self._ver_table)
        self.addTab(vt, "\\U0001f4dc  \\u7248\\u672c")

        # Tab3: lineage
        lt = QWidget(); lt_l = QVBoxLayout(lt)
        self._lineage = LineageTreeWidget(engine)
        lt_l.addWidget(self._lineage)
        self.addTab(lt, "\\U0001f9ec  \\u8840\\u7f18")

    def load(self, did: str):
        self._id = did
        ds = self._engine.get_dataset(did)
        if not ds: return
        self._title.setText(ds.name)
        sc = DS_STATUS_COLOR.get(ds.status, "#6c757d")
        self._bar.setStyleSheet("background:" + sc + ";border-radius:2px;")
        self._c_rows._val_lbl.setText(str(ds.row_count or 0))
        self._c_size._val_lbl.setText(str(ds.size_mb or 0))
        self._c_qual._val_lbl.setText(str(round(ds.quality_score or 0, 2)))
        self._c_ver._val_lbl.setText(str(len(ds.versions or [])))
        self._info.setRowCount(0)
        for k, v in [
            ("ID", ds.dataset_id), ("\\u540d\\u79f0", ds.name),
            ("\\u7248\\u672c", ds.version), ("\\u72b6\\u6001", ds.status.value),
            ("\\u6570\\u636e\\u6e90", ds.source or "\\u2014"),
            ("\\u5f00\\u59cb", ds.start_date or "\\u2014"),
            ("\\u7ed3\\u675f", ds.end_date or "\\u2014"),
            ("\\u6807\\u7b7e", ", ".join(ds.tags) if ds.tags else "\\u2014"),
            ("\\u63cf\\u8ff0", ds.description or "\\u2014"),
            ("\\u521b\\u5efa", ds.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        self._ver_table.setRowCount(0)
        for ver in (ds.versions or []):
            r = self._ver_table.rowCount(); self._ver_table.insertRow(r)
            self._ver_table.setItem(r, 0, QTableWidgetItem(ver.get("version","?")))
            self._ver_table.setItem(r, 1, QTableWidgetItem(str(ver.get("row_count",0))))
            ts = ver.get("created_at","")
            if hasattr(ts, "strftime"): ts = ts.strftime("%Y-%m-%d %H:%M")
            self._ver_table.setItem(r, 2, QTableWidgetItem(str(ts)))
        self._lineage.load(did)

    def clear(self):
        self._id = None
        self._title.setText("\\u8bf7\\u9009\\u62e9\\u6570\\u636e\\u96c6")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        for c in (self._c_rows, self._c_size, self._c_qual, self._c_ver):
            c._val_lbl.setText("0")
        self._info.setRowCount(0)
        self._ver_table.setRowCount(0)
        self._lineage.clear()
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("DatasetList+Detail OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
