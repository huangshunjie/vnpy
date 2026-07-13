"""
execution_engine/ui/cost_tab.py

CostTab — 成本分析 Tab（Phase 3 实现）。

顶部：成本配置面板（手续费模式 / 冲击系数）
中部：成本汇总卡片（手续费 / 滑点 / 冲击 / 总成本 / 成本率）
底部：逐笔成本明细表格
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..engine.cost_engine import CostBreakdown, CostConfig, CostSummary, CommissionMode

_FG  = "#cdd6f4"
_MUT = "#6c7086"
_GRN = "#a6e3a1"
_RED = "#f38ba8"
_YLW = "#f9e2af"
_BLU = "#89b4fa"

_INPUT_STYLE = (
    "QDoubleSpinBox, QSpinBox, QComboBox {"
    " background: #313244; color: #cdd6f4; border: 1px solid #45475a;"
    " border-radius: 3px; padding: 2px 6px; font-size: 12px; }"
)

_COLS = [
    ("订单ID",    80),
    ("合约",     120),
    ("方向",      60),
    ("名义价值",  100),
    ("手续费",    90),
    ("滑点成本",  90),
    ("冲击成本",  90),
    ("总成本",    90),
    ("成本率",    80),
    ("净PnL影响", 90),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    item = QtWidgets.QTableWidgetItem(str(text))
    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    item.setForeground(QtGui.QColor(color))
    return item


class CostTab(QtWidgets.QWidget):
    """成本分析 Tab（Phase 3 实现）。"""

    config_changed = QtCore.Signal(object)   # CostConfig

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._breakdowns: list[CostBreakdown] = []
        self._init_ui()

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # 顶部：配置 + 汇总并排
        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(self._build_config_panel(), stretch=0)
        top.addWidget(self._build_summary_bar(),  stretch=1)
        root.addLayout(top)

        # 底部：明细表格
        root.addWidget(self._build_table(), stretch=1)

    # ------------------------------------------------------------------ #
    #  构建子区域
    # ------------------------------------------------------------------ #

    def _build_config_panel(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("成本配置")
        box.setFixedWidth(260)
        box.setStyleSheet(
            "QGroupBox { color: #cdd6f4; font-size: 12px; font-weight: bold;"
            " border: 1px solid #45475a; border-radius: 4px; margin-top: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; padding: 0 4px; }"
        )
        form = QtWidgets.QFormLayout(box)
        form.setContentsMargins(10, 16, 10, 10)
        form.setSpacing(7)
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        lbl_s = "color: #a6adc8; font-size: 11px;"

        self._cmb_commission = QtWidgets.QComboBox()
        self._cmb_commission.addItems([
            "按成交额(rate)", "每笔固定(fixed)", "每手固定(per_lot)"
        ])
        self._cmb_commission.setStyleSheet(_INPUT_STYLE)
        lbl = QtWidgets.QLabel("手续费模式：")
        lbl.setStyleSheet(lbl_s)
        form.addRow(lbl, self._cmb_commission)

        self._spn_rate = self._dbl(0.0, 0.01, 0.0003, 5)
        lbl2 = QtWidgets.QLabel("手续费率：")
        lbl2.setStyleSheet(lbl_s)
        form.addRow(lbl2, self._spn_rate)

        self._spn_fixed = self._dbl(0.0, 1000.0, 5.0, 2)
        lbl3 = QtWidgets.QLabel("固定费用：")
        lbl3.setStyleSheet(lbl_s)
        form.addRow(lbl3, self._spn_fixed)

        self._spn_impact = self._dbl(0.0, 5.0, 0.3, 3)
        lbl4 = QtWidgets.QLabel("冲击系数：")
        lbl4.setStyleSheet(lbl_s)
        form.addRow(lbl4, self._spn_impact)

        self._spn_daily_vol = self._dbl(1.0, 9999999.0, 10000.0, 0)
        lbl5 = QtWidgets.QLabel("日均成交量：")
        lbl5.setStyleSheet(lbl_s)
        form.addRow(lbl5, self._spn_daily_vol)

        self._spn_multiplier = self._dbl(0.01, 10000.0, 1.0, 2)
        lbl6 = QtWidgets.QLabel("合约乘数：")
        lbl6.setStyleSheet(lbl_s)
        form.addRow(lbl6, self._spn_multiplier)

        btn = QtWidgets.QPushButton("应用")
        btn.setStyleSheet(
            "QPushButton { background: #89b4fa; color: #1e1e2e; border-radius: 4px;"
            " padding: 5px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background: #b4befe; }"
        )
        btn.clicked.connect(self._apply_config)
        form.addRow(btn)
        return box

    def _build_summary_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setStyleSheet("background: #181825; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(bar)
        v.setContentsMargins(12, 8, 12, 8)
        v.setSpacing(8)

        # 第一行：金额
        row1 = QtWidgets.QHBoxLayout()
        row1.setSpacing(20)
        cards1 = [
            ("总手续费",   "0.0000", _BLU),
            ("总滑点成本", "0.0000", _YLW),
            ("总冲击成本", "0.0000", _RED),
            ("总成本",     "0.0000", _RED),
            ("总名义价值", "0.0000", _FG),
        ]
        self._sum_lbls: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in cards1:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._sum_lbls[name] = lv
            row1.addLayout(col)
        row1.addStretch()
        v.addLayout(row1)

        # 第二行：占比
        row2 = QtWidgets.QHBoxLayout()
        row2.setSpacing(20)
        cards2 = [
            ("平均成本率",  "—", _RED),
            ("手续费占比",  "—", _BLU),
            ("滑点占比",    "—", _YLW),
            ("冲击占比",    "—", _RED),
            ("总笔数",      "0", _FG),
        ]
        for name, val, color in cards2:
            col = QtWidgets.QVBoxLayout()
            col.setSpacing(1)
            ln = QtWidgets.QLabel(name)
            ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
            ln.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel(val)
            lv.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            col.addWidget(ln)
            col.addWidget(lv)
            self._sum_lbls[name] = lv
            row2.addLayout(col)
        row2.addStretch()
        v.addLayout(row2)
        return bar

    def _build_table(self) -> QtWidgets.QTableWidget:
        self._table = QtWidgets.QTableWidget(0, len(_COLS))
        self._table.setHorizontalHeaderLabels([c[0] for c in _COLS])
        for i, (_, w) in enumerate(_COLS):
            self._table.setColumnWidth(i, w)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setStyleSheet("font-size: 12px;")
        return self._table

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def add_breakdown(self, bd: CostBreakdown) -> None:
        """追加一条成本明细（实时模式）。"""
        self._breakdowns.append(bd)
        self._append_row(bd)

    def refresh_all(
        self,
        breakdowns: list[CostBreakdown],
        summary:    CostSummary | None = None,
    ) -> None:
        """全量刷新。"""
        self._table.setRowCount(0)
        self._breakdowns = list(breakdowns)
        for bd in breakdowns:
            self._append_row(bd)
        if summary:
            self.update_summary(summary)

    def update_summary(self, summary: CostSummary) -> None:
        """刷新汇总卡片。"""
        def fmt(v: float) -> str:
            return f"{v:.4f}"
        def pct(v: float) -> str:
            return f"{v:.2%}" if v else "—"

        self._sum_lbls["总手续费"  ].setText(fmt(summary.total_commission))
        self._sum_lbls["总滑点成本"].setText(fmt(summary.total_slippage))
        self._sum_lbls["总冲击成本"].setText(fmt(summary.total_impact))
        self._sum_lbls["总成本"    ].setText(fmt(summary.total_cost))
        self._sum_lbls["总名义价值"].setText(f"{summary.total_notional:.2f}")
        self._sum_lbls["平均成本率"].setText(pct(summary.avg_cost_pct))
        self._sum_lbls["手续费占比"].setText(pct(summary.commission_share))
        self._sum_lbls["滑点占比"  ].setText(pct(summary.slippage_share))
        self._sum_lbls["冲击占比"  ].setText(pct(summary.impact_share))
        self._sum_lbls["总笔数"    ].setText(str(summary.total_orders))

    def get_cost_config(self) -> CostConfig:
        idx_map = {
            0: CommissionMode.RATE_ON_NOTIONAL,
            1: CommissionMode.FIXED_PER_ORDER,
            2: CommissionMode.FIXED_PER_LOT,
        }
        return CostConfig(
            commission_mode      = idx_map.get(self._cmb_commission.currentIndex(),
                                               CommissionMode.RATE_ON_NOTIONAL),
            commission_rate      = self._spn_rate.value(),
            commission_fixed     = self._spn_fixed.value(),
            impact_factor        = self._spn_impact.value(),
            daily_volume         = self._spn_daily_vol.value(),
            contract_multiplier  = self._spn_multiplier.value(),
        )

    def clear(self) -> None:
        self._breakdowns.clear()
        self._table.setRowCount(0)

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _append_row(self, bd: CostBreakdown) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        dir_color = "#4fc3f7" if bd.direction == "LONG" else "#f38ba8"
        self._table.setItem(row, 0, _item(bd.order_id,                  _MUT))
        self._table.setItem(row, 1, _item(bd.symbol,                    _FG))
        self._table.setItem(row, 2, _item(bd.direction,                 dir_color))
        self._table.setItem(row, 3, _item(f"{bd.notional:.2f}",         _FG))
        self._table.setItem(row, 4, _item(f"{bd.commission:.4f}",       _BLU))
        self._table.setItem(row, 5, _item(f"{bd.slippage_cost:.4f}",    _YLW))
        self._table.setItem(row, 6, _item(f"{bd.impact_cost:.4f}",      _RED))
        self._table.setItem(row, 7, _item(f"{bd.total_cost:.4f}",       _RED))
        self._table.setItem(row, 8, _item(f"{bd.total_cost_pct:.4%}",   _RED))
        self._table.setItem(row, 9, _item(f"{-bd.total_cost:.4f}",      _GRN))
        self._table.scrollToBottom()

    def _apply_config(self) -> None:
        self.config_changed.emit(self.get_cost_config())

    @staticmethod
    def _dbl(lo, hi, val, dec) -> QtWidgets.QDoubleSpinBox:
        spn = QtWidgets.QDoubleSpinBox()
        spn.setRange(lo, hi)
        spn.setValue(val)
        spn.setDecimals(dec)
        spn.setSingleStep(10 ** (-dec) if dec > 0 else 1.0)
        spn.setStyleSheet(_INPUT_STYLE)
        return spn
