"""
capital_allocation_ai/ui/allocation_tab.py  (Phase 3)

AllocationTab — 资金分配面板。

布局：
  顶部：5 个 KPI 卡片（总资金 / 活跃Alpha数 / 集中度HHI / 有效N / 换手率）
  中部左：分配比例表（可排序，含流向标识）
  中部右：资金流向信号列表
  底部：操作栏（计算分配 / 刷新）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_MAV      = "#cba6f7"
_ORG      = "#fab387"
_CYN      = "#89dceb"

_FLOW_COLOR = {
    "increase": _GRN,
    "decrease": _RED,
    "transfer": _YLW,
    "hold":     _MUT,
}

_FLOW_ICON = {
    "increase": "▲",
    "decrease": "▼",
    "transfer": "⇄",
    "hold":     "─",
}

_ALLOC_COLS = [
    ("排名",        50),
    ("Alpha ID",   110),
    ("资本评分",     80),
    ("分配比例",     80),
    ("分配金额",    100),
    ("上期比例",     80),
    ("变化 Δ",      75),
    ("流向",         65),
    ("流动金额",    100),
    ("状态",         70),
]

_SIGNAL_COLS = [
    ("信号 ID",     100),
    ("Alpha",      100),
    ("方向",         60),
    ("目标比例",     80),
    ("目标金额",    100),
    ("变化金额",    100),
    ("紧急度",       65),
    ("原因",        180),
]


def _item(text, color=_FG, align=QtCore.Qt.AlignmentFlag.AlignCenter):
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(align)
    it.setForeground(QtGui.QColor(color))
    return it


class _KpiCard(QtWidgets.QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(66)
        self.setStyleSheet(
            f"background: #11111b; border-radius: 6px;"
            f" border: 1px solid {_BORDER};"
        )
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(12, 6, 12, 6)
        v.setSpacing(2)
        self._lt = QtWidgets.QLabel(title)
        self._lt.setStyleSheet(f"color: {_MUT}; font-size: 10px; border: none;")
        self._lv = QtWidgets.QLabel("---")
        self._lv.setStyleSheet(
            f"color: {_FG}; font-size: 18px; font-weight: bold; border: none;")
        v.addWidget(self._lt)
        v.addWidget(self._lv)

    def update(self, value: str, color: str = _FG) -> None:
        self._lv.setText(value)
        self._lv.setStyleSheet(
            f"color: {color}; font-size: 18px;"
            f" font-weight: bold; border: none;")


class AllocationTab(QtWidgets.QWidget):
    """资金分配面板（Phase 3）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_kpi_bar())
        root.addWidget(self._build_main_area(), stretch=1)
        root.addWidget(self._build_action_bar())

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setFixedHeight(82)
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        self._kpi_capital  = _KpiCard("总资金  Total Capital")
        self._kpi_active   = _KpiCard("活跃 Alpha  Active")
        self._kpi_hhi      = _KpiCard("集中度 HHI")
        self._kpi_eff_n    = _KpiCard("有效 Alpha 数  Eff-N")
        self._kpi_turnover = _KpiCard("换手率  Turnover")
        for c in (self._kpi_capital, self._kpi_active, self._kpi_hhi,
                  self._kpi_eff_n, self._kpi_turnover):
            h.addWidget(c, stretch=1)
        return w

    def _build_main_area(self) -> QtWidgets.QSplitter:
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_alloc_table())
        splitter.addWidget(self._build_signal_panel())
        splitter.setSizes([800, 400])
        return splitter

    def _build_alloc_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("资金分配明细  Capital Allocation Details")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._alloc_tbl = QtWidgets.QTableWidget(0, len(_ALLOC_COLS))
        self._alloc_tbl.setHorizontalHeaderLabels([c[0] for c in _ALLOC_COLS])
        for i, (_, w_) in enumerate(_ALLOC_COLS):
            self._alloc_tbl.setColumnWidth(i, w_)
        self._alloc_tbl.horizontalHeader().setStretchLastSection(True)
        self._alloc_tbl.horizontalHeader().setSortIndicatorShown(True)
        self._alloc_tbl.setSortingEnabled(True)
        self._alloc_tbl.verticalHeader().setVisible(False)
        self._alloc_tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._alloc_tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._alloc_tbl.setStyleSheet("font-size: 11px;")
        v.addWidget(self._alloc_tbl, stretch=1)
        return w

    def _build_signal_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("资金流动信号  Capital Flow Signals")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._signal_tbl = QtWidgets.QTableWidget(0, len(_SIGNAL_COLS))
        self._signal_tbl.setHorizontalHeaderLabels([c[0] for c in _SIGNAL_COLS])
        for i, (_, w_) in enumerate(_SIGNAL_COLS):
            self._signal_tbl.setColumnWidth(i, w_)
        self._signal_tbl.horizontalHeader().setStretchLastSection(True)
        self._signal_tbl.verticalHeader().setVisible(False)
        self._signal_tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._signal_tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._signal_tbl.setStyleSheet("font-size: 11px;")
        v.addWidget(self._signal_tbl, stretch=1)
        return w

    def _build_action_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(8)

        def _btn(label, color, slot):
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color};"
                f" border: 1px solid {color}; border-radius: 3px;"
                f" padding: 4px 14px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            b.clicked.connect(slot)
            return b

        h.addWidget(_btn("★ 计算分配  Calculate", _MAV, self._on_calculate))
        h.addWidget(_btn("动态调整  Adjust", _CYN, self._on_adjust))
        h.addStretch()
        h.addWidget(QtWidgets.QLabel("最大比例:"))
        self._max_spin = QtWidgets.QDoubleSpinBox()
        self._max_spin.setRange(0.05, 1.0)
        self._max_spin.setSingleStep(0.05)
        self._max_spin.setValue(0.30)
        self._max_spin.setDecimals(2)
        self._max_spin.setFixedWidth(70)
        self._max_spin.setStyleSheet(
            f"background: #11111b; color: {_FG}; border: 1px solid {_BORDER};"
            f" border-radius: 3px; padding: 2px;"
        )
        h.addWidget(self._max_spin)
        h.addWidget(_btn("刷新 Refresh", _MUT, self.refresh))
        return bar

    def refresh(self) -> None:
        if self._engine is None:
            return
        snap = self._engine.allocation_engine.get_latest_snapshot()
        if snap is None:
            return
        self._update_kpis(snap)
        self._render_alloc_table(snap)
        self._render_signal_table(snap)

    def _on_calculate(self) -> None:
        if self._engine is None:
            QtWidgets.QMessageBox.warning(
                self, "未初始化", "请先启动引擎。")
            return
        self._engine.calculate_allocation(max_ratio=self._max_spin.value())
        self.refresh()

    def _on_adjust(self) -> None:
        if self._engine is None:
            return
        snap = self._engine.allocation_engine.get_latest_snapshot()
        if snap is None:
            QtWidgets.QMessageBox.information(self, "提示", "请先执行「计算分配」。")
            return
        scores = {k: v.capital_score for k, v in snap.allocations.items()}
        self._engine.allocation_engine.adjust_by_score_change(
            scores, snap.total_capital)
        self.refresh()

    def _update_kpis(self, snap) -> None:
        cap = snap.total_capital
        self._kpi_capital.update(
            f"¥{cap/1_000_000:.1f}M" if cap >= 1_000_000 else f"¥{cap:,.0f}",
            _MAV,
        )
        self._kpi_active.update(str(snap.n_active), _GRN)
        hhi = snap.concentration
        self._kpi_hhi.update(
            f"{hhi:.4f}",
            _GRN if hhi < 0.1 else (_YLW if hhi < 0.2 else _RED),
        )
        self._kpi_eff_n.update(f"{snap.effective_n:.1f}", _BLU)
        to = snap.turnover
        self._kpi_turnover.update(
            f"{to:.3f}",
            _GRN if to < 0.1 else (_YLW if to < 0.3 else _RED),
        )

    def _render_alloc_table(self, snap) -> None:
        self._alloc_tbl.setSortingEnabled(False)
        self._alloc_tbl.setRowCount(0)
        for rank, alloc in enumerate(
            sorted(snap.allocations.values(),
                   key=lambda a: a.ratio, reverse=True),
            start=1,
        ):
            row = self._alloc_tbl.rowCount()
            self._alloc_tbl.insertRow(row)
            flow = alloc.flow_direction.value
            fc   = _FLOW_COLOR.get(flow, _MUT)
            icon = _FLOW_ICON.get(flow, "─")
            ratio_c = _GRN if alloc.ratio > 0.1 else (
                _YLW if alloc.ratio > 0.02 else _MUT)
            delta_c = (_GRN if alloc.delta_ratio > 0
                       else _RED if alloc.delta_ratio < 0 else _MUT)
            score_c = (_GRN if alloc.capital_score > 0.5
                       else _YLW if alloc.capital_score > 0.3 else _RED)
            self._alloc_tbl.setItem(row, 0, _item(rank,                             _MUT))
            self._alloc_tbl.setItem(row, 1, _item(alloc.alpha_id,                   _MAV))
            self._alloc_tbl.setItem(row, 2, _item(f"{alloc.capital_score:.4f}",     score_c))
            self._alloc_tbl.setItem(row, 3, _item(f"{alloc.ratio:.4f}",             ratio_c))
            self._alloc_tbl.setItem(row, 4, _item(f"¥{alloc.allocated:,.0f}",       _FG))
            self._alloc_tbl.setItem(row, 5, _item(f"{alloc.prev_ratio:.4f}",        _MUT))
            self._alloc_tbl.setItem(row, 6, _item(f"{alloc.delta_ratio:+.4f}",      delta_c))
            self._alloc_tbl.setItem(row, 7, _item(f"{icon} {flow}",                 fc))
            self._alloc_tbl.setItem(row, 8, _item(f"¥{alloc.flow_amount:+,.0f}",    fc))
            self._alloc_tbl.setItem(
                row, 9,
                _item(alloc.status.value,
                      _GRN if alloc.ratio > 1e-8 else _MUT))
        self._alloc_tbl.setSortingEnabled(True)

    def _render_signal_table(self, snap) -> None:
        self._signal_tbl.setRowCount(0)
        urgency_color = {"high": _RED, "normal": _YLW, "low": _MUT}
        for sig in snap.signals:
            row = self._signal_tbl.rowCount()
            self._signal_tbl.insertRow(row)
            flow = sig.direction.value
            fc   = _FLOW_COLOR.get(flow, _MUT)
            icon = _FLOW_ICON.get(flow, "─")
            uc   = urgency_color.get(sig.urgency, _MUT)
            self._signal_tbl.setItem(row, 0, _item(sig.signal_id,                   _MUT))
            self._signal_tbl.setItem(row, 1, _item(sig.alpha_id,                    _MAV))
            self._signal_tbl.setItem(row, 2, _item(f"{icon} {flow}",                fc))
            self._signal_tbl.setItem(row, 3, _item(f"{sig.target_ratio:.4f}",       _FG))
            self._signal_tbl.setItem(row, 4, _item(f"¥{sig.target_amount:,.0f}",    _FG))
            self._signal_tbl.setItem(row, 5, _item(f"¥{sig.delta_amount:+,.0f}",    fc))
            self._signal_tbl.setItem(row, 6, _item(sig.urgency,                     uc))
            self._signal_tbl.setItem(
                row, 7,
                _item(sig.reason, _FG,
                      QtCore.Qt.AlignmentFlag.AlignLeft |
                      QtCore.Qt.AlignmentFlag.AlignVCenter))
