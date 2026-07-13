"""
execution_intelligence_ai/ui/slicing_tab.py  (Phase 2)

SlicingTab — 智能拆单可视化面板。
布局：左栏参数设置 | 右侧汇总KPI + 进度条 + 切片表格
"""
from __future__ import annotations
from datetime import datetime

from vnpy.trader.ui import QtCore, QtWidgets, QtGui

from ..constant import ExecutionStrategy
from ..model.slicing_model import SlicePlan, SlicingParams

_PANEL  = "#1e1e2e"
_DARK   = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_BLUE   = "#89b4fa"
_GRN    = "#a6e3a1"
_YLW    = "#f9e2af"
_RED    = "#f38ba8"
_MAV    = "#cba6f7"
_HEAD   = "#313244"

_HINTS = {
    ExecutionStrategy.TWAP:
        "TWAP：将总量均匀分配到 N 个时间切片。\n适合流动性稳定场景。",
    ExecutionStrategy.VWAP:
        "VWAP：按历史成交量分布加权拆单。\n无 volume_profile 时退化为 TWAP。",
    ExecutionStrategy.POV:
        "POV：占市场实时成交量的固定百分比参与。\n适合大单、冲击敏感场景。",
    ExecutionStrategy.ADAPTIVE:
        "Adaptive：实时波动率+流动性双因子调整切片量。\n高波动/低流动时自动减小切片。",
    ExecutionStrategy.MARKET:
        "Market：单片直接市价发送，不拆单。\n仅适合小单或极高紧迫度场景。",
    ExecutionStrategy.LIMIT:
        "Limit：单片以限价发送，不拆单。\n需提供 target_price。",
}

_INPUT = (
    f"QLineEdit,QSpinBox,QDoubleSpinBox,QComboBox{{"
    f"background:{_HEAD};color:{_FG};border:1px solid {_BORDER};"
    f"border-radius:3px;padding:3px 6px;font-size:11px;}}"
    f"QComboBox::drop-down{{border:none;}}"
)
_LLBL = f"color:{_MUT};font-size:11px;border:none;background:transparent;"


def _lbl(t, s=""): w=QtWidgets.QLabel(t); w.setStyleSheet(s); return w
def _sep():
    s=QtWidgets.QFrame(); s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};background:transparent;")
    return s


class SlicingTab(QtWidgets.QWidget):
    """智能拆单可视化面板 (Phase 2)。"""

    def __init__(self, engine=None, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._plan: SlicePlan | None = None
        self._init_ui()

    def set_engine(self, engine):
        self._engine = engine

    # ── UI ──────────────────────────────────────────────────────────
    def _init_ui(self):
        self.setStyleSheet(f"background:{_PANEL};color:{_FG};")
        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(10,10,10,10); h.setSpacing(10)
        h.addWidget(self._build_left(), stretch=0)
        h.addWidget(self._build_right(), stretch=1)

    def _build_left(self):
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(260)
        panel.setStyleSheet(f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(12,14,12,14); vb.setSpacing(10)

        vb.addWidget(_lbl("拆单参数设置", f"color:{_MAV};font-weight:bold;font-size:12px;border:none;"))
        vb.addWidget(_sep())

        fm = QtWidgets.QFormLayout()
        fm.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        fm.setVerticalSpacing(8); fm.setContentsMargins(0,0,0,0)

        self._eid = QtWidgets.QLineEdit(); self._eid.setReadOnly(True)
        self._eid.setPlaceholderText("auto-generated"); self._eid.setStyleSheet(_INPUT)
        fm.addRow(_lbl("执行ID：",_LLBL), self._eid)

        self._sym = QtWidgets.QLineEdit(); self._sym.setPlaceholderText("如 000001")
        self._sym.setStyleSheet(_INPUT)
        fm.addRow(_lbl("标的代码：",_LLBL), self._sym)

        self._dir = QtWidgets.QComboBox(); self._dir.addItems(["long（多）","short（空）"])
        self._dir.setStyleSheet(_INPUT)
        fm.addRow(_lbl("方向：",_LLBL), self._dir)

        self._vol = QtWidgets.QDoubleSpinBox()
        self._vol.setRange(1,1e9); self._vol.setValue(10000)
        self._vol.setDecimals(0); self._vol.setSingleStep(100); self._vol.setStyleSheet(_INPUT)
        fm.addRow(_lbl("总数量：",_LLBL), self._vol)

        self._strat = QtWidgets.QComboBox()
        for s in ExecutionStrategy: self._strat.addItem(s.value.upper(), s)
        self._strat.setStyleSheet(_INPUT)
        self._strat.currentIndexChanged.connect(self._update_hint)
        fm.addRow(_lbl("拆单策略：",_LLBL), self._strat)

        vb.addLayout(fm); vb.addWidget(_sep())

        # 高级参数
        grp = QtWidgets.QGroupBox("策略参数")
        grp.setStyleSheet(
            f"QGroupBox{{color:{_MUT};border:1px solid {_BORDER};border-radius:4px;"
            f"margin-top:6px;font-size:11px;background:transparent;}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:8px;padding:0 4px;}}")
        af = QtWidgets.QFormLayout(grp)
        af.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        af.setVerticalSpacing(6); af.setContentsMargins(8,12,8,8)

        self._nslc = QtWidgets.QSpinBox(); self._nslc.setRange(1,500)
        self._nslc.setValue(10); self._nslc.setStyleSheet(_INPUT)
        af.addRow(_lbl("切片数：",_LLBL), self._nslc)

        self._intv = QtWidgets.QSpinBox(); self._intv.setRange(1,3600)
        self._intv.setValue(60); self._intv.setSuffix(" 秒"); self._intv.setStyleSheet(_INPUT)
        af.addRow(_lbl("间隔：",_LLBL), self._intv)

        self._pov = QtWidgets.QDoubleSpinBox()
        self._pov.setRange(0.01,1.0); self._pov.setValue(0.10)
        self._pov.setSingleStep(0.01); self._pov.setDecimals(2); self._pov.setStyleSheet(_INPUT)
        af.addRow(_lbl("POV 率：",_LLBL), self._pov)

        vb.addWidget(grp)

        self._hint = QtWidgets.QLabel(); self._hint.setWordWrap(True)
        self._hint.setStyleSheet(f"color:{_MUT};font-size:10px;border:none;background:{_HEAD};border-radius:3px;padding:6px;")
        vb.addWidget(self._hint); vb.addStretch()

        btn = QtWidgets.QPushButton("▶  生成拆单计划")
        btn.setStyleSheet(
            f"QPushButton{{background:{_BLUE};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:8px;font-size:12px;}}"
            f"QPushButton:hover{{background:#74c7ec;}}")
        btn.clicked.connect(self._on_generate)
        vb.addWidget(btn)
        self._update_hint()
        return panel

    def _build_right(self):
        panel = QtWidgets.QWidget(); panel.setStyleSheet("background:transparent;")
        vb = QtWidgets.QVBoxLayout(panel); vb.setContentsMargins(0,0,0,0); vb.setSpacing(8)

        # KPI bar
        kbar = QtWidgets.QWidget()
        kbar.setStyleSheet(f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        kh = QtWidgets.QHBoxLayout(kbar); kh.setContentsMargins(12,8,12,8); kh.setSpacing(24)
        self._kpi: dict = {}
        for key, txt in [("strategy","策略"),("n_slices","切片数"),("total_vol","总数量"),
                          ("filled","已成交"),("fill_rate","成交率"),("created_at","创建时间")]:
            cell = QtWidgets.QWidget(); cell.setStyleSheet("background:transparent;border:none;")
            cv = QtWidgets.QVBoxLayout(cell); cv.setContentsMargins(0,0,0,0); cv.setSpacing(2)
            lk = QtWidgets.QLabel(txt)
            lk.setStyleSheet(f"color:{_MUT};font-size:9px;border:none;background:transparent;")
            lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel("--")
            lv.setStyleSheet(f"color:{_FG};font-size:13px;font-weight:bold;border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv); self._kpi[key]=lv; kh.addWidget(cell)
        kh.addStretch()
        rb = QtWidgets.QPushButton("刷新"); rb.setFixedWidth(60)
        rb.setStyleSheet(f"QPushButton{{background:transparent;color:{_MUT};border:1px solid {_BORDER};border-radius:3px;padding:4px;}}QPushButton:hover{{background:{_HEAD};}}")
        rb.clicked.connect(self.refresh); kh.addWidget(rb)
        vb.addWidget(kbar)

        # 进度条
        self._pbar = QtWidgets.QProgressBar(); self._pbar.setValue(0)
        self._pbar.setFormat("等待计划生成…"); self._pbar.setMinimumHeight(20)
        self._pbar.setStyleSheet(
            f"QProgressBar{{background:{_DARK};border:1px solid {_BORDER};border-radius:3px;color:{_FG};font-size:11px;text-align:center;}}"
            f"QProgressBar::chunk{{background:{_BLUE};border-radius:2px;}}")
        vb.addWidget(self._pbar)

        # 表格
        vb.addWidget(_lbl("切片计划明细", f"color:{_MAV};font-size:11px;font-weight:bold;border:none;"))
        cols = ["序号","计划时间","计划数量","已成交","成交率","目标价","成交价","滑点(bp)","状态"]
        self._tbl = QtWidgets.QTableWidget(0, len(cols))
        self._tbl.setHorizontalHeaderLabels(cols)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._tbl.horizontalHeader().setStretchLastSection(True)
        self._tbl.setStyleSheet(
            f"QTableWidget{{background:{_DARK};color:{_FG};border:1px solid {_BORDER};gridline-color:{_BORDER};font-size:11px;}}"
            f"QTableWidget::item{{padding:3px 6px;}}"
            f"QTableWidget::item:alternate{{background:#181825;}}"
            f"QTableWidget::item:selected{{background:#45475a;}}"
            f"QHeaderView::section{{background:{_HEAD};color:{_MUT};border:none;border-bottom:1px solid {_BORDER};padding:4px 6px;font-size:10px;}}")
        vb.addWidget(self._tbl)
        return panel

    # ── slots ────────────────────────────────────────────────────────
    def _update_hint(self):
        s = self._strat.currentData()
        if s: self._hint.setText(_HINTS.get(s,""))

    def _on_generate(self):
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self,"引擎未就绪","Engine 未连接，无法生成计划。"); return
        sym  = self._sym.text().strip() or "DEMO"
        dirn = "long" if self._dir.currentIndex()==0 else "short"
        vol  = self._vol.value()
        strat = self._strat.currentData()
        params = SlicingParams(
            strategy=strat, n_slices=self._nslc.value(),
            interval_seconds=self._intv.value(), pov_rate=self._pov.value())
        order = {"symbol":sym,"exchange":"SSE","direction":dirn,
                 "total_volume":vol,"start_dt":datetime.now()}
        try:
            plan = self._engine.process_order(order, params)
            self._plan = plan; self._eid.setText(plan.execution_id)
            self._fill_table(plan); self._fill_kpi(plan)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self,"生成失败",str(e))

    # ── fill ─────────────────────────────────────────────────────────
    def _fill_table(self, plan: SlicePlan):
        self._tbl.setRowCount(0); self._tbl.setRowCount(len(plan.slices))
        sc = {"pending":_MUT,"submitted":_YLW,"partial":_YLW,
              "filled":_GRN,"cancelled":_RED,"failed":_RED}
        for row, s in enumerate(plan.slices):
            cells = [str(s.sequence), str(s.scheduled_at)[:19],
                     f"{s.volume:,.0f}", f"{s.filled_volume:,.0f}",
                     f"{s.fill_rate:.1%}",
                     f"{s.target_price:.4f}" if s.target_price else "--",
                     f"{s.filled_price:.4f}" if s.filled_price else "--",
                     f"{s.slippage_bps:.2f}" if s.slippage_bps else "--",
                     s.status.value]
            for col, txt in enumerate(cells):
                it = QtWidgets.QTableWidgetItem(txt)
                it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if col == len(cells)-1:
                    it.setForeground(QtGui.QColor(sc.get(s.status.value, _FG)))
                self._tbl.setItem(row, col, it)
        n = len(plan.slices)
        fn = sum(1 for s in plan.slices if s.status.value=="filled")
        pct = int(fn/n*100) if n>0 else 0
        self._pbar.setValue(pct); self._pbar.setFormat(f"切片进度  {fn}/{n}  ({pct}%)")

    def _fill_kpi(self, plan: SlicePlan):
        self._kpi["strategy"].setText(plan.params.strategy.value.upper())
        self._kpi["n_slices"].setText(str(plan.n_slices))
        self._kpi["total_vol"].setText(f"{plan.total_volume:,.0f}")
        self._kpi["filled"].setText(f"{plan.total_filled_volume:,.0f}")
        self._kpi["fill_rate"].setText(f"{plan.overall_fill_rate:.1%}")
        self._kpi["created_at"].setText(str(plan.created_at)[:16])

    def refresh(self):
        if self._plan is None: return
        if self._engine is not None:
            p = self._engine.get_slice_plan(self._plan.execution_id)
            if p: self._plan = p
        self._fill_table(self._plan); self._fill_kpi(self._plan)
