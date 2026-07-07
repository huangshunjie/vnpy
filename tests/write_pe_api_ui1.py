"""write_pe_api_ui1.py — append RouteList + StatPanel + RegisterRouteDialog"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\api.py"
)

CODE = '''

class RegisterRouteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("\\u6ce8\\u518c\\u8def\\u7531")
        self.setMinimumWidth(420)
        root = QVBoxLayout(self)
        grp  = QGroupBox("\\u8def\\u7531\\u4fe1\\u606f")
        form = QFormLayout(grp)
        self._path = QLineEdit(); self._path.setPlaceholderText("/api/v1/xxx")
        form.addRow("\\u8def\\u5f84 *", self._path)
        self._methods = QLineEdit(); self._methods.setText("GET")
        self._methods.setPlaceholderText("GET,POST")
        form.addRow("\\u65b9\\u6cd5", self._methods)
        self._group = QLineEdit()
        form.addRow("\\u5206\\u7ec4", self._group)
        self._desc = QLineEdit()
        form.addRow("\\u63cf\\u8ff0", self._desc)
        self._rate = QLineEdit(); self._rate.setText("0")
        self._rate.setPlaceholderText("0 = \\u65e0\\u9650\\u6d41")
        form.addRow("\\u9650\\u6d41 (\\u6b21/\\u5206)", self._rate)
        root.addWidget(grp)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("\\u6ce8\\u518c")
        btns.button(QDialogButtonBox.Cancel).setText("\\u53d6\\u6d88")
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _ok(self):
        if not self._path.text().strip(): self._path.setFocus(); return
        self.accept()

    def get_path(self)     -> str:       return self._path.text().strip()
    def get_methods(self)  -> list:
        return [m.strip().upper() for m in self._methods.text().split(",") if m.strip()]
    def get_group(self)    -> str:       return self._group.text().strip()
    def get_desc(self)     -> str:       return self._desc.text().strip()
    def get_rate_limit(self) -> int:
        try: return int(self._rate.text())
        except: return 0


def _status_color(code: int) -> str:
    return STATUS_COLOR.get(code // 100, "#8c8c8c")


class StatCard(QFrame):
    def __init__(self, label: str, color: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame{background:#fff;border-radius:8px;border:1px solid #f0f0f0;}")
        self.setFixedHeight(72)
        lay = QVBoxLayout(self); lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(2)
        self._val = QLabel("\\u2014")
        self._val.setStyleSheet(
            f"font-size:22px;font-weight:bold;color:{color};"
            "background:transparent;border:none;")
        lay.addWidget(self._val)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size:11px;color:#8c8c8c;background:transparent;border:none;")
        lay.addWidget(lbl)

    def set_value(self, v): self._val.setText(str(v))


class StatPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        grid = QGridLayout(self); grid.setSpacing(8); grid.setContentsMargins(0,0,0,0)
        self._cards = {}
        defs = [
            ("routes",      "\\u8def\\u7531\\u603b\\u6570",   "#4a6cf7"),
            ("total_calls", "\\u8bf7\\u6c42\\u603b\\u6570",   "#1890ff"),
            ("total_errors","\\u9519\\u8bef\\u603b\\u6570",   "#ff4d4f"),
            ("avg_latency", "\\u5e73\\u5747\\u5ef6\\u8fdf(ms)","#faad14"),
            ("error_rate",  "\\u9519\\u8bef\\u7387",          "#ff4d4f"),
            ("log_entries", "\\u65e5\\u5fd7\\u6761\\u6570",   "#52c41a"),
        ]
        for i, (key, label, color) in enumerate(defs):
            card = StatCard(label, color)
            self._cards[key] = card
            grid.addWidget(card, i // 3, i % 3)

    def refresh(self, stats: dict):
        self._cards["routes"].set_value(stats.get("routes", 0))
        self._cards["total_calls"].set_value(stats.get("total_calls", 0))
        self._cards["total_errors"].set_value(stats.get("total_errors", 0))
        self._cards["avg_latency"].set_value(
            f"{stats.get('avg_latency_ms', 0.0):.1f}")
        self._cards["error_rate"].set_value(
            f"{stats.get('error_rate', 0.0)*100:.2f}%")
        self._cards["log_entries"].set_value(stats.get("log_entries", 0))


class RouteList(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._on_select = None
        root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        tb = QHBoxLayout(); tb.setSpacing(6)
        self._btn_reg = QPushButton("\\u2795 \\u6ce8\\u518c\\u8def\\u7531")
        self._btn_reg.setFixedHeight(26)
        self._btn_reg.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_reg.clicked.connect(self._on_register)
        tb.addWidget(self._btn_reg)
        self._btn_del = QPushButton("\\U0001f5d1 \\u5220\\u9664")
        self._btn_del.setFixedHeight(26)
        self._btn_del.setStyleSheet(
            "background:#ff4d4f;color:#fff;border-radius:4px;border:none;")
        self._btn_del.clicked.connect(self._on_delete)
        tb.addWidget(self._btn_del)
        self._group_combo = QComboBox(); self._group_combo.setFixedHeight(26)
        self._group_combo.addItem("\\u5168\\u90e8\\u5206\\u7ec4", None)
        self._group_combo.currentIndexChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._group_combo, 1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("\\u8fc7\\u6ee4\\u8def\\u5f84...")
        self._search.setFixedHeight(26)
        self._search.textChanged.connect(lambda _: self.refresh())
        tb.addWidget(self._search)
        root.addLayout(tb)
        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels([
            "\\u8def\\u5f84","\\u65b9\\u6cd5","\\u5206\\u7ec4",
            "\\u8c03\\u7528\\u6b21\\u6570","\\u5e73\\u5747\\u5ef6\\u8fdf(ms)","\\u63cf\\u8ff0"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.itemClicked.connect(self._on_click)
        root.addWidget(self._table)

    def set_select_callback(self, cb): self._on_select = cb

    def refresh(self):
        if not self._engine: return
        grp  = self._group_combo.currentData()
        routes = self._engine.api.list_routes(group=grp)
        kw = self._search.text().strip().lower()
        if kw: routes = [r for r in routes if kw in r.path.lower()]
        # rebuild group combo (preserve selection)
        cur_grp = self._group_combo.currentData()
        self._group_combo.blockSignals(True)
        self._group_combo.clear()
        self._group_combo.addItem("\\u5168\\u90e8\\u5206\\u7ec4", None)
        all_groups = sorted({r.group for r in self._engine.api.list_routes() if r.group})
        for g in all_groups: self._group_combo.addItem(g, g)
        idx = self._group_combo.findData(cur_grp)
        if idx >= 0: self._group_combo.setCurrentIndex(idx)
        self._group_combo.blockSignals(False)

        self._table.setRowCount(0)
        for r in routes:
            row = self._table.rowCount(); self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(r.path))
            methods_str = ",".join(r.methods)
            mi = QTableWidgetItem(methods_str)
            color = METHOD_COLOR.get(r.methods[0] if r.methods else "GET", "#8c8c8c")
            mi.setForeground(QBrush(QColor(color)))
            self._table.setItem(row, 1, mi)
            self._table.setItem(row, 2, QTableWidgetItem(r.group or "\\u2014"))
            self._table.setItem(row, 3, QTableWidgetItem(str(r.call_count)))
            self._table.setItem(row, 4,
                QTableWidgetItem(f"{r.avg_latency_ms:.1f}"))
            self._table.setItem(row, 5, QTableWidgetItem(r.description))
            for c in range(6):
                self._table.item(row, c).setData(ROLE_PATH, r.path)

    def _on_click(self, item):
        if self._on_select: self._on_select(item.data(ROLE_PATH))

    def _on_register(self):
        if not self._engine: return
        dlg = RegisterRouteDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self._engine.api.register(
                path=dlg.get_path(),
                handler=lambda req: {"path": req.path, "ok": True},
                methods=dlg.get_methods(),
                group=dlg.get_group(),
                description=dlg.get_desc(),
                rate_limit=dlg.get_rate_limit(),
            )
            self.refresh()

    def _on_delete(self):
        items = self._table.selectedItems()
        if not items or not self._engine: return
        path = items[0].data(ROLE_PATH)
        self._engine.api.unregister(path)
        self.refresh()
        if self._on_select: self._on_select(None)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("Part1 OK, lines:", len(full.splitlines()))
