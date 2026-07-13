"""
adaptive_learning_ai/ui/learning_tab.py  (Phase 3)

LearningTab — 学习引擎可视化面板。
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import AdaptationTarget, FeedbackType

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _BLUE = "#89b4fa"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"
_RED = "#f38ba8"; _MAV = "#cba6f7"; _HEAD = "#313244"; _CYN = "#89dceb"
_IS = ("QDoubleSpinBox,QSpinBox,QComboBox,QLineEdit{background:#313244;color:#cdd6f4;"
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
_TARGET_COLOR = {
    AdaptationTarget.EXECUTION_PARAMS:   _BLUE,
    AdaptationTarget.STRATEGY_ALLOCATION:_GRN,
    AdaptationTarget.PORTFOLIO_WEIGHTS:  _MAV,
    AdaptationTarget.RISK_THRESHOLDS:    _RED,
    AdaptationTarget.ALPHA_WEIGHTS:      _YLW,
}


def _lbl(t, s=""):
    w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w


def _sep():
    s = QtWidgets.QFrame()
    s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    s.setStyleSheet("border:none;border-top:1px solid #45475a;background:transparent;")
    return s


class LearningTab(QtWidgets.QWidget):
    """学习引擎可视化面板（Phase 3）。"""

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

    def _build_left(self):
        panel = QtWidgets.QWidget(); panel.setFixedWidth(230)
        panel.setStyleSheet(
            f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(12, 14, 12, 14); vb.setSpacing(10)
        vb.addWidget(_lbl("Learning Engine",
                          f"color:{_GRN};font-weight:bold;font-size:12px;border:none;"))
        vb.addWidget(_sep())
        fm = QtWidgets.QFormLayout()
        fm.setContentsMargins(0, 0, 0, 0); fm.setVerticalSpacing(8)
        fm.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._conf_thresh = QtWidgets.QDoubleSpinBox()
        self._conf_thresh.setRange(0.0, 1.0); self._conf_thresh.setValue(0.7)
        self._conf_thresh.setSingleStep(0.05); self._conf_thresh.setDecimals(2)
        self._conf_thresh.setStyleSheet(_IS)
        fm.addRow(_lbl("Conf Threshold:", _LLBL), self._conf_thresh)
        self._top_n = QtWidgets.QSpinBox()
        self._top_n.setRange(1, 20); self._top_n.setValue(5)
        self._top_n.setStyleSheet(_IS)
        fm.addRow(_lbl("Top-N Urgent:", _LLBL), self._top_n)
        self._target_combo = QtWidgets.QComboBox()
        self._target_combo.addItem("All Targets", None)
        for t in AdaptationTarget:
            self._target_combo.addItem(t.value.replace("_", " ").title(), t)
        self._target_combo.setStyleSheet(_IS)
        fm.addRow(_lbl("Filter Target:", _LLBL), self._target_combo)
        vb.addLayout(fm); vb.addWidget(_sep())
        vb.addWidget(_lbl("Simulate Feedback",
                          f"color:{_MUT};font-size:10px;border:none;"))
        fm2 = QtWidgets.QFormLayout()
        fm2.setContentsMargins(0, 0, 0, 0); fm2.setVerticalSpacing(6)
        fm2.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._sim_type = QtWidgets.QComboBox()
        for ft in FeedbackType:
            self._sim_type.addItem(ft.value.replace("_", " ").title(), ft)
        self._sim_type.setStyleSheet(_IS)
        fm2.addRow(_lbl("Type:", _LLBL), self._sim_type)
        self._sim_n = QtWidgets.QSpinBox()
        self._sim_n.setRange(1, 20); self._sim_n.setValue(5)
        self._sim_n.setStyleSheet(_IS)
        fm2.addRow(_lbl("Count:", _LLBL), self._sim_n)
        vb.addLayout(fm2); vb.addStretch()
        btn = QtWidgets.QPushButton(">> Run Learning Cycle")
        btn.setStyleSheet(
            f"QPushButton{{background:{_GRN};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:8px;font-size:12px;}}"
            f"QPushButton:hover{{background:#94e2a1;}}")
        btn.clicked.connect(self._on_run_cycle); vb.addWidget(btn)
        btn2 = QtWidgets.QPushButton("Simulate + Learn")
        btn2.setStyleSheet(
            f"QPushButton{{background:transparent;color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:4px;"
            f"padding:6px;font-size:11px;}}"
            f"QPushButton:hover{{background:{_HEAD};}}")
        btn2.clicked.connect(self._on_simulate); vb.addWidget(btn2)
        return panel

    def _build_right(self):
        panel = QtWidgets.QWidget(); panel.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(8)
        vb.addWidget(self._build_kpi_bar())
        vb.addWidget(self._build_signal_stream())
        vb.addWidget(self._build_pattern_table())
        return panel

    def _build_kpi_bar(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(16, 10, 16, 10); h.setSpacing(18)
        self._kpi: dict = {}
        for key, txt, color in [
            ("cycle",    "Cycle",         _CYN),
            ("signals",  "Total Signals", _BLUE),
            ("patterns", "Patterns",      _GRN),
            ("hi_conf",  "High Conf",     _YLW),
            ("avg_conf", "Avg Conf",      _GRN),
            ("velocity", "Velocity",      _MAV),
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

    def _build_signal_stream(self):
        grp = QtWidgets.QGroupBox("Learning Signal Stream")
        grp.setStyleSheet(
            f"QGroupBox{{color:{_GRN};border:1px solid {_BORDER};"
            f"border-radius:4px;margin-top:8px;font-size:11px;background:{_DARK};}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}")
        vb = QtWidgets.QVBoxLayout(grp); vb.setContentsMargins(10, 14, 10, 10)
        self._stream = QtWidgets.QPlainTextEdit()
        self._stream.setReadOnly(True); self._stream.setFixedHeight(110)
        self._stream.setFont(QtGui.QFont("Consolas", 10))
        self._stream.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_GRN};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        self._stream.setPlainText("  Run a learning cycle to see signals...")
        vb.addWidget(self._stream); return grp

    def _build_pattern_table(self):
        w = QtWidgets.QWidget(); w.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(4)
        vb.addWidget(_lbl("Active Learning Patterns",
                          f"color:{_GRN};font-size:11px;font-weight:bold;border:none;"))
        cols = ["Pattern", "Feedback", "Target", "N",
                "AvgConf", "Consistency", "Strength", "RecDelta", "Detected"]
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

    def _on_run_cycle(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected.")
            return
        try:
            result = self._engine.run_learning_cycle()
            self._append_stream(
                f"  Cycle {result['cycle']}  records={result['n_records']}  "
                f"signals={result['n_signals']}  patterns={result['n_patterns']}")
            self._refresh_patterns(); self._refresh_kpi()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _on_simulate(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected.")
            return
        import random
        ft = self._sim_type.currentData(); n = self._sim_n.value()
        try:
            for _ in range(n):
                base = random.uniform(80.0, 120.0)
                dev  = random.uniform(-0.05, 0.05)
                self._engine.ingest_feedback({
                    "feedback_type":  ft,
                    "decision_value": base,
                    "actual_value":   base * (1 + dev),
                    "source_module":  ft.value.split("_")[0],
                })
            result = self._engine.run_learning_cycle()
            self._append_stream(
                f"  Sim {n}x {ft.value}  "
                f"signals={result['n_signals']}  patterns={result['n_patterns']}")
            self._refresh_patterns(); self._refresh_kpi()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _append_stream(self, line: str):
        self._stream.appendPlainText(line)
        self._stream.verticalScrollBar().setValue(
            self._stream.verticalScrollBar().maximum())

    def _refresh_kpi(self):
        if self._engine is None: return
        s = self._engine.get_learning_state()
        self._kpi["cycle"].setText(str(s.cycle))
        self._kpi["signals"].setText(str(s.total_signals))
        self._kpi["patterns"].setText(str(s.active_patterns))
        self._kpi["hi_conf"].setText(str(s.high_conf_signals))
        self._kpi["avg_conf"].setText(f"{s.avg_confidence:.3f}")
        self._kpi["velocity"].setText(f"{s.learning_velocity:.3f}")

    def _refresh_patterns(self):
        if self._engine is None: return
        tgt = self._target_combo.currentData()
        patterns = self._engine.get_learning_patterns(tgt)
        self._tbl.setRowCount(0)
        for p in patterns:
            row = self._tbl.rowCount(); self._tbl.insertRow(row)
            tgt_c = _TARGET_COLOR.get(p.target, _FG)
            cells = [p.pattern_id[-8:],
                     p.feedback_type.value.replace("_", " "),
                     p.target.value.replace("_", " "),
                     str(p.n_signals), f"{p.avg_confidence:.3f}",
                     f"{p.consistency:.3f}", f"{p.pattern_strength:.3f}",
                     f"{p.recommended_delta:+.5f}", str(p.detected_at)[:16]]
            for col, txt in enumerate(cells):
                it = QtWidgets.QTableWidgetItem(txt)
                it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if col == 2: it.setForeground(QtGui.QColor(tgt_c))
                elif col == 6:
                    sc = p.pattern_strength
                    it.setForeground(QtGui.QColor(
                        _GRN if sc >= 0.6 else (_YLW if sc >= 0.3 else _MUT)))
                self._tbl.setItem(row, col, it)

    def refresh(self):
        self._refresh_kpi(); self._refresh_patterns()
