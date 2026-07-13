"""
global_portfolio_intelligence/ui/objective_tab.py  (Phase 2)

ObjectiveTab — 统一目标函数监控面板。

布局：
  左栏  — 权重配置 + 模式选择
  右上  — 目标函数 KPI 卡片
  右中  — 六分量贡献条形图（ASCII）
  右下  — 多目标评分仪表盘 + 历史趋势
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import OptimizationMode
from ..model.objective_model import ObjectiveConfig, ObjectiveState

_BG    = "#1e1e2e"; _DARK  = "#181825"; _BORDER= "#45475a"; _FG= "#cdd6f4"
_MUT   = "#6c7086"; _BLUE  = "#89b4fa"; _GRN   = "#a6e3a1"; _YLW= "#f9e2af"
_RED   = "#f38ba8"; _MAV   = "#cba6f7"; _HEAD  = "#313244"; _PNK= "#f5c2e7"
_INPUT = (f"QDoubleSpinBox,QComboBox{{background:{_HEAD};color:{_FG};"
          f"border:1px solid {_BORDER};border-radius:3px;padding:3px 6px;font-size:11px;}}"
          f"QComboBox::drop-down{{border:none;}}")
_LLBL  = f"color:{_MUT};font-size:11px;border:none;background:transparent;"

def _lbl(t, s=""): w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w
def _sep():
    s = QtWidgets.QFrame(); s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};background:transparent;")
    return s


class ObjectiveTab(QtWidgets.QWidget):
    """统一目标函数监控面板（Phase 2）。"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine): self._engine = engine

    def _init_ui(self):
        self.setStyleSheet(f"background:{_BG};color:{_FG};")
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(10,10,10,10); h.setSpacing(10)
        h.addWidget(self._build_left(), stretch=0)
        h.addWidget(self._build_right(), stretch=1)

    def _build_left(self):
        panel = QtWidgets.QWidget(); panel.setFixedWidth(240)
        panel.setStyleSheet(f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel); vb.setContentsMargins(12,14,12,14); vb.setSpacing(10)
        vb.addWidget(_lbl("目标函数配置", f"color:{_MAV};font-weight:bold;font-size:12px;border:none;"))
        vb.addWidget(_sep())

        fm0 = QtWidgets.QFormLayout(); fm0.setContentsMargins(0,0,0,0); fm0.setVerticalSpacing(8)
        fm0.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._mode_combo = QtWidgets.QComboBox()
        for m in OptimizationMode: self._mode_combo.addItem(m.value.capitalize(), m)
        self._mode_combo.setStyleSheet(_INPUT)
        fm0.addRow(_lbl("优化模式：",_LLBL), self._mode_combo)
        vb.addLayout(fm0); vb.addWidget(_sep())

        vb.addWidget(_lbl("一阶目标权重", f"color:{_MUT};font-size:10px;border:none;"))
        fm = QtWidgets.QFormLayout(); fm.setContentsMargins(0,0,0,0); fm.setVerticalSpacing(6)
        fm.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._w: dict = {}
        for key, label, default in [
            ("return","Return", 0.30),("risk","Risk", 0.25),
            ("cost","Cost", 0.15),("turnover","Turnover", 0.10),
            ("alpha","Alpha", 0.10),("execution","Execution", 0.10),
        ]:
            sp = QtWidgets.QDoubleSpinBox()
            sp.setRange(0,1); sp.setValue(default); sp.setSingleStep(0.05)
            sp.setDecimals(2); sp.setStyleSheet(_INPUT); self._w[key] = sp
            fm.addRow(_lbl(f"{label}：", _LLBL), sp)
        vb.addLayout(fm); vb.addWidget(_sep())

        vb.addWidget(_lbl("系统输入（模拟）", f"color:{_MUT};font-size:10px;border:none;"))
        fm2 = QtWidgets.QFormLayout(); fm2.setContentsMargins(0,0,0,0); fm2.setVerticalSpacing(6)
        fm2.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self._inp: dict = {}
        for key, label, default in [
            ("expected_return","预期收益",0.6),("risk","风险水平",0.3),
            ("cost","成本",0.2),("turnover","换手率",0.2),
            ("alpha_quality","Alpha质量",0.6),("execution_efficiency","执行效率",0.75),
        ]:
            sp = QtWidgets.QDoubleSpinBox()
            sp.setRange(0,1); sp.setValue(default); sp.setSingleStep(0.05)
            sp.setDecimals(2); sp.setStyleSheet(_INPUT); self._inp[key] = sp
            fm2.addRow(_lbl(f"{label}：", _LLBL), sp)
        vb.addLayout(fm2); vb.addStretch()

        btn = QtWidgets.QPushButton(">> 计算目标函数")
        btn.setStyleSheet(f"QPushButton{{background:{_BLUE};color:#1e1e2e;font-weight:bold;border:none;border-radius:4px;padding:8px;font-size:12px;}}QPushButton:hover{{background:#74c7ec;}}")
        btn.clicked.connect(self._on_compute); vb.addWidget(btn)
        return panel

    def _build_right(self):
        panel = QtWidgets.QWidget(); panel.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(panel); vb.setContentsMargins(0,0,0,0); vb.setSpacing(8)
        vb.addWidget(self._build_kpi_bar())
        vb.addWidget(self._build_component_chart())
        vb.addWidget(self._build_multi_obj_bar())
        vb.addWidget(self._build_history_table())
        return panel

    def _build_kpi_bar(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w); h.setContentsMargins(16,10,16,10); h.setSpacing(24)
        self._kpi: dict = {}
        self._score_lbl = QtWidgets.QLabel("--")
        self._score_lbl.setStyleSheet(f"color:{_BLUE};font-size:40px;font-weight:bold;border:none;background:transparent;")
        self._score_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._score_lbl.setFixedWidth(90); h.addWidget(self._score_lbl)
        stxt = QtWidgets.QLabel("系统\n得分"); stxt.setStyleSheet(f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        h.addWidget(stxt)
        vsep = QtWidgets.QFrame(); vsep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        vsep.setStyleSheet(f"border:none;border-left:1px solid {_BORDER};background:transparent;"); h.addWidget(vsep)
        for key, txt in [("objective","目标函数值"),("composite","多目标综合"),
                          ("mode","优化模式"),("iteration","计算次数")]:
            cell = QtWidgets.QWidget(); cell.setStyleSheet("background:transparent;border:none;")
            cv = QtWidgets.QVBoxLayout(cell); cv.setContentsMargins(0,0,0,0); cv.setSpacing(2)
            lk = QtWidgets.QLabel(txt); lk.setStyleSheet(f"color:{_MUT};font-size:9px;border:none;background:transparent;"); lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel("--"); lv.setStyleSheet(f"color:{_FG};font-size:13px;font-weight:bold;border:none;background:transparent;"); lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv); self._kpi[key] = lv; h.addWidget(cell)
        h.addStretch(); return w

    def _build_component_chart(self):
        grp = QtWidgets.QGroupBox("目标分量贡献  Component Contributions")
        grp.setStyleSheet(f"QGroupBox{{color:{_MAV};border:1px solid {_BORDER};border-radius:4px;margin-top:8px;font-size:11px;background:{_DARK};}}QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}")
        vb = QtWidgets.QVBoxLayout(grp); vb.setContentsMargins(10,14,10,10)
        self._comp_text = QtWidgets.QPlainTextEdit()
        self._comp_text.setReadOnly(True); self._comp_text.setFixedHeight(130)
        self._comp_text.setFont(QtGui.QFont("Consolas", 10))
        self._comp_text.setStyleSheet(f"QPlainTextEdit{{background:{_BG};color:{_GRN};border:1px solid {_BORDER};border-radius:3px;}}")
        self._comp_text.setPlainText("  点击「计算目标函数」查看分量贡献")
        vb.addWidget(self._comp_text); return grp

    def _build_multi_obj_bar(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w); h.setContentsMargins(16,10,16,10); h.setSpacing(24)
        self._multi_kpi: dict = {}
        for key, txt, color in [("sharpe","Sharpe评分",_BLUE),("drawdown","回撤评分",_GRN),
                                  ("capacity","容量评分",_YLW),("stability","稳定性",_MAV)]:
            cell = QtWidgets.QWidget(); cell.setStyleSheet("background:transparent;border:none;")
            cv = QtWidgets.QVBoxLayout(cell); cv.setContentsMargins(0,0,0,0); cv.setSpacing(2)
            lk = QtWidgets.QLabel(txt); lk.setStyleSheet(f"color:{_MUT};font-size:9px;border:none;background:transparent;"); lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel("--"); lv.setStyleSheet(f"color:{color};font-size:15px;font-weight:bold;border:none;background:transparent;"); lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv); self._multi_kpi[key] = lv; h.addWidget(cell)
        h.addStretch(); return w

    def _build_history_table(self):
        w = QtWidgets.QWidget(); w.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(w); vb.setContentsMargins(0,0,0,0); vb.setSpacing(4)
        vb.addWidget(_lbl("历史计算记录", f"color:{_MAV};font-size:11px;font-weight:bold;border:none;"))
        cols = ["#","模式","目标值","系统分","Sharpe","回撤","容量","稳定性","多目标","时间"]
        self._tbl = QtWidgets.QTableWidget(0, len(cols)); self._tbl.setHorizontalHeaderLabels(cols)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.setStyleSheet(f"QTableWidget{{background:{_DARK};color:{_FG};border:1px solid {_BORDER};gridline-color:{_BORDER};font-size:11px;}}QTableWidget::item{{padding:3px 6px;}}QTableWidget::item:alternate{{background:#181825;}}QTableWidget::item:selected{{background:#45475a;}}QHeaderView::section{{background:{_HEAD};color:{_MUT};border:none;border-bottom:1px solid {_BORDER};padding:4px 6px;font-size:10px;}}")
        vb.addWidget(self._tbl); return w

    def _on_compute(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "引擎未就绪", "Engine 未连接。"); return
        inputs = {k: sp.value() for k, sp in self._inp.items()}
        from ..model.objective_model import ObjectiveConfig
        cfg = ObjectiveConfig(
            mode=self._mode_combo.currentData(),
            w_return=self._w["return"].value(), w_risk=self._w["risk"].value(),
            w_cost=self._w["cost"].value(),     w_turnover=self._w["turnover"].value(),
            w_alpha=self._w["alpha"].value(),   w_execution=self._w["execution"].value(),
        )
        self._engine.set_objective_config(cfg)
        try:
            state = self._engine.update_objective_inputs(inputs)
            self._fill(state)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "计算失败", str(e))

    def _fill(self, state):
        s = state.score
        c = _GRN if s >= 70 else (_YLW if s >= 45 else _RED)
        self._score_lbl.setText(f"{s:.0f}")
        self._score_lbl.setStyleSheet(f"color:{c};font-size:40px;font-weight:bold;border:none;background:transparent;")
        self._kpi["objective"].setText(f"{state.objective:.4f}")
        self._kpi["composite"].setText(f"{state.multi_objective.composite:.1f}")
        self._kpi["mode"].setText(state.config.mode.value)
        self._kpi["iteration"].setText(str(state.iteration))
        self._multi_kpi["sharpe"].setText(f"{state.multi_objective.sharpe_score:.1f}")
        self._multi_kpi["drawdown"].setText(f"{state.multi_objective.drawdown_score:.1f}")
        self._multi_kpi["capacity"].setText(f"{state.multi_objective.capacity_score:.1f}")
        self._multi_kpi["stability"].setText(f"{state.multi_objective.stability_score:.1f}")
        comp = state.components
        lines = ["  Component    Contribution  Bar"]
        max_abs = max(abs(v) for v in comp.values()) if comp else 1e-9
        for k, v in comp.items():
            bar = ("+" if v >= 0 else "-") * int(abs(v) / max_abs * 20)
            lines.append(f"  {k:<12}  {v:+.4f}      {bar}")
        self._comp_text.setPlainText("\n".join(lines))
        row = self._tbl.rowCount(); self._tbl.insertRow(row)
        mo = state.multi_objective
        cells = [str(state.iteration), state.config.mode.value,
                 f"{state.objective:.4f}", f"{state.score:.1f}",
                 f"{mo.sharpe_score:.1f}", f"{mo.drawdown_score:.1f}",
                 f"{mo.capacity_score:.1f}", f"{mo.stability_score:.1f}",
                 f"{mo.composite:.1f}", str(state.updated_at)[:16]]
        for col, txt in enumerate(cells):
            it = QtWidgets.QTableWidgetItem(txt)
            it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if col == 3:
                sc = _GRN if state.score >= 70 else (_YLW if state.score >= 45 else _RED)
                it.setForeground(QtGui.QColor(sc))
            self._tbl.setItem(row, col, it)
        self._tbl.scrollToBottom()

    def refresh(self):
        if self._engine is None: return
        state = self._engine.get_objective_state()
        if state and state.iteration > 0:
            self._fill(state)