"""
capital_allocation_ai/ui/risk_budget_tab.py  (Phase 4)

RiskBudgetTab — 风险预算面板。

布局：
  顶部：5 个 KPI（组合VaR / 组合DD / 组合Beta / 违规Alpha数 / 风险信号数）
  中部左：Alpha 风险预算明细表
  中部右：风险调整信号列表
  底部：操作栏（评估风险 / 更新上限 / 刷新）
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
_CYN      = "#89dceb"

_BUDGET_COLS = [
    ("Alpha ID",   110), ("风险类型", 80), ("当前值", 75),
    ("预算上限",    75),  ("使用率",   70), ("剩余空间", 75),
    ("权重",        65),  ("状态",     70), ("严重度", 70),
]
_SIGNAL_COLS = [
    ("信号 ID",   100), ("Alpha",   100), ("违规类型", 80),
    ("当前比例",   80),  ("建议比例",  80), ("调整 Δ",  75),
    ("紧急度",     65),  ("原因",    200),
]


def _item(text, color=_FG, align=QtCore.Qt.AlignmentFlag.AlignCenter):
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(align)
    it.setForeground(QtGui.QColor(color))
    return it


def _util_color(util: float) -> str:
    if util >= 1.0: return _RED
    if util >= 0.8: return _YLW
    return _GRN


class _KpiCard(QtWidgets.QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(66)
        self.setStyleSheet(
            f"background: #11111b; border-radius: 6px;"
            f" border: 1px solid {_BORDER};")
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
            f"color: {color}; font-size: 18px; font-weight: bold; border: none;")


class RiskBudgetTab(QtWidgets.QWidget):
    """风险预算面板（Phase 4）。"""

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
        self._kpi_var    = _KpiCard("组合 VaR 95%（日）")
        self._kpi_dd     = _KpiCard("组合回撤  Port DD")
        self._kpi_beta   = _KpiCard("组合 Beta")
        self._kpi_breach = _KpiCard("违规 Alpha 数  Breached")
        self._kpi_sigs   = _KpiCard("风险信号数  Signals")
        for c in (self._kpi_var, self._kpi_dd, self._kpi_beta,
                  self._kpi_breach, self._kpi_sigs):
            h.addWidget(c, stretch=1)
        return w

    def _build_main_area(self) -> QtWidgets.QSplitter:
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_budget_table())
        splitter.addWidget(self._build_signal_panel())
        splitter.setSizes([800, 420])
        return splitter

    def _build_budget_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("Alpha 风险预算明细  Risk Budget Details")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._budget_tbl = QtWidgets.QTableWidget(0, len(_BUDGET_COLS))
        self._budget_tbl.setHorizontalHeaderLabels([c[0] for c in _BUDGET_COLS])
        for i, (_, w_) in enumerate(_BUDGET_COLS):
            self._budget_tbl.setColumnWidth(i, w_)
        self._budget_tbl.horizontalHeader().setStretchLastSection(True)
        self._budget_tbl.horizontalHeader().setSortIndicatorShown(True)
        self._budget_tbl.setSortingEnabled(True)
        self._budget_tbl.verticalHeader().setVisible(False)
        self._budget_tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._budget_tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._budget_tbl.setStyleSheet("font-size: 11px;")
        v.addWidget(self._budget_tbl, stretch=1)
        return w

    def _build_signal_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("风险调整信号  Risk Adjust Signals")
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

        h.addWidget(_btn("★ 评估风险  Evaluate", _MAV, self._on_evaluate))
        h.addStretch()
        for label, attr, default, lo, hi, step in [
            ("Vol上限:", "_vol_spin",   0.30, 0.05, 1.0, 0.05),
            ("DD上限:",  "_dd_spin",    0.20, 0.05, 1.0, 0.05),
            ("Beta上限:","_beta_spin",  0.80, 0.10, 2.0, 0.10),
        ]:
            h.addWidget(QtWidgets.QLabel(label))
            spin = QtWidgets.QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setSingleStep(step)
            spin.setValue(default)
            spin.setDecimals(2)
            spin.setFixedWidth(65)
            spin.setStyleSheet(
                f"background: #11111b; color: {_FG};"
                f" border: 1px solid {_BORDER}; border-radius: 3px; padding: 2px;"
            )
            setattr(self, attr, spin)
            h.addWidget(spin)
        h.addWidget(_btn("更新上限  Update", _CYN, self._on_update_limits))
        h.addWidget(_btn("刷新 Refresh", _MUT, self.refresh))
        return bar

    def refresh(self) -> None:
        if self._engine is None:
            return
        snap = self._engine.risk_budget_engine.get_latest_snapshot()
        if snap is None:
            return
        self._update_kpis(snap)
        self._render_budget_table(snap)
        self._render_signal_table(snap)

    def _on_evaluate(self) -> None:
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "未初始化", "请先启动引擎。")
            return
        snap_alloc = self._engine.allocation_engine.get_latest_snapshot()
        if snap_alloc is None:
            QtWidgets.QMessageBox.information(self, "提示", "请先执行「计算分配」。")
            return
        self._engine.evaluate_risk()
        self.refresh()

    def _on_update_limits(self) -> None:
        if self._engine is None:
            return
        self._engine.update_risk_budget(
            vol_limit  = self._vol_spin.value(),
            dd_limit   = self._dd_spin.value(),
            beta_limit = self._beta_spin.value(),
        )

    def _update_kpis(self, snap) -> None:
        var_c = _RED if snap.portfolio_var > 0.02 else (
            _YLW if snap.portfolio_var > 0.01 else _GRN)
        self._kpi_var.update(f"{snap.portfolio_var:.4f}", var_c)
        dd_c = _RED if snap.portfolio_dd > 0.12 else (
            _YLW if snap.portfolio_dd > 0.06 else _GRN)
        self._kpi_dd.update(f"{snap.portfolio_dd:.4f}", dd_c)
        b = snap.portfolio_beta
        self._kpi_beta.update(f"{b:.4f}", _YLW if abs(b) > 0.5 else _GRN)
        self._kpi_breach.update(
            str(snap.n_breached), _RED if snap.n_breached > 0 else _GRN)
        n_sig = len(snap.adjust_signals)
        self._kpi_sigs.update(str(n_sig), _RED if n_sig > 0 else _GRN)

    def _render_budget_table(self, snap) -> None:
        self._budget_tbl.setSortingEnabled(False)
        self._budget_tbl.setRowCount(0)
        sev_color = {"critical": _RED, "warn": _YLW, "": _MUT}

        for alpha_id, budgets in sorted(snap.budgets.items()):
            for b in budgets:
                row = self._budget_tbl.rowCount()
                self._budget_tbl.insertRow(row)
                uc  = _util_color(b.utilization)
                hc  = _GRN if b.headroom > 0 else _RED
                sev = next(
                    (br.severity for br in snap.breaches
                     if br.alpha_id == alpha_id
                     and br.budget_type == b.budget_type),
                    "",
                )
                bc = sev_color.get(sev, _MUT)
                self._budget_tbl.setItem(row, 0, _item(alpha_id,                   _MAV))
                self._budget_tbl.setItem(row, 1, _item(b.budget_type.value,        _BLU))
                self._budget_tbl.setItem(row, 2, _item(f"{b.current_value:.4f}",   uc))
                self._budget_tbl.setItem(row, 3, _item(f"{b.budget_limit:.4f}",    _MUT))
                self._budget_tbl.setItem(row, 4, _item(f"{b.utilization:.2%}",     uc))
                self._budget_tbl.setItem(row, 5, _item(f"{b.headroom:.4f}",        hc))
                self._budget_tbl.setItem(row, 6, _item(f"{b.weight:.4f}",          _FG))
                self._budget_tbl.setItem(
                    row, 7, _item(b.status.value, _RED if b.is_breached else _GRN))
                self._budget_tbl.setItem(
                    row, 8, _item("⚠" if b.is_breached else "✓", bc))
        self._budget_tbl.setSortingEnabled(True)

    def _render_signal_table(self, snap) -> None:
        self._signal_tbl.setRowCount(0)
        uc_map = {"critical": _RED, "high": _RED, "warn": _YLW,
                  "normal": _YLW, "low": _MUT}
        for sig in snap.adjust_signals:
            row = self._signal_tbl.rowCount()
            self._signal_tbl.insertRow(row)
            uc = uc_map.get(sig.urgency, _MUT)
            dc = _RED if sig.delta_ratio < 0 else _YLW
            self._signal_tbl.setItem(row, 0, _item(sig.signal_id,                  _MUT))
            self._signal_tbl.setItem(row, 1, _item(sig.alpha_id,                   _MAV))
            self._signal_tbl.setItem(row, 2, _item(sig.breach.budget_type.value,   _BLU))
            self._signal_tbl.setItem(row, 3, _item(f"{sig.current_ratio:.4f}",     _FG))
            self._signal_tbl.setItem(row, 4, _item(f"{sig.suggested_ratio:.4f}",   _YLW))
            self._signal_tbl.setItem(row, 5, _item(f"{sig.delta_ratio:+.4f}",      dc))
            self._signal_tbl.setItem(row, 6, _item(sig.urgency,                    uc))
            self._signal_tbl.setItem(
                row, 7,
                _item(sig.reason, _FG,
                      QtCore.Qt.AlignmentFlag.AlignLeft |
                      QtCore.Qt.AlignmentFlag.AlignVCenter))
