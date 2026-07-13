"""
adaptive_learning_ai/ui/feedback_tab.py  (Phase 2)

FeedbackTab — 反馈采集可视化面板。
左栏：反馈输入控制 | 右侧：状态KPI + 反馈流 + 记录表
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import FeedbackType

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _BLUE = "#89b4fa"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"
_RED = "#f38ba8"; _MAV = "#cba6f7"; _HEAD = "#313244"; _CYN = "#89dceb"
_IS = ("QDoubleSpinBox,QComboBox,QLineEdit{background:#313244;color:#cdd6f4;"
       "border:1px solid #45475a;border-radius:3px;padding:3px 6px;font-size:11px;}"
       "QComboBox::drop-down{border:none;}")
_LLBL = "color:#6c7086;font-size:11px;border:none;background:transparent;"
_TBL = ("QTableWidget{background:#181825;color:#cdd6f4;border:1px solid #45475a;"
        "gridline-color:#45475a;font-size:11px;}"
        "QTableWidget::item{padding:3px 6px;}"
        "QTableWidget::item:alternate{background:#1e1e2e;}"
        "QTableWidget::item:selected{background:#45475a;}"
        "QHeaderView::section{background:#313244;color:#6c7086;border:none;"
        "border-bottom:1px solid #45475a;padding:4px 6px;font-size:10px;}")

_TYPE_COLOR = {
    FeedbackType.EXECUTION_SLIPPAGE:   _BLUE,
    FeedbackType.STRATEGY_PERFORMANCE: _GRN,
    FeedbackType.PORTFOLIO_DRIFT:      _MAV,
    FeedbackType.RISK_VIOLATION:       _RED,
    FeedbackType.ALPHA_DECAY:          _YLW,
    FeedbackType.REGIME_MISMATCH:      _CYN,
}


def _lbl(t, s=""):
    w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w


def _sep():
    s = QtWidgets.QFrame()
    s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    s.setStyleSheet("border:none;border-top:1px solid #45475a;background:transparent;")
    return s


class FeedbackTab(QtWidgets.QWidget):
    """反馈采集可视化面板（Phase 2）。"""

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
        vb.addWidget(_lbl("反馈采集控制",
                          f"color:{_CYN};font-weight:bold;font-size:12px;border:none;"))
        vb.addWidget(_sep())

        fm = QtWidgets.QFormLayout()
        fm.setContentsMargins(0, 0, 0, 0); fm.setVerticalSpacing(8)
        fm.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        self._type_combo = QtWidgets.QComboBox()
        for ft in FeedbackType:
            self._type_combo.addItem(ft.value.replace("_", " ").title(), ft)
        self._type_combo.setStyleSheet(_IS)
        fm.addRow(_lbl("反馈类型:", _LLBL), self._type_combo)

        self._decision_sp = QtWidgets.QDoubleSpinBox()
        self._decision_sp.setRange(-1e6, 1e6); self._decision_sp.setValue(100.0)
        self._decision_sp.setDecimals(4); self._decision_sp.setStyleSheet(_IS)
        fm.addRow(_lbl("决策值:", _LLBL), self._decision_sp)

        self._actual_sp = QtWidgets.QDoubleSpinBox()
        self._actual_sp.setRange(-1e6, 1e6); self._actual_sp.setValue(100.5)
        self._actual_sp.setDecimals(4); self._actual_sp.setStyleSheet(_IS)
        fm.addRow(_lbl("实际值:", _LLBL), self._actual_sp)

        self._symbol_ed = QtWidgets.QLineEdit("BTCUSDT")
        self._symbol_ed.setStyleSheet(_IS)
        fm.addRow(_lbl("标的:", _LLBL), self._symbol_ed)

        self._strat_ed = QtWidgets.QLineEdit("S1")
        self._strat_ed.setStyleSheet(_IS)
        fm.addRow(_lbl("策略ID:", _LLBL), self._strat_ed)

        vb.addLayout(fm); vb.addStretch()

        btn = QtWidgets.QPushButton(">> 注入反馈记录")
        btn.setStyleSheet(
            f"QPushButton{{background:{_CYN};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:8px;font-size:12px;}}"
            f"QPushButton:hover{{background:#74c7ec;}}")
        btn.clicked.connect(self._on_ingest)
        vb.addWidget(btn)

        btn2 = QtWidgets.QPushButton("推进周期")
        btn2.setStyleSheet(
            f"QPushButton{{background:transparent;color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:4px;"
            f"padding:6px;font-size:11px;}}"
            f"QPushButton:hover{{background:{_HEAD};}}")
        btn2.clicked.connect(self._on_next_cycle)
        vb.addWidget(btn2)
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
            ("total",    "Total Records",  _FG),
            ("batches",  "Batches",        _BLUE),
            ("cycle",    "Cycle",          _CYN),
            ("avg_sev",  "Avg Severity",   _YLW),
            ("avg_sig",  "Avg Signal",     _GRN),
            ("high_sev", "High Severity%", _RED),
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
        grp = QtWidgets.QGroupBox("Feedback Stream")
        grp.setStyleSheet(
            f"QGroupBox{{color:{_CYN};border:1px solid {_BORDER};"
            f"border-radius:4px;margin-top:8px;font-size:11px;background:{_DARK};}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}")
        vb = QtWidgets.QVBoxLayout(grp); vb.setContentsMargins(10, 14, 10, 10)
        self._stream = QtWidgets.QPlainTextEdit()
        self._stream.setReadOnly(True); self._stream.setFixedHeight(120)
        self._stream.setFont(QtGui.QFont("Consolas", 10))
        self._stream.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_GRN};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        self._stream.setPlainText("  Waiting for feedback records...")
        vb.addWidget(self._stream); return grp

    def _build_table(self):
        w = QtWidgets.QWidget(); w.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(4)
        vb.addWidget(_lbl("Feedback Records",
                          f"color:{_CYN};font-size:11px;font-weight:bold;border:none;"))
        cols = ["ID", "Type", "Source", "Decision",
                "Actual", "Deviation", "Severity", "Signal", "Time"]
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
    def _on_ingest(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected.")
            return
        ft = self._type_combo.currentData()
        raw = {
            "feedback_type":  ft,
            "decision_value": self._decision_sp.value(),
            "actual_value":   self._actual_sp.value(),
            "source_module":  ft.value.split("_")[0],
            "symbol":         self._symbol_ed.text().strip(),
            "strategy_id":    self._strat_ed.text().strip(),
        }
        try:
            record = self._engine.ingest_feedback(raw)
            self._append_stream(record)
            self._append_row(record)
            self._refresh_kpi()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _on_next_cycle(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected.")
            return
        batch = self._engine.next_feedback_cycle()
        self._stream.appendPlainText(
            f"\n  ── Cycle closed ── {batch.get('batch_id','')} "
            f"records={batch.get('n_records',0)} "
            f"avg_sev={batch.get('avg_severity',0):.3f}\n")
        self._refresh_kpi()

    def _append_stream(self, record):
        color_map = {ft: c for ft, c in _TYPE_COLOR.items()}
        ft    = record.feedback_type
        line  = (f"  [{ft.value:<26}] "
                 f"dev={record.deviation_pct:+.3%}  "
                 f"sev={record.severity:.3f}  "
                 f"sig={record.signal_strength:.3f}  "
                 f"{record.symbol}")
        self._stream.appendPlainText(line)
        sb = self._stream.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _append_row(self, record):
        row = self._tbl.rowCount(); self._tbl.insertRow(row)
        ft_color = _TYPE_COLOR.get(record.feedback_type, _FG)
        cells = [
            record.record_id[-8:],
            record.feedback_type.value.replace("_", " "),
            record.source_module,
            f"{record.decision_value:.4f}",
            f"{record.actual_value:.4f}",
            f"{record.deviation_pct:+.3%}",
            f"{record.severity:.3f}",
            f"{record.signal_strength:.3f}",
            str(record.created_at)[:19],
        ]
        for col, txt in enumerate(cells):
            it = QtWidgets.QTableWidgetItem(txt)
            it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if col == 1:
                it.setForeground(QtGui.QColor(ft_color))
            elif col == 6:
                sev_c = _RED if record.severity > 0.7 else (
                    _YLW if record.severity > 0.4 else _GRN)
                it.setForeground(QtGui.QColor(sev_c))
            self._tbl.setItem(row, col, it)
        self._tbl.scrollToBottom()

    def _refresh_kpi(self):
        if self._engine is None:
            return
        s = self._engine.get_feedback_state()
        self._kpi["total"].setText(str(s.total_records))
        self._kpi["batches"].setText(str(s.total_batches))
        self._kpi["cycle"].setText(str(s.current_cycle))
        self._kpi["avg_sev"].setText(f"{s.avg_severity:.3f}")
        self._kpi["avg_sig"].setText(f"{s.avg_signal:.3f}")
        self._kpi["high_sev"].setText(f"{s.high_severity_pct:.1%}")

    def refresh(self):
        if self._engine is None:
            return
        self._refresh_kpi()
        records = self._engine.get_feedback_records(50)
        self._tbl.setRowCount(0)
        for r in records:
            self._append_row(r)
