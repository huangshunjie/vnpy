"""
global_portfolio_intelligence/ui/rebalance_tab.py  (Phase 5)

RebalanceTab — 再平衡决策可视化面板。
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import RebalanceTrigger

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _BLUE = "#89b4fa"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"
_RED = "#f38ba8"; _MAV = "#cba6f7"; _HEAD = "#313244"
_IS = ("QDoubleSpinBox{background:#313244;color:#cdd6f4;"
       "border:1px solid #45475a;border-radius:3px;padding:3px 6px;font-size:11px;}")
_LLBL = "color:#6c7086;font-size:11px;border:none;background:transparent;"
_TBL = ("QTableWidget{background:#181825;color:#cdd6f4;border:1px solid #45475a;"
        "gridline-color:#45475a;font-size:11px;}"
        "QTableWidget::item{padding:3px 6px;}"
        "QTableWidget::item:alternate{background:#1e1e2e;}"
        "QTableWidget::item:selected{background:#45475a;}"
        "QHeaderView::section{background:#313244;color:#6c7086;border:none;"
        "border-bottom:1px solid #45475a;padding:4px 6px;font-size:10px;}")


def _lbl(t, s=""):
    w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w


def _sep():
    s = QtWidgets.QFrame()
    s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    s.setStyleSheet("border:none;border-top:1px solid #45475a;background:transparent;")
    return s


class RebalanceTab(QtWidgets.QWidget):
    """再平衡决策可视化面板（Phase 5）。"""

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
        vb.addWidget(_lbl("Rebalance Config",
                          f"color:{_MAV};font-weight:bold;font-size:12px;border:none;"))
        vb.addWidget(_sep())
        vb.addWidget(_lbl("Trigger Thresholds",
                          f"color:{_MUT};font-size:10px;border:none;"))

        fm = QtWidgets.QFormLayout()
        fm.setContentsMargins(0, 0, 0, 0); fm.setVerticalSpacing(8)
        fm.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._thresh: dict = {}
        for key, label, default in [
            ("risk_drift",        "Risk Drift",     0.05),
            ("alpha_decay",       "Alpha Decay",    0.15),
            ("exec_inefficiency", "Exec Ineff.",    0.20),
            ("regime_shift_prob", "Regime Shift",   0.60),
        ]:
            sp = QtWidgets.QDoubleSpinBox()
            sp.setRange(0.01, 1.0); sp.setValue(default)
            sp.setSingleStep(0.05); sp.setDecimals(2)
            sp.setStyleSheet(_IS)
            self._thresh[key] = sp
            fm.addRow(_lbl(f"{label}:", _LLBL), sp)
        vb.addLayout(fm); vb.addWidget(_sep())

        vb.addWidget(_lbl("System Metrics (simulate)",
                          f"color:{_MUT};font-size:10px;border:none;"))
        fm2 = QtWidgets.QFormLayout()
        fm2.setContentsMargins(0, 0, 0, 0); fm2.setVerticalSpacing(6)
        fm2.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._metrics: dict = {}
        for key, label, default in [
            ("risk_drift",        "Risk Drift",   0.03),
            ("alpha_decay_rate",  "Alpha Decay",  0.10),
            ("exec_inefficiency", "Exec Ineff.",  0.15),
            ("regime_shift_prob", "Regime Prob",  0.40),
        ]:
            sp = QtWidgets.QDoubleSpinBox()
            sp.setRange(0.0, 1.0); sp.setValue(default)
            sp.setSingleStep(0.05); sp.setDecimals(2)
            sp.setStyleSheet(_IS)
            self._metrics[key] = sp
            fm2.addRow(_lbl(f"{label}:", _LLBL), sp)
        vb.addLayout(fm2); vb.addStretch()

        btn = QtWidgets.QPushButton(">> Detect Rebalance")
        btn.setStyleSheet(
            f"QPushButton{{background:{_BLUE};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:8px;font-size:12px;}}"
            f"QPushButton:hover{{background:#74c7ec;}}")
        btn.clicked.connect(self._on_detect); vb.addWidget(btn)

        btn2 = QtWidgets.QPushButton("Manual Rebalance")
        btn2.setStyleSheet(
            f"QPushButton{{background:transparent;color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:4px;"
            f"padding:6px;font-size:11px;}}"
            f"QPushButton:hover{{background:{_HEAD};}}")
        btn2.clicked.connect(self._on_manual); vb.addWidget(btn2)
        return panel

    def _build_right(self):
        panel = QtWidgets.QWidget(); panel.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(8)
        vb.addWidget(self._build_health_bar())
        vb.addWidget(self._build_trigger_panel())
        vb.addWidget(self._build_adj_table())
        return panel

    def _build_health_bar(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(16, 10, 16, 10); h.setSpacing(20)

        self._health_lbl = QtWidgets.QLabel("--")
        self._health_lbl.setStyleSheet(
            f"color:{_GRN};font-size:40px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._health_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._health_lbl.setFixedWidth(90)
        h.addWidget(self._health_lbl)

        ht = QtWidgets.QLabel("System\nHealth")
        ht.setStyleSheet(f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        h.addWidget(ht)

        vsep = QtWidgets.QFrame()
        vsep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        vsep.setStyleSheet("border:none;border-left:1px solid #45475a;background:transparent;")
        h.addWidget(vsep)

        self._rb_kpi: dict = {}
        for key, txt, color in [
            ("imbalance",   "Imbalance",   _RED),
            ("triggers",    "Triggers",    _YLW),
            ("high_adj",    "High-Pri Adj",_RED),
            ("count",       "Rebalances",  _BLUE),
            ("risk_drift",  "Risk Drift",  _YLW),
            ("alpha_decay", "Alpha Decay", _MAV),
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
            self._rb_kpi[key] = lv; h.addWidget(cell)
        h.addStretch(); return w

    def _build_trigger_panel(self):
        grp = QtWidgets.QGroupBox("Active Triggers")
        grp.setStyleSheet(
            f"QGroupBox{{color:{_MAV};border:1px solid {_BORDER};"
            f"border-radius:4px;margin-top:8px;font-size:11px;background:{_DARK};}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}")
        vb = QtWidgets.QVBoxLayout(grp); vb.setContentsMargins(10, 14, 10, 10)
        self._trigger_text = QtWidgets.QPlainTextEdit()
        self._trigger_text.setReadOnly(True); self._trigger_text.setFixedHeight(110)
        self._trigger_text.setFont(QtGui.QFont("Consolas", 10))
        self._trigger_text.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_YLW};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        self._trigger_text.setPlainText("  No active triggers")
        vb.addWidget(self._trigger_text); return grp

    def _build_adj_table(self):
        w = QtWidgets.QWidget(); w.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(4)
        vb.addWidget(_lbl("Adjustment Recommendations",
                          f"color:{_MAV};font-size:11px;font-weight:bold;border:none;"))
        cols = ["Entity", "Type", "Dimension", "Current", "Target",
                "Delta", "Priority", "Reason"]
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

    def _on_detect(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected.")
            return
        for key, sp in self._thresh.items():
            self._engine.set_rebalance_threshold(key, sp.value())
        metrics = {k: sp.value() for k, sp in self._metrics.items()}
        try:
            state = self._engine.detect_rebalance(metrics)
            self._fill(state)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _on_manual(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected.")
            return
        try:
            state = self._engine.manual_rebalance("User initiated manual rebalance")
            self._fill(state)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _fill(self, state):
        h = state.system_health
        hc = _GRN if h >= 70 else (_YLW if h >= 40 else _RED)
        self._health_lbl.setText(f"{h:.0f}")
        self._health_lbl.setStyleSheet(
            f"color:{hc};font-size:40px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._rb_kpi["imbalance"].setText(f"{state.imbalance_score:.1f}")
        self._rb_kpi["triggers"].setText(str(state.trigger_count))
        self._rb_kpi["high_adj"].setText(str(state.n_high_priority))
        self._rb_kpi["count"].setText(str(state.rebalance_count))
        self._rb_kpi["risk_drift"].setText(f"{state.risk_drift:.3f}")
        self._rb_kpi["alpha_decay"].setText(f"{state.alpha_decay_rate:.3f}")

        if state.active_triggers:
            lines = []
            for t in state.active_triggers:
                sev_bar = "!" * max(1, int(t.severity * 5))
                lines.append(
                    f"  [{t.trigger_type.value:<26}] "
                    f"sev={t.severity:.2f} {sev_bar}  {t.description}")
            self._trigger_text.setPlainText("\n".join(lines))
        else:
            self._trigger_text.setPlainText("  No active triggers — system balanced")

        self._tbl.setRowCount(0)
        for adj in state.adjustments:
            row = self._tbl.rowCount(); self._tbl.insertRow(row)
            pri_color = _RED if adj.priority == 1 else (_YLW if adj.priority == 2 else _MUT)
            cells = [adj.entity_id, adj.entity_type, adj.dimension,
                     f"{adj.current_value:.4f}", f"{adj.target_value:.4f}",
                     f"{adj.delta:+.4f}", str(adj.priority), adj.reason]
            for col, txt in enumerate(cells):
                it = QtWidgets.QTableWidgetItem(txt)
                it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if col == 6:
                    it.setForeground(QtGui.QColor(pri_color))
                elif col == 5:
                    it.setForeground(
                        QtGui.QColor(_GRN if adj.delta >= 0 else _RED))
                self._tbl.setItem(row, col, it)

    def refresh(self):
        if self._engine is None: return
        state = self._engine.get_rebalance_state()
        if state and state.rebalance_count > 0:
            self._fill(state)
