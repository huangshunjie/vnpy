"""
global_portfolio_intelligence/ui/performance_tab.py  (Phase 4)

PerformanceTab — 资金流可视化面板。
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import AllocationMode

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _BLUE = "#89b4fa"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"
_RED = "#f38ba8"; _MAV = "#cba6f7"; _HEAD = "#313244"
_IS = ("QSpinBox,QDoubleSpinBox,QComboBox,QLineEdit{background:#313244;color:#cdd6f4;"
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


def _lbl(t, s=""):
    w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w


def _sep():
    s = QtWidgets.QFrame()
    s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    s.setStyleSheet("border:none;border-top:1px solid #45475a;background:transparent;")
    return s


class PerformanceTab(QtWidgets.QWidget):
    """资金流可视化面板（Phase 4）。"""

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
        vb.addWidget(_lbl("Capital Flow Config",
                          f"color:{_MAV};font-weight:bold;font-size:12px;border:none;"))
        vb.addWidget(_sep())
        fm = QtWidgets.QFormLayout()
        fm.setContentsMargins(0, 0, 0, 0); fm.setVerticalSpacing(8)
        fm.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._total_cap = QtWidgets.QDoubleSpinBox()
        self._total_cap.setRange(0, 1e12); self._total_cap.setValue(10_000_000)
        self._total_cap.setDecimals(0); self._total_cap.setSingleStep(1_000_000)
        self._total_cap.setStyleSheet(_IS)
        fm.addRow(_lbl("Total Capital:", _LLBL), self._total_cap)
        self._mode_combo = QtWidgets.QComboBox()
        for m in AllocationMode:
            self._mode_combo.addItem(m.value.replace("_", " ").title(), m)
        self._mode_combo.setStyleSheet(_IS)
        fm.addRow(_lbl("Alloc Mode:", _LLBL), self._mode_combo)
        vb.addLayout(fm); vb.addWidget(_sep())
        vb.addWidget(_lbl("Strategies (ID,score,risk)",
                          f"color:{_MUT};font-size:10px;border:none;"))
        self._strat_input = QtWidgets.QPlainTextEdit()
        self._strat_input.setPlaceholderText("S1,75,0.15\nS2,60,0.20\nS3,80,0.12")
        self._strat_input.setFixedHeight(80)
        self._strat_input.setStyleSheet(
            f"QPlainTextEdit{{background:{_HEAD};color:{_FG};"
            f"border:1px solid {_BORDER};border-radius:3px;font-size:10px;}}")
        vb.addWidget(self._strat_input)
        vb.addWidget(_lbl("Alphas (ID,score)",
                          f"color:{_MUT};font-size:10px;border:none;"))
        self._alpha_input = QtWidgets.QPlainTextEdit()
        self._alpha_input.setPlaceholderText("A1,70\nA2,65\nA3,80")
        self._alpha_input.setFixedHeight(65)
        self._alpha_input.setStyleSheet(
            f"QPlainTextEdit{{background:{_HEAD};color:{_FG};"
            f"border:1px solid {_BORDER};border-radius:3px;font-size:10px;}}")
        vb.addWidget(self._alpha_input); vb.addStretch()
        btn = QtWidgets.QPushButton(">> Allocate Capital")
        btn.setStyleSheet(
            f"QPushButton{{background:{_BLUE};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:8px;font-size:12px;}}"
            f"QPushButton:hover{{background:#74c7ec;}}")
        btn.clicked.connect(self._on_allocate); vb.addWidget(btn)
        btn2 = QtWidgets.QPushButton("Perf Rebalance")
        btn2.setStyleSheet(
            f"QPushButton{{background:transparent;color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:4px;"
            f"padding:6px;font-size:11px;}}"
            f"QPushButton:hover{{background:{_HEAD};}}")
        btn2.clicked.connect(self._on_perf_rebalance); vb.addWidget(btn2)
        return panel

    def _build_right(self):
        panel = QtWidgets.QWidget(); panel.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(8)
        vb.addWidget(self._build_kpi_bar())
        vb.addWidget(self._build_flow_chart())
        vb.addWidget(self._build_budget_table())
        return panel

    def _build_kpi_bar(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(16, 10, 16, 10); h.setSpacing(16)
        self._kpi: dict = {}
        for key, txt, color in [
            ("total",        "Total",        _FG),
            ("deployed",     "Deployed",     _BLUE),
            ("idle",         "Idle",         _YLW),
            ("ratio",        "Deploy%",      _GRN),
            ("n_strat",      "Entities",     _MAV),
            ("concentration","Concentration",_GRN),
            ("efficiency",   "Efficiency",   _BLUE),
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
                f"color:{color};font-size:12px;font-weight:bold;"
                f"border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv)
            self._kpi[key] = lv; h.addWidget(cell)
        h.addStretch(); return w

    def _build_flow_chart(self):
        grp = QtWidgets.QGroupBox("Capital Flow Distribution")
        grp.setStyleSheet(
            f"QGroupBox{{color:{_MAV};border:1px solid {_BORDER};"
            f"border-radius:4px;margin-top:8px;font-size:11px;background:{_DARK};}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}")
        vb = QtWidgets.QVBoxLayout(grp); vb.setContentsMargins(10, 14, 10, 10)
        self._flow_text = QtWidgets.QPlainTextEdit()
        self._flow_text.setReadOnly(True); self._flow_text.setFixedHeight(140)
        self._flow_text.setFont(QtGui.QFont("Consolas", 10))
        self._flow_text.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_GRN};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        self._flow_text.setPlainText("  Execute capital allocation to see flow distribution")
        vb.addWidget(self._flow_text); return grp

    def _build_budget_table(self):
        w = QtWidgets.QWidget(); w.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(4)
        vb.addWidget(_lbl("Budget Details",
                          f"color:{_MAV};font-size:11px;font-weight:bold;border:none;"))
        cols = ["ID", "Type", "Allocated", "Ratio", "Perf", "Regime", "Risk", "Active"]
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

    def _parse_strategies(self):
        result = []
        for line in self._strat_input.toPlainText().splitlines():
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if len(parts) >= 1:
                sid   = parts[0]
                score = float(parts[1]) if len(parts) > 1 else 50.0
                risk  = float(parts[2]) if len(parts) > 2 else 0.15
                result.append((sid, score, risk))
        return result

    def _parse_alphas(self):
        result = []
        for line in self._alpha_input.toPlainText().splitlines():
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if len(parts) >= 1:
                result.append((parts[0], float(parts[1]) if len(parts) > 1 else 50.0))
        return result

    def _on_allocate(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected.")
            return
        try:
            self._engine.set_total_capital(self._total_cap.value())
            mode = self._mode_combo.currentData()
            self._engine.set_allocation_mode(mode)
            for sid, score, risk in self._parse_strategies():
                self._engine.register_strategy(sid, score, risk)
            for aid, score in self._parse_alphas():
                self._engine.register_alpha(aid, score)
            state = self._engine.allocate_capital(mode)
            self._fill(state)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _on_perf_rebalance(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected.")
            return
        try:
            updates = {}
            for sid, score, _ in self._parse_strategies():
                updates[sid] = score
            for aid, score in self._parse_alphas():
                updates[aid] = score
            state = self._engine.rebalance_by_performance(updates)
            self._fill(state)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _fill(self, state):
        def _fmt(v):
            return f"{v/1_000_000:.2f}M" if v >= 1_000_000 else f"{v:,.0f}"
        self._kpi["total"].setText(_fmt(state.total_capital))
        self._kpi["deployed"].setText(_fmt(state.deployed_capital))
        self._kpi["idle"].setText(_fmt(state.idle_capital))
        self._kpi["ratio"].setText(f"{state.deployment_ratio:.1%}")
        self._kpi["n_strat"].setText(
            f"{state.n_active_strategies}S+{state.n_active_alphas}A")
        self._kpi["concentration"].setText(f"{state.concentration_score:.1f}")
        self._kpi["efficiency"].setText(f"{state.efficiency_score:.1f}")
        all_b = list(state.strategy_budgets) + list(state.alpha_budgets)
        lines = [f"  Total: {_fmt(state.total_capital)}  "
                 f"Deployed: {_fmt(state.deployed_capital)} "
                 f"({state.deployment_ratio:.1%})", ""]
        for b in all_b:
            bar = "#" * int(b.allocation_ratio * 50)
            lines.append(
                f"  [{b.entity_type[0].upper()}] {b.entity_id:<8}"
                f"  {_fmt(b.allocated_capital):>10}"
                f"  {b.allocation_ratio:.3%}  {bar}")
        self._flow_text.setPlainText("\n".join(lines))
        self._tbl.setRowCount(0)
        for b in all_b:
            row = self._tbl.rowCount(); self._tbl.insertRow(row)
            cells = [b.entity_id, b.entity_type, f"{b.allocated_capital:,.0f}",
                     f"{b.allocation_ratio:.3%}", f"{b.performance_score:.1f}",
                     f"{b.regime_weight:.3f}", f"{b.risk_budget:.3f}",
                     "Y" if b.is_active else "N"]
            for col, txt in enumerate(cells):
                it = QtWidgets.QTableWidgetItem(txt)
                it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if col == 1:
                    it.setForeground(
                        QtGui.QColor(_BLUE if b.entity_type == "strategy" else _MAV))
                self._tbl.setItem(row, col, it)

    def refresh(self):
        if self._engine is None: return
        state = self._engine.get_capital_flow_state()
        if state and state.flow_count > 0:
            self._fill(state)
