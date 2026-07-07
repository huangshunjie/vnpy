"""write_pe_health_ui2.py — append DetailPanel + StrategyHealthTab"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\ui\strategy_health.py"
)

CODE = '''

class DetailPanel(QWidget):
    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._sid    = None
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8,0,0,0); root.setSpacing(8)

        # title row
        hdr = QHBoxLayout()
        self._title = QLabel("\\u8bf7\\u9009\\u62e9\\u7b56\\u7565")
        self._title.setStyleSheet("font-size:15px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(self._title); hdr.addStretch()
        self._status_badge = QLabel("")
        self._status_badge.setStyleSheet(
            "font-size:12px;padding:2px 10px;border-radius:10px;")
        hdr.addWidget(self._status_badge)
        root.addLayout(hdr)

        self._bar = QFrame(); self._bar.setFixedHeight(4)
        self._bar.setStyleSheet("background:#dee2e6;border-radius:2px;")
        root.addWidget(self._bar)

        # update snapshot button
        tb = QHBoxLayout()
        self._btn_update = QPushButton("\\U0001f4ca  \\u66f4\\u65b0\\u6307\\u6807\\u5feb\\u7167")
        self._btn_update.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;border:none;")
        self._btn_update.setFixedHeight(28)
        self._btn_update.clicked.connect(self._on_update_snapshot)
        tb.addWidget(self._btn_update); tb.addStretch()
        self._score_lbl = QLabel("\\u603b\\u5206: \\u2014")
        self._score_lbl.setStyleSheet("font-size:18px;font-weight:bold;color:#4a6cf7;")
        tb.addWidget(self._score_lbl)
        root.addLayout(tb)

        # four dim rings
        self._dim_panel = DimScorePanel()
        root.addWidget(self._dim_panel)

        # metric table
        mg = QGroupBox("\\u6307\\u6807\\u5feb\\u7167")
        ml = QVBoxLayout(mg)
        self._metric_table = QTableWidget(0, 2)
        self._metric_table.setHorizontalHeaderLabels(["\\u6307\\u6807","\\u5f53\\u524d\\u5024"])
        self._metric_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._metric_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._metric_table.setAlternatingRowColors(True)
        self._metric_table.verticalHeader().setVisible(False)
        self._metric_table.setFixedHeight(220)
        ml.addWidget(self._metric_table)
        root.addWidget(mg)

        # warnings
        wg = QGroupBox("\\u544a\\u8b66\\u4e0e\\u5efa\\u8bae")
        wl = QVBoxLayout(wg)
        self._warn_scroll = QScrollArea()
        self._warn_scroll.setWidgetResizable(True)
        self._warn_scroll.setFrameShape(QFrame.NoFrame)
        self._warn_scroll.setFixedHeight(120)
        self._warn_container = QWidget()
        self._warn_layout    = QVBoxLayout(self._warn_container)
        self._warn_layout.setAlignment(Qt.AlignTop)
        self._warn_scroll.setWidget(self._warn_container)
        wl.addWidget(self._warn_scroll)
        root.addWidget(wg, 1)

    def load(self, strategy_id: str):
        self._sid = strategy_id
        rec = self._engine.health.get_health(strategy_id)
        if rec: self._render(rec)

    def _render(self, rec: StrategyHealthRecord):
        color = STATUS_COLOR.get(rec.status, "#8c8c8c")
        icon  = STATUS_ICON.get(rec.status, "")
        self._title.setText(rec.strategy_name)
        self._bar.setStyleSheet(f"background:{color};border-radius:2px;")
        self._status_badge.setText(icon+" "+rec.status.value.upper())
        self._status_badge.setStyleSheet(
            f"font-size:12px;padding:2px 10px;border-radius:10px;"
            f"background:{color}22;color:{color};border:1px solid {color}44;")
        self._score_lbl.setText(f"\\u603b\\u5206: {rec.score:.1f}")
        self._score_lbl.setStyleSheet(
            f"font-size:18px;font-weight:bold;color:{color};")
        self._dim_panel.update_scores(rec)

        # metric table
        self._metric_table.setRowCount(0)
        snap = rec.snapshot
        rows = []
        if snap:
            rows = [
                ("Sharpe Ratio",        snap.sharpe,         ""),
                ("\\u6700\\u5927\\u56de\\u64a4",   snap.max_drawdown,   "%",  100),
                ("\\u80dc\\u7387",              snap.win_rate,       "%",  100),
                ("IC \\u5747\\u5024",          snap.ic_mean,        ""),
                ("Alpha \\u8870\\u51cf",        snap.alpha_decay,    "%",  100),
                ("\\u98ce\\u9669\\u655e\\u53e3",        snap.risk_exposure,  "%",  100),
                ("\\u8ba2\\u5355\\u5ef6\\u8fdf (ms)",   snap.order_delay_ms, "ms"),
                ("\\u6210\\u4ea4\\u7387",          snap.fill_rate,      "%",  100),
                ("\\u6ed1\\u70b9 (bps)",        snap.slippage_bps,   "bps"),
            ]
        for row in rows:
            name   = row[0]
            val    = row[1]
            unit   = row[2]
            mult   = row[3] if len(row) > 3 else 1
            r = self._metric_table.rowCount()
            self._metric_table.insertRow(r)
            ki = QTableWidgetItem(name)
            ki.setForeground(QBrush(QColor("#8c8c8c")))
            self._metric_table.setItem(r, 0, ki)
            if val is None:
                self._metric_table.setItem(r, 1, QTableWidgetItem("\\u2014"))
            else:
                display = f"{val*mult:.2f}{unit}"
                self._metric_table.setItem(r, 1, QTableWidgetItem(display))

        # warnings
        while self._warn_layout.count():
            item = self._warn_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        if not rec.warnings:
            ok = QLabel("\\u2705  \\u65e0\\u544a\\u8b66\\uff0c\\u7b56\\u7565\\u8fd0\\u884c\\u6b63\\u5e38")
            ok.setStyleSheet("color:#52c41a;font-size:12px;padding:4px;")
            self._warn_layout.addWidget(ok)
        else:
            for w in rec.warnings:
                lbl = QLabel("\\u26a0\\ufe0f  " + w)
                lbl.setStyleSheet(
                    "color:#faad14;font-size:12px;padding:2px 4px;"
                    "background:#fffbe6;border-radius:4px;margin-bottom:2px;")
                lbl.setWordWrap(True)
                self._warn_layout.addWidget(lbl)

    def _on_update_snapshot(self):
        if not self._sid: return
        dlg = UpdateSnapshotDialog(self)
        if dlg.exec() == QDialog.Accepted:
            snap = dlg.get_snapshot()
            self._engine.health.update_snapshot(self._sid, snap)
            self.load(self._sid)


class StrategyHealthTab(QWidget):
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
        root.setContentsMargins(12,12,12,12); root.setSpacing(8)

        hdr = QHBoxLayout()
        title = QLabel("\\U0001f493  Strategy Health Monitor")
        title.setStyleSheet("font-size:16px;font-weight:bold;color:#1a1f36;")
        hdr.addWidget(title); hdr.addStretch()
        self._stats_lbl = QLabel("")
        self._stats_lbl.setStyleSheet("font-size:11px;color:#8c8c8c;")
        hdr.addWidget(self._stats_lbl)
        btn = QPushButton("\\U0001f504 \\u5237\\u65b0")
        btn.setFixedSize(68, 26)
        btn.setStyleSheet(
            "background:#4a6cf7;color:#fff;border-radius:4px;"
            "font-size:12px;border:none;")
        btn.clicked.connect(self._refresh)
        hdr.addWidget(btn)
        root.addLayout(hdr)

        sp = QSplitter(Qt.Horizontal)
        self._health_list  = HealthList(self._engine)
        self._detail_panel = DetailPanel(self._engine)
        self._health_list.set_select_callback(self._on_selected)
        sp.addWidget(self._health_list)
        sp.addWidget(self._detail_panel)
        sp.setSizes([300, 900])
        sp.setStretchFactor(0, 0); sp.setStretchFactor(1, 1)
        root.addWidget(sp, 1)

        self._status_bar = QLabel("\\u5c31\\u7eea")
        self._status_bar.setStyleSheet("font-size:11px;color:#6c757d;")
        root.addWidget(self._status_bar)

    def _on_selected(self, sid: str):
        self._detail_panel.load(sid)

    def _refresh(self):
        self._health_list.refresh()
        if self._engine:
            s = self._engine.health.stats()
            self._stats_lbl.setText(
                f"\\u603b\\u8ba1: {s.get('total',0)}"
                f"  \\u5065\\u5eb7: {s.get('healthy',0)}"
                f"  \\u544a\\u8b66: {s.get('warning',0)}"
                f"  \\u4e25\\u91cd: {s.get('critical',0)}"
                f"  \\u9000\\u5f39: {s.get('retire',0)}"
                f"  \\u5747\\u5206: {s.get('avg_score',0.0):.1f}")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
'''

ast.parse(CODE)
with open(P, "a", encoding="utf-8") as f:
    f.write(CODE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("StrategyHealthTab OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
