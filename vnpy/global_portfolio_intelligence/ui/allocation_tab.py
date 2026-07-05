"""
global_portfolio_intelligence/ui/allocation_tab.py  (Phase 3)

AllocationTab — 跨模块优化可视化面板。
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import OptimizationMode

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _BLUE = "#89b4fa"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"
_RED = "#f38ba8"; _MAV = "#cba6f7"; _HEAD = "#313244"

_IE = ("QLineEdit{background:#313244;color:#cdd6f4;"
       "border:1px solid #45475a;border-radius:3px;padding:3px 6px;font-size:11px;}")
_IS = ("QSpinBox,QDoubleSpinBox,QComboBox{background:#313244;color:#cdd6f4;"
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


class AllocationTab(QtWidgets.QWidget):
    """跨模块优化可视化面板（Phase 3）。"""

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
        vb.addWidget(_lbl("跨模块优化参数",
                          f"color:{_MAV};font-weight:bold;font-size:12px;border:none;"))
        vb.addWidget(_sep())
        fm = QtWidgets.QFormLayout()
        fm.setContentsMargins(0, 0, 0, 0); fm.setVerticalSpacing(8)
        fm.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._mode_combo = QtWidgets.QComboBox()
        for m in OptimizationMode:
            self._mode_combo.addItem(m.value.capitalize(), m)
        self._mode_combo.setStyleSheet(_IS)
        fm.addRow(_lbl("优化模式：", _LLBL), self._mode_combo)
        self._n_alpha = QtWidgets.QSpinBox()
        self._n_alpha.setRange(1, 10); self._n_alpha.setValue(3)
        self._n_alpha.setStyleSheet(_IS)
        fm.addRow(_lbl("Alpha数量：", _LLBL), self._n_alpha)
        self._n_strategy = QtWidgets.QSpinBox()
        self._n_strategy.setRange(1, 10); self._n_strategy.setValue(4)
        self._n_strategy.setStyleSheet(_IS)
        fm.addRow(_lbl("策略数量：", _LLBL), self._n_strategy)
        self._n_asset = QtWidgets.QSpinBox()
        self._n_asset.setRange(1, 20); self._n_asset.setValue(5)
        self._n_asset.setStyleSheet(_IS)
        fm.addRow(_lbl("资产数量：", _LLBL), self._n_asset)
        self._lr = QtWidgets.QDoubleSpinBox()
        self._lr.setRange(0.001, 0.5); self._lr.setValue(0.05)
        self._lr.setDecimals(3); self._lr.setStyleSheet(_IS)
        fm.addRow(_lbl("学习率：", _LLBL), self._lr)
        self._n_iter = QtWidgets.QSpinBox()
        self._n_iter.setRange(5, 200); self._n_iter.setValue(30)
        self._n_iter.setStyleSheet(_IS)
        fm.addRow(_lbl("迭代次数：", _LLBL), self._n_iter)
        vb.addLayout(fm); vb.addWidget(_sep())
        vb.addWidget(_lbl("子系统评分（逗号分隔）",
                          f"color:{_MUT};font-size:10px;border:none;"))
        fm2 = QtWidgets.QFormLayout()
        fm2.setContentsMargins(0, 0, 0, 0); fm2.setVerticalSpacing(6)
        fm2.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._alpha_sc = QtWidgets.QLineEdit("70,60,80")
        self._alpha_sc.setStyleSheet(_IE)
        fm2.addRow(_lbl("Alpha：", _LLBL), self._alpha_sc)
        self._strat_sc = QtWidgets.QLineEdit("75,65,80,55")
        self._strat_sc.setStyleSheet(_IE)
        fm2.addRow(_lbl("策略：", _LLBL), self._strat_sc)
        self._port_sc = QtWidgets.QLineEdit("70,60,65,80,75")
        self._port_sc.setStyleSheet(_IE)
        fm2.addRow(_lbl("组合：", _LLBL), self._port_sc)
        vb.addLayout(fm2); vb.addStretch()
        btn = QtWidgets.QPushButton(">> 运行跨模块优化")
        btn.setStyleSheet(
            f"QPushButton{{background:{_BLUE};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:8px;font-size:12px;}}"
            f"QPushButton:hover{{background:#74c7ec;}}")
        btn.clicked.connect(self._on_optimize); vb.addWidget(btn)
        btn2 = QtWidgets.QPushButton("风险平价模式")
        btn2.setStyleSheet(
            f"QPushButton{{background:transparent;color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:4px;"
            f"padding:6px;font-size:11px;}}"
            f"QPushButton:hover{{background:{_HEAD};}}")
        btn2.clicked.connect(self._on_risk_parity); vb.addWidget(btn2)
        return panel

    def _build_right(self):
        panel = QtWidgets.QWidget(); panel.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(8)
        vb.addWidget(self._build_score_bar())
        vb.addWidget(self._build_weights_display())
        vb.addWidget(self._build_history_table())
        return panel

    def _build_score_bar(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(16, 10, 16, 10); h.setSpacing(20)
        self._comp_lbl = QtWidgets.QLabel("--")
        self._comp_lbl.setStyleSheet(
            f"color:{_BLUE};font-size:38px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._comp_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._comp_lbl.setFixedWidth(80); h.addWidget(self._comp_lbl)
        ct = QtWidgets.QLabel("综合 评分")
        ct.setStyleSheet(f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        h.addWidget(ct)
        vsep = QtWidgets.QFrame()
        vsep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        vsep.setStyleSheet("border:none;border-left:1px solid #45475a;background:transparent;")
        h.addWidget(vsep)
        self._score_kpi: dict = {}
        for key, txt, color in [
            ("alpha", "Alpha", _MAV), ("strategy", "Strategy", _BLUE),
            ("portfolio", "Portfolio", _GRN), ("execution", "Execution", _YLW),
            ("capital", "Capital", "#f5c2e7"), ("improvement", "Improve", _GRN),
        ]:
            cell = QtWidgets.QWidget(); cell.setStyleSheet("background:transparent;border:none;")
            cv = QtWidgets.QVBoxLayout(cell); cv.setContentsMargins(0,0,0,0); cv.setSpacing(2)
            lk = QtWidgets.QLabel(txt)
            lk.setStyleSheet(f"color:{_MUT};font-size:9px;border:none;background:transparent;")
            lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel("--")
            lv.setStyleSheet(
                f"color:{color};font-size:13px;font-weight:bold;"
                f"border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv)
            self._score_kpi[key] = lv; h.addWidget(cell)
        h.addStretch(); return w

    def _build_weights_display(self):
        grp = QtWidgets.QGroupBox("Weight Distribution")
        grp.setStyleSheet(
            f"QGroupBox{{color:{_MAV};border:1px solid {_BORDER};"
            f"border-radius:4px;margin-top:8px;font-size:11px;background:{_DARK};}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}")
        vb = QtWidgets.QVBoxLayout(grp); vb.setContentsMargins(10, 14, 10, 10)
        self._weights_text = QtWidgets.QPlainTextEdit()
        self._weights_text.setReadOnly(True); self._weights_text.setFixedHeight(160)
        self._weights_text.setFont(QtGui.QFont("Consolas", 10))
        self._weights_text.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_GRN};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        self._weights_text.setPlainText("  Run optimization to see weight distribution")
        vb.addWidget(self._weights_text); return grp

    def _build_history_table(self):
        w = QtWidgets.QWidget(); w.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(w); vb.setContentsMargins(0, 0, 0, 0); vb.setSpacing(4)
        vb.addWidget(_lbl("Optimization History",
                          f"color:{_MAV};font-size:11px;font-weight:bold;border:none;"))
        cols = ["Run ID", "Mode", "Init", "Final", "Gain", "Iter", "Conv", "Time"]
        self._tbl = QtWidgets.QTableWidget(0, len(cols))
        self._tbl.setHorizontalHeaderLabels(cols)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.setStyleSheet(_TBL)
        vb.addWidget(self._tbl); return w

    def _parse_scores(self, text: str) -> list[float]:
        try:    return [float(x.strip()) for x in text.split(",") if x.strip()]
        except: return []

    def _on_optimize(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected."); return
        a_sc = self._parse_scores(self._alpha_sc.text())
        s_sc = self._parse_scores(self._strat_sc.text())
        p_sc = self._parse_scores(self._port_sc.text())
        mode = self._mode_combo.currentData()
        self._engine.set_optimization_mode(mode)
        if a_sc: self._engine.update_optimizer_scores(alpha_scores=a_sc)
        if s_sc: self._engine.update_optimizer_scores(strategy_scores=s_sc)
        if p_sc: self._engine.update_optimizer_scores(portfolio_scores=p_sc)
        try:
            result = self._engine.run_optimization(
                n_alpha=self._n_alpha.value(), n_strategy=self._n_strategy.value(),
                n_asset=self._n_asset.value(), lr=self._lr.value(),
                n_iter=self._n_iter.value())
            self._fill(result)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _on_risk_parity(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Engine not connected."); return
        import random
        n_s = self._n_strategy.value(); n_a = self._n_asset.value()
        s_vols = [0.1 + random.random() * 0.2 for _ in range(n_s)]
        a_vols = [0.05 + random.random() * 0.15 for _ in range(n_a)]
        try:
            state = self._engine.run_risk_parity(s_vols, a_vols)
            self._fill_state(state)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _fill(self, result):
        s = result.final_score
        c = _GRN if s >= 70 else (_YLW if s >= 50 else _RED)
        self._comp_lbl.setText(f"{s:.0f}")
        self._comp_lbl.setStyleSheet(
            f"color:{c};font-size:38px;font-weight:bold;border:none;background:transparent;")
        st = result.state
        self._score_kpi["alpha"].setText(f"{st.alpha_score:.1f}")
        self._score_kpi["strategy"].setText(f"{st.strategy_score:.1f}")
        self._score_kpi["portfolio"].setText(f"{st.portfolio_score:.1f}")
        self._score_kpi["execution"].setText(f"{st.execution_score:.1f}")
        self._score_kpi["capital"].setText(f"{st.capital_score:.1f}")
        imp = result.improvement
        self._score_kpi["improvement"].setText(f"{imp:+.2f}")
        self._score_kpi["improvement"].setStyleSheet(
            f"color:{'#a6e3a1' if imp >= 0 else '#f38ba8'};"
            f"font-size:13px;font-weight:bold;border:none;background:transparent;")
        self._fill_weights(st)
        row = self._tbl.rowCount(); self._tbl.insertRow(row)
        cells = [result.run_id[-8:], result.mode.value,
                 f"{result.initial_score:.1f}", f"{result.final_score:.1f}",
                 f"{result.improvement:+.2f}", str(result.n_iterations),
                 "Y" if result.converged else "N", str(result.completed_at)[:16]]
        for col, txt in enumerate(cells):
            it = QtWidgets.QTableWidgetItem(txt)
            it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if col == 4:
                it.setForeground(
                    QtGui.QColor(_GRN if result.improvement >= 0 else _RED))
            elif col == 6:
                it.setForeground(QtGui.QColor(_GRN if result.converged else _YLW))
            self._tbl.setItem(row, col, it)
        self._tbl.scrollToBottom()

    def _fill_state(self, state):
        s = state.composite_score
        c = _GRN if s >= 70 else (_YLW if s >= 50 else _RED)
        self._comp_lbl.setText(f"{s:.0f}")
        self._comp_lbl.setStyleSheet(
            f"color:{c};font-size:38px;font-weight:bold;border:none;background:transparent;")
        for k, v in [("alpha", state.alpha_score), ("strategy", state.strategy_score),
                     ("portfolio", state.portfolio_score), ("execution", state.execution_score),
                     ("capital", state.capital_score)]:
            self._score_kpi[k].setText(f"{v:.1f}")
        self._fill_weights(state)

    def _fill_weights(self, state):
        def _bar(weights, ids):
            return [f"  {wid:<8} {w:.4f}  " + "#" * int(w * 30)
                    for wid, w in zip(ids, weights)]
        n_a = len(state.alpha_weights); n_s = len(state.strategy_allocs)
        n_p = min(5, len(state.portfolio_weights))
        a_ids = state.alpha_ids or [f"A{i}" for i in range(n_a)]
        s_ids = state.strategy_ids or [f"S{i}" for i in range(n_s)]
        p_ids = (state.asset_ids or [f"P{i}" for i in range(n_p)])[:n_p]
        lines = (["  === Alpha Weights ==="] + _bar(state.alpha_weights, a_ids)
                 + ["", "  === Strategy Allocs ==="] + _bar(state.strategy_allocs, s_ids)
                 + ["", "  === Portfolio Weights (top 5) ==="]
                 + _bar(state.portfolio_weights[:n_p], p_ids))
        self._weights_text.setPlainText("\n".join(lines))

    def refresh(self):
        if self._engine is None: return
        state = self._engine.get_cross_module_state()
        if state and state.iterations > 0:
            self._fill_state(state)
