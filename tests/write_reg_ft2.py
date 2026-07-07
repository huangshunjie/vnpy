"""write_reg_ft2.py — FeatureList + FeatureDetail"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\registry_tab.py"
)

CODE = """

class FeatureList(QWidget):
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
        for st in FeatureStatus:
            self._combo.addItem(st.value, st)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\\u540d\\u79f0","\\u5206\\u7c7b","IC","\\u72b6\\u6001"])
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
        for ev in (EVENT_RO_FT_CREATED, EVENT_RO_FT_UPDATED, EVENT_RO_FT_DELETED):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()
    def _on_filter(self, _):   self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_features()
        if self._filter:
            items = [f for f in items if f.status == self._filter]
        if self._keyword:
            items = [f for f in items if self._keyword in f.name.lower()
                     or self._keyword in (f.category or "").lower()]
        items.sort(key=lambda f: (f.ic or 0), reverse=True)
        self._table.setRowCount(0)
        for ft in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(ft.name))
            self._table.setItem(r, 1, QTableWidgetItem(ft.category or ""))
            ic_val = round(ft.ic or 0, 4)
            ic_item = QTableWidgetItem(str(ic_val))
            ic_item.setTextAlignment(Qt.AlignCenter)
            col = ("#198754" if ic_val >= 0.04
                   else "#dc3545" if ic_val <= 0 else "#fd7e14")
            ic_item.setForeground(QBrush(QColor(col)))
            self._table.setItem(r, 2, ic_item)
            sc = FT_STATUS_COLOR.get(ft.status, "#6c757d")
            si = QTableWidgetItem(ft.status.value)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 3, si)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, ft.feature_id)

    def _on_click(self, item): self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        fid = item.data(ROLE_ID)
        ft  = self._engine.get_feature(fid)
        if not ft: return
        menu = QMenu(self)
        a_val = menu.addAction("\\u2705  Validated")
        a_dep = menu.addAction("\\u26a0  Deprecated")
        menu.addSeparator()
        a_del = menu.addAction("\\U0001f5d1  \\u5220\\u9664")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        if action == a_val:
            self._engine.set_feature_status(fid, FeatureStatus.VALIDATED); self._refresh()
        elif action == a_dep:
            self._engine.set_feature_status(fid, FeatureStatus.DEPRECATED); self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\\u786e\\u8ba4",
                "\\u5220\\u9664\\u56e0\\u5b50\\u300c" + ft.name + "\\u300d\\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_feature(fid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class FeatureDetail(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id = None
        self._init_ui()

    def _init_ui(self):
        self.setDocumentMode(True)

        ov = QWidget(); ov_l = QVBoxLayout(ov)
        self._title = QLabel("\\u8bf7\\u9009\\u62e9\\u56e0\\u5b50")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        ov_l.addWidget(self._title)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._bar)
        cr = QHBoxLayout()
        self._c_ic   = _make_stat_card("IC",       "\\u2014")
        self._c_rank = _make_stat_card("Rank IC",  "\\u2014")
        self._c_ir   = _make_stat_card("IR",       "\\u2014")
        self._c_icir = _make_stat_card("ICIR",     "\\u2014")
        self._c_cov  = _make_stat_card("Coverage", "\\u2014")
        for c in (self._c_ic, self._c_rank, self._c_ir, self._c_icir, self._c_cov):
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

        ht = QWidget(); ht_l = QVBoxLayout(ht)
        self._ic_chart = MetricChart()
        ht_l.addWidget(self._ic_chart)
        self.addTab(ht, "\\U0001f4c8  IC \\u5386\\u53f2")

        lt = QWidget(); lt_l = QVBoxLayout(lt)
        self._lineage = LineageTreeWidget(engine)
        lt_l.addWidget(self._lineage)
        self.addTab(lt, "\\U0001f9ec  \\u8840\\u7f18")

    def load(self, fid: str):
        self._id = fid
        ft = self._engine.get_feature(fid)
        if not ft: return
        self._title.setText(ft.name)
        sc = FT_STATUS_COLOR.get(ft.status, "#6c757d")
        self._bar.setStyleSheet("background:" + sc + ";border-radius:2px;")
        def _fmt(v): return str(round(v, 4)) if v is not None else "\\u2014"
        self._c_ic._val_lbl.setText(_fmt(ft.ic))
        self._c_rank._val_lbl.setText(_fmt(ft.rank_ic))
        self._c_ir._val_lbl.setText(_fmt(ft.ir))
        self._c_icir._val_lbl.setText(_fmt(ft.icir))
        self._c_cov._val_lbl.setText(_fmt(ft.coverage))
        if ft.ic is not None:
            col = "#198754" if ft.ic >= 0.04 else ("#dc3545" if ft.ic <= 0 else "#fd7e14")
            self._c_ic._val_lbl.setStyleSheet(
                "font-size:18px;font-weight:bold;color:" + col + ";")
        self._info.setRowCount(0)
        for k, v in [
            ("ID", ft.feature_id), ("\\u540d\\u79f0", ft.name),
            ("\\u7248\\u672c", ft.version), ("\\u72b6\\u6001", ft.status.value),
            ("\\u5206\\u7c7b", ft.category or "\\u2014"),
            ("\\u4f5c\\u8005", ft.author or "\\u2014"),
            ("\\u6807\\u7b7e", ", ".join(ft.tags) if ft.tags else "\\u2014"),
            ("Git", ft.git_commit or "\\u2014"),
            ("\\u63cf\\u8ff0", ft.description or "\\u2014"),
            ("\\u521b\\u5efa", ft.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        hist = ft.ic_history or []
        if hist:
            pts = [MetricPoint(key="IC", value=h.get("ic", 0), step=i+1)
                   for i, h in enumerate(hist)]
            self._ic_chart.set_series({"IC": pts}, title="IC \\u5386\\u53f2")
        else:
            self._ic_chart.clear()
        self._lineage.load(fid)

    def clear(self):
        self._id = None
        self._title.setText("\\u8bf7\\u9009\\u62e9\\u56e0\\u5b50")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        for c in (self._c_ic, self._c_rank, self._c_ir, self._c_icir, self._c_cov):
            c._val_lbl.setText("\\u2014")
        self._info.setRowCount(0)
        self._ic_chart.clear()
        self._lineage.clear()
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("FeatureList+Detail OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
