"""
data_intelligence_ai/ui/feature_tab.py  (Phase 2)

FeatureTab — Feature Store 可视化面板。
左栏：写入控制 | 右侧：状态KPI + 特征流 + 特征表
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import FeatureType

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _BLUE = "#89b4fa"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"
_RED = "#f38ba8"; _MAV = "#cba6f7"; _HEAD = "#313244"; _CYN = "#89dceb"
_TEA = "#94e2d5"
_IS = ("QDoubleSpinBox,QSpinBox,QComboBox,QLineEdit{background:#313244;color:#cdd6f4;"
       "border:1px solid #45475a;border-radius:3px;padding:3px 6px;font-size:11px;}"
       "QComboBox::drop-down{border:none;}")
_LLBL = "color:#6c7086;font-size:11px;border:none;background:transparent;"
_TBL  = ("QTableWidget{background:#181825;color:#cdd6f4;border:1px solid #45475a;"
         "gridline-color:#45475a;font-size:11px;}"
         "QTableWidget::item{padding:3px 6px;}"
         "QTableWidget::item:alternate{background:#1e1e2e;}"
         "QTableWidget::item:selected{background:#45475a;}"
         "QHeaderView::section{background:#313244;color:#6c7086;border:none;"
         "border-bottom:1px solid #45475a;padding:4px 6px;font-size:10px;}")
_TYPE_COLOR = {
    FeatureType.PRICE:      _BLUE,
    FeatureType.VOLUME:     _GRN,
    FeatureType.VOLATILITY: _YLW,
    FeatureType.ALPHA:      _MAV,
    FeatureType.REGIME:     _CYN,
    FeatureType.EXECUTION:  _TEA,
}


def _lbl(t, s=""):
    w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w


def _sep():
    s = QtWidgets.QFrame()
    s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    s.setStyleSheet("border:none;border-top:1px solid #45475a;background:transparent;")
    return s


class FeatureTab(QtWidgets.QWidget):
    """Feature Store 可视化面板（Phase 2）。"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine):
        self._engine = engine

    def _init_ui(self):
        self.setStyleSheet(f"background:{_BG};color:{_FG};")
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(10, 10, 10, 10); h.setSpacing(10)
        h.addWidget(self._build_left(), stretch=0)
        h.addWidget(self._build_right(), stretch=1)

    # ── left panel ────────────────────────────────────────────────────
    def _build_left(self):
        panel = QtWidgets.QWidget(); panel.setFixedWidth(230)
        panel.setStyleSheet(
            f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(12, 14, 12, 14); vb.setSpacing(10)
        vb.addWidget(_lbl("Feature Store 写入",
                          f"color:{_GRN};font-weight:bold;font-size:12px;border:none;"))
        vb.addWidget(_sep())

        fm = QtWidgets.QFormLayout()
        fm.setContentsMargins(0, 0, 0, 0); fm.setVerticalSpacing(8)
        fm.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self._type_combo = QtWidgets.QComboBox()
        for ft in FeatureType:
            self._type_combo.addItem(ft.value.title(), ft)
        self._type_combo.setStyleSheet(_IS)
        fm.addRow(_lbl("特征类型:", _LLBL), self._type_combo)

        self._name_ed = QtWidgets.QLineEdit("close_ret")
        self._name_ed.setStyleSheet(_IS)
        fm.addRow(_lbl("特征名:", _LLBL), self._name_ed)

        self._symbol_ed = QtWidgets.QLineEdit("BTCUSDT")
        self._symbol_ed.setStyleSheet(_IS)
        fm.addRow(_lbl("标的:", _LLBL), self._symbol_ed)

        self._value_sp = QtWidgets.QDoubleSpinBox()
        self._value_sp.setRange(-1e6, 1e6)
        self._value_sp.setValue(0.012); self._value_sp.setDecimals(6)
        self._value_sp.setStyleSheet(_IS)
        fm.addRow(_lbl("特征值:", _LLBL), self._value_sp)

        self._ver_sp = QtWidgets.QSpinBox()
        self._ver_sp.setRange(1, 999); self._ver_sp.setValue(1)
        self._ver_sp.setStyleSheet(_IS)
        fm.addRow(_lbl("版本:", _LLBL), self._ver_sp)

        vb.addLayout(fm); vb.addWidget(_sep())

        vb.addWidget(_lbl("行情批量注入",
                          f"color:{_MUT};font-size:10px;border:none;"))
        fm2 = QtWidgets.QFormLayout()
        fm2.setContentsMargins(0, 0, 0, 0); fm2.setVerticalSpacing(6)
        fm2.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._mkt_symbol = QtWidgets.QLineEdit("ETHUSDT")
        self._mkt_symbol.setStyleSheet(_IS)
        fm2.addRow(_lbl("标的:", _LLBL), self._mkt_symbol)
        self._mkt_bars = QtWidgets.QSpinBox()
        self._mkt_bars.setRange(5, 100); self._mkt_bars.setValue(20)
        self._mkt_bars.setStyleSheet(_IS)
        fm2.addRow(_lbl("K线数:", _LLBL), self._mkt_bars)
        vb.addLayout(fm2); vb.addStretch()

        btn = QtWidgets.QPushButton(">> 写入特征")
        btn.setStyleSheet(
            f"QPushButton{{background:{_GRN};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:8px;font-size:12px;}}"
            f"QPushButton:hover{{background:#94e2a1;}}")
        btn.clicked.connect(self._on_write); vb.addWidget(btn)

        btn2 = QtWidgets.QPushButton("模拟行情注入")
        btn2.setStyleSheet(
            f"QPushButton{{background:transparent;color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:4px;"
            f"padding:6px;font-size:11px;}}"
            f"QPushButton:hover{{background:{_HEAD};}}")
        btn2.clicked.connect(self._on_simulate_market); vb.addWidget(btn2)
        return panel

    # ── right panel ───────────────────────────────────────────────────
    def _build_right(self):
        panel = QtWidgets.QWidget(); panel.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(8)
        vb.addWidget(self._build_kpi_bar())
        vb.addWidget(self._build_stream())
        vb.addWidget(self._build_table())
        return panel

    def _build_kpi_bar(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(16, 10, 16, 10); h.setSpacing(18)
        self._kpi: dict = {}
        for key, txt, color in [
            ("total",     "Total Features", _FG),
            ("active",    "Active",         _GRN),
            ("versions",  "Total Versions", _BLUE),
            ("overwrites","Overwrites",     _YLW),
            ("rate",      "Write Rate/min", _TEA),
            ("symbols",   "Symbols",        _MAV),
        ]:
            cell = QtWidgets.QWidget()
            cell.setStyleSheet("background:transparent;border:none;")
            cv = QtWidgets.QVBoxLayout(cell)
            cv.setContentsMargins(0, 0, 0, 0); cv.setSpacing(2)
            lk = QtWidgets.QLabel(txt)
            lk.setStyleSheet(
                f"color:{_MUT};font-size:9px;border:none;background:transparent;")
            lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel("--")
            lv.setStyleSheet(
                f"color:{color};font-size:13px;font-weight:bold;"
                f"border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv)
            self._kpi[key] = lv; h.addWidget(cell)
        h.addStretch(); return w

    def _build_stream(self):
        grp = QtWidgets.QGroupBox("Feature Write Stream")
        grp.setStyleSheet(
            f"QGroupBox{{color:{_GRN};border:1px solid {_BORDER};"
            f"border-radius:4px;margin-top:8px;font-size:11px;background:{_DARK};}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}")
        vb = QtWidgets.QVBoxLayout(grp); vb.setContentsMargins(10, 14, 10, 10)
        self._stream = QtWidgets.QPlainTextEdit()
        self._stream.setReadOnly(True); self._stream.setFixedHeight(100)
        self._stream.setFont(QtGui.QFont("Consolas", 10))
        self._stream.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_GRN};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        self._stream.setPlainText("  Waiting for feature writes...")
        vb.addWidget(self._stream); return grp

    def _build_table(self):
        w = QtWidgets.QWidget(); w.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(4)
        vb.addWidget(_lbl("Feature Store",
                          f"color:{_GRN};font-size:11px;font-weight:bold;border:none;"))
        cols = ["Feature Name", "Type", "Symbol",
                "Value", "Version", "Source", "Timestamp"]
        self._tbl = QtWidgets.QTableWidget(0, len(cols))
        self._tbl.setHorizontalHeaderLabels(cols)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.setStyleSheet(_TBL)
        vb.addWidget(self._tbl); return w

    # ── slots ─────────────────────────────────────────────────────────
    def _on_write(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected.")
            return
        from ..utils.feature_utils import make_feature
        ft   = self._type_combo.currentData()
        name = self._name_ed.text().strip() or "feature"
        sym  = self._symbol_ed.text().strip() or "BTC"
        val  = self._value_sp.value()
        ver  = self._ver_sp.value()
        rec  = make_feature(name, ft, sym, val, version=ver)
        try:
            ok, reason = self._engine.write_feature(rec)
            color = _GRN if ok else _YLW
            line  = (f"  {'✓' if ok else '⚠'}  [{ft.value:<12}] "
                     f"{name}/{sym}  val={val:.6f}  v{ver}  {reason}")
            self._stream.appendPlainText(line)
            self._stream.verticalScrollBar().setValue(
                self._stream.verticalScrollBar().maximum())
            self._refresh_table(); self._refresh_kpi()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _on_simulate_market(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected.")
            return
        import random
        sym    = self._mkt_symbol.text().strip() or "ETHUSDT"
        n_bars = self._mkt_bars.value()
        base   = random.uniform(1000.0, 5000.0)
        prices  = [base * (1 + random.uniform(-0.02, 0.02)) for _ in range(n_bars)]
        volumes = [random.uniform(1e6, 5e6) for _ in range(n_bars)]
        try:
            result = self._engine.ingest_market_features(sym, prices, volumes)
            self._stream.appendPlainText(
                f"  ✓  Market sim {sym}  {n_bars} bars → "
                f"written={result['written']} skipped={result['skipped']}")
            self._stream.verticalScrollBar().setValue(
                self._stream.verticalScrollBar().maximum())
            self._refresh_table(); self._refresh_kpi()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _refresh_kpi(self):
        if self._engine is None: return
        s = self._engine.get_feature_state()
        self._kpi["total"].setText(str(s.total_features))
        self._kpi["active"].setText(str(s.active_features))
        self._kpi["versions"].setText(str(s.total_versions))
        self._kpi["overwrites"].setText(str(s.overwrite_count))
        self._kpi["rate"].setText(f"{s.write_rate:.1f}")
        self._kpi["symbols"].setText(str(len(s.symbol_counts)))

    def _refresh_table(self):
        if self._engine is None: return
        records = self._engine.get_all_features()
        self._tbl.setRowCount(0)
        for r in sorted(records, key=lambda x: x.timestamp, reverse=True)[:100]:
            row = self._tbl.rowCount(); self._tbl.insertRow(row)
            tc = _TYPE_COLOR.get(r.feature_type, _FG)
            cells = [r.feature_name, r.feature_type.value, r.symbol,
                     f"{r.value:.8f}", str(r.version), r.source,
                     str(r.timestamp)[:19]]
            for col, txt in enumerate(cells):
                it = QtWidgets.QTableWidgetItem(txt)
                it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if col == 1:
                    it.setForeground(QtGui.QColor(tc))
                self._tbl.setItem(row, col, it)

    def refresh(self):
        self._refresh_kpi(); self._refresh_table()
