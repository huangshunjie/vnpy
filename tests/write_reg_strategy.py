"""write_reg_strategy.py — Strategy Dialog + List + Detail"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\ui\registry_tab.py"
)

CODE = """

class StrategyDialog(QDialog):
    def __init__(self, parent=None, record=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self.setWindowTitle(
            "\\u7f16\\u8f91\\u7b56\\u7565" if self._editing else "\\u6ce8\\u518c\\u7b56\\u7565")
        self.setMinimumWidth(480)
        self._init_ui()
        if self._editing: self._load()

    def _init_ui(self):
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u7b56\\u7565\\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._name = QLineEdit()
        form.addRow("\\u540d\\u79f0 *", self._name)
        self._desc = QTextEdit(); self._desc.setFixedHeight(52)
        form.addRow("\\u63cf\\u8ff0", self._desc)
        self._author = QLineEdit()
        form.addRow("\\u4f5c\\u8005", self._author)
        self._tags = QLineEdit(); self._tags.setPlaceholderText("\\u9017\\u53f7\\u5206\\u9694")
        form.addRow("\\u6807\\u7b7e", self._tags)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u786e\\u8ba4")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._on_ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _load(self):
        r = self._record
        self._name.setText(r.name); self._desc.setPlainText(r.description)
        self._author.setText(r.author or "")
        self._tags.setText(", ".join(r.tags))

    def _on_ok(self):
        if not self._name.text().strip(): self._name.setFocus(); return
        self.accept()

    def _split(self, t): return [x.strip() for x in t.split(",") if x.strip()]
    def get_name(self)        -> str:       return self._name.text().strip()
    def get_description(self) -> str:       return self._desc.toPlainText().strip()
    def get_author(self)      -> str:       return self._author.text().strip()
    def get_tags(self)        -> List[str]: return self._split(self._tags.text())


class StrategyList(QWidget):
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
        for st in StrategyStatus:
            self._combo.addItem(st.value, st)
        self._combo.setFixedHeight(26)
        self._combo.currentIndexChanged.connect(self._on_filter)
        fb.addWidget(self._combo, 1)
        root.addLayout(fb)
        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels([
            "\\u540d\\u79f0","Sharpe","\\u5e74\\u5316","\\u72b6\\u6001"])
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
        for ev in (EVENT_RO_ST_CREATED, EVENT_RO_ST_UPDATED, EVENT_RO_ST_DELETED):
            ee.register(ev, lambda _: self._refresh())

    def set_keyword(self, kw): self._keyword = kw.lower(); self._refresh()
    def _on_filter(self, _):   self._filter = self._combo.currentData(); self._refresh()

    def _refresh(self):
        items = self._engine.list_strategies()
        if self._filter:
            items = [s for s in items if s.status == self._filter]
        if self._keyword:
            items = [s for s in items if self._keyword in s.name.lower()]
        items.sort(key=lambda s: (s.sharpe or 0), reverse=True)
        self._table.setRowCount(0)
        for st in items:
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setItem(r, 0, QTableWidgetItem(st.name))
            sh = round(st.sharpe or 0, 2)
            sh_item = QTableWidgetItem(str(sh))
            sh_item.setTextAlignment(Qt.AlignCenter)
            sh_item.setForeground(QBrush(QColor(
                "#198754" if sh >= 1.5 else "#dc3545" if sh <= 0 else "#fd7e14")))
            self._table.setItem(r, 1, sh_item)
            ar = str(round((st.annual_return or 0) * 100, 1)) + "%"
            ar_item = QTableWidgetItem(ar)
            ar_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(r, 2, ar_item)
            sc = ST_STATUS_COLOR.get(st.status, "#6c757d")
            si = QTableWidgetItem(st.status.value)
            si.setForeground(QBrush(QColor(sc)))
            self._table.setItem(r, 3, si)
            for c in range(4):
                self._table.item(r, c).setData(ROLE_ID, st.strategy_id)

    def _on_click(self, item): self.selected.emit(item.data(ROLE_ID))

    def _on_ctx(self, pos):
        item = self._table.itemAt(pos)
        if not item: return
        sid = item.data(ROLE_ID)
        st  = self._engine.get_strategy(sid)
        if not st: return
        menu = QMenu(self)
        sm = menu.addMenu("\\u8bbe\\u7f6e\\u72b6\\u6001")
        a_bt  = sm.addAction("\\u56de\\u6d4b\\u5b8c\\u6210")
        a_val = sm.addAction("\\u5df2\\u9a8c\\u8bc1")
        a_live= sm.addAction("\\u5b9e\\u76d8")
        a_ret = sm.addAction("\\u5df2\\u9000\\u5f03")
        menu.addSeparator()
        a_del = menu.addAction("\\U0001f5d1  \\u5220\\u9664")
        action = menu.exec(self._table.viewport().mapToGlobal(pos))
        status_map = {
            a_bt:  StrategyStatus.BACKTESTED,
            a_val: StrategyStatus.VALIDATED,
            a_live:StrategyStatus.LIVE,
            a_ret: StrategyStatus.RETIRED,
        }
        if action in status_map:
            self._engine.set_strategy_status(sid, status_map[action])
            self._refresh()
        elif action == a_del:
            if QMessageBox.question(
                self, "\\u786e\\u8ba4",
                "\\u5220\\u9664\\u7b56\\u7565\\u300c" + st.name + "\\u300d\\uff1f",
                QMessageBox.Yes | QMessageBox.No
            ) == QMessageBox.Yes:
                self._engine.delete_strategy(sid); self._refresh()

    def selected_id(self):
        items = self._table.selectedItems()
        return items[0].data(ROLE_ID) if items else None


class StrategyDetail(QTabWidget):
    def __init__(self, engine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._id = None
        self._init_ui()

    def _init_ui(self):
        self.setDocumentMode(True)

        ov = QWidget(); ov_l = QVBoxLayout(ov)
        self._title = QLabel("\\u8bf7\\u9009\\u62e9\\u7b56\\u7565")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        ov_l.addWidget(self._title)
        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        ov_l.addWidget(self._bar)
        cr = QHBoxLayout()
        self._c_ar  = _make_stat_card("\\u5e74\\u5316\\u6536\\u76ca", "\\u2014")
        self._c_sh  = _make_stat_card("Sharpe", "\\u2014")
        self._c_dd  = _make_stat_card("MaxDD", "\\u2014")
        self._c_wr  = _make_stat_card("\\u80dc\\u7387", "\\u2014")
        self._c_so  = _make_stat_card("Sortino", "\\u2014")
        for c in (self._c_ar, self._c_sh, self._c_dd, self._c_wr, self._c_so):
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

        vt = QWidget(); vt_l = QVBoxLayout(vt)
        self._ver_table = QTableWidget(0, 3)
        self._ver_table.setHorizontalHeaderLabels(
            ["\\u7248\\u672c","\\u5907\\u6ce8","\\u65f6\\u95f4"])
        self._ver_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._ver_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._ver_table.setAlternatingRowColors(True)
        self._ver_table.verticalHeader().setVisible(False)
        vt_l.addWidget(self._ver_table)
        self.addTab(vt, "\\U0001f4dc  \\u7248\\u672c")

        lt = QWidget(); lt_l = QVBoxLayout(lt)
        self._lineage = LineageTreeWidget(engine)
        lt_l.addWidget(self._lineage)
        self.addTab(lt, "\\U0001f9ec  \\u8840\\u7f18")

    def load(self, sid: str):
        self._id = sid
        st = self._engine.get_strategy(sid)
        if not st: return
        self._title.setText(st.name)
        sc = ST_STATUS_COLOR.get(st.status, "#6c757d")
        self._bar.setStyleSheet("background:" + sc + ";border-radius:2px;")
        def _pct(v): return str(round((v or 0)*100,1))+"%" if v is not None else "\\u2014"
        def _fmt(v): return str(round(v,3)) if v is not None else "\\u2014"
        self._c_ar._val_lbl.setText(_pct(st.annual_return))
        sh = st.sharpe or 0
        self._c_sh._val_lbl.setText(_fmt(st.sharpe))
        self._c_sh._val_lbl.setStyleSheet(
            "font-size:18px;font-weight:bold;color:"
            + ("#198754" if sh >= 1.5 else "#dc3545" if sh <= 0 else "#fd7e14") + ";")
        dd = st.max_drawdown or 0
        self._c_dd._val_lbl.setText(_pct(st.max_drawdown))
        self._c_dd._val_lbl.setStyleSheet(
            "font-size:18px;font-weight:bold;color:"
            + ("#dc3545" if dd <= -0.2 else "#198754" if dd >= -0.1 else "#fd7e14") + ";")
        self._c_wr._val_lbl.setText(_pct(st.win_rate))
        self._c_so._val_lbl.setText(_fmt(st.sortino))
        self._info.setRowCount(0)
        for k, v in [
            ("ID", st.strategy_id), ("\\u540d\\u79f0", st.name),
            ("\\u7248\\u672c", st.version), ("\\u72b6\\u6001", st.status.value),
            ("\\u4f5c\\u8005", st.author or "\\u2014"),
            ("\\u6807\\u7b7e", ", ".join(st.tags) if st.tags else "\\u2014"),
            ("Git", st.git_commit or "\\u2014"),
            ("\\u56e0\\u5b50\\u6570", len(st.feature_ids)),
            ("\\u6a21\\u578b\\u6570", len(st.model_ids)),
            ("\\u521b\\u5efa", st.created_at.strftime("%Y-%m-%d %H:%M")),
        ]:
            r = self._info.rowCount(); self._info.insertRow(r)
            ki = QTableWidgetItem(k); ki.setForeground(QBrush(QColor("#6c757d")))
            self._info.setItem(r, 0, ki)
            self._info.setItem(r, 1, QTableWidgetItem(str(v)))
        self._ver_table.setRowCount(0)
        for ver in (st.versions or []):
            r = self._ver_table.rowCount(); self._ver_table.insertRow(r)
            self._ver_table.setItem(r, 0, QTableWidgetItem(ver.get("version","?")))
            self._ver_table.setItem(r, 1, QTableWidgetItem(ver.get("note","") or ""))
            ts = ver.get("created_at","")
            if hasattr(ts, "strftime"): ts = ts.strftime("%Y-%m-%d %H:%M")
            self._ver_table.setItem(r, 2, QTableWidgetItem(str(ts)))
        self._lineage.load(sid)

    def clear(self):
        self._id = None
        self._title.setText("\\u8bf7\\u9009\\u62e9\\u7b56\\u7565")
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        for c in (self._c_ar, self._c_sh, self._c_dd, self._c_wr, self._c_so):
            c._val_lbl.setText("\\u2014")
        self._info.setRowCount(0)
        self._ver_table.setRowCount(0)
        self._lineage.clear()
"""

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("Strategy subsystem OK, lines:", len(full.splitlines()), "size:", P.stat().st_size)
