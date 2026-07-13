"""
capital_allocation_ai/ui/rebalance_tab.py  (Phase 5)

RebalanceTab — 再平衡面板。
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

_TRADE_COLS = [
    ("Alpha ID",  110), ("当前比例", 80), ("目标比例", 80),
    ("变化 Δ",     75), ("交易金额", 110), ("方向",      65),
]
_HIST_COLS = [
    ("记录 ID",   100), ("计划 ID",   100), ("触发类型",  80),
    ("状态",       70), ("交易笔数",   70), ("换手金额",  110),
    ("预估成本",   90), ("创建时间",   140),
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


class RebalanceTab(QtWidgets.QWidget):
    """再平衡面板（Phase 5）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._current_plan_id: str | None = None
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
        self._kpi_count   = _KpiCard("再平衡次数  Count")
        self._kpi_drift   = _KpiCard("最新漂移分  Drift")
        self._kpi_trades  = _KpiCard("交易笔数  Trades")
        self._kpi_cost    = _KpiCard("预估成本  Est.Cost")
        self._kpi_cost_ok = _KpiCard("成本有效  Cost-OK")
        for c in (self._kpi_count, self._kpi_drift, self._kpi_trades,
                  self._kpi_cost, self._kpi_cost_ok):
            h.addWidget(c, stretch=1)
        return w

    def _build_main_area(self) -> QtWidgets.QSplitter:
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_trade_table())
        splitter.addWidget(self._build_history_panel())
        splitter.setSizes([700, 500])
        return splitter

    def _build_trade_table(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("再平衡交易明细  Rebalance Trades")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._trade_tbl = QtWidgets.QTableWidget(0, len(_TRADE_COLS))
        self._trade_tbl.setHorizontalHeaderLabels([c[0] for c in _TRADE_COLS])
        for i, (_, w_) in enumerate(_TRADE_COLS):
            self._trade_tbl.setColumnWidth(i, w_)
        self._trade_tbl.horizontalHeader().setStretchLastSection(True)
        self._trade_tbl.verticalHeader().setVisible(False)
        self._trade_tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._trade_tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._trade_tbl.setStyleSheet("font-size: 11px;")
        v.addWidget(self._trade_tbl, stretch=1)
        self._cost_lbl = QtWidgets.QLabel("--- 成本明细 ---")
        self._cost_lbl.setStyleSheet(
            f"color: {_MUT}; font-size: 10px; padding: 2px 0px;")
        v.addWidget(self._cost_lbl)
        return w

    def _build_history_panel(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("再平衡历史  Rebalance History")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._hist_tbl = QtWidgets.QTableWidget(0, len(_HIST_COLS))
        self._hist_tbl.setHorizontalHeaderLabels([c[0] for c in _HIST_COLS])
        for i, (_, w_) in enumerate(_HIST_COLS):
            self._hist_tbl.setColumnWidth(i, w_)
        self._hist_tbl.horizontalHeader().setStretchLastSection(True)
        self._hist_tbl.verticalHeader().setVisible(False)
        self._hist_tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._hist_tbl.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._hist_tbl.setStyleSheet("font-size: 11px;")
        v.addWidget(self._hist_tbl, stretch=1)
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

        h.addWidget(_btn("⚡ 手动触发  Manual", _MAV, self._on_manual))
        h.addWidget(_btn("★ 自动检测  Auto",    _CYN, self._on_auto))
        h.addWidget(_btn("✓ 批准  Approve",     _GRN, self._on_approve))
        h.addWidget(_btn("✗ 取消  Cancel",      _RED, self._on_cancel))
        h.addStretch()
        h.addWidget(_btn("刷新 Refresh",         _MUT, self.refresh))
        return bar

    def refresh(self) -> None:
        if self._engine is None:
            return
        plan = self._engine.rebalance_engine.get_latest_plan()
        summ = self._engine.rebalance_engine.summary()
        hist = self._engine.get_rebalance_history(limit=50)
        self._update_kpis(summ, plan)
        if plan:
            self._render_trade_table(plan)
            self._current_plan_id = plan.plan_id
        self._render_history_table(hist)

    def _on_manual(self) -> None:
        if self._engine is None:
            QtWidgets.QMessageBox.warning(self, "未初始化", "请先启动引擎。")
            return
        if self._engine.allocation_engine.get_latest_snapshot() is None:
            QtWidgets.QMessageBox.information(self, "提示", "请先执行「计算分配」。")
            return
        self._engine.trigger_rebalance(trigger_type="manual", force=True)
        self.refresh()

    def _on_auto(self) -> None:
        if self._engine is None:
            return
        plan = self._engine.auto_rebalance()
        if plan is None:
            QtWidgets.QMessageBox.information(
                self, "自动检测", "当前无需再平衡，所有条件均未触发。")
        self.refresh()

    def _on_approve(self) -> None:
        if self._engine is None or self._current_plan_id is None:
            return
        ok = self._engine.approve_rebalance(self._current_plan_id)
        if ok:
            QtWidgets.QMessageBox.information(
                self, "批准", f"计划 {self._current_plan_id} 已批准。")
        self.refresh()

    def _on_cancel(self) -> None:
        if self._engine is None or self._current_plan_id is None:
            return
        ok = self._engine.cancel_rebalance(
            self._current_plan_id, reason="User cancelled")
        if ok:
            QtWidgets.QMessageBox.information(
                self, "取消", f"计划 {self._current_plan_id} 已取消。")
        self.refresh()

    def _update_kpis(self, summ: dict, plan) -> None:
        self._kpi_count.update(str(summ.get("rebalances", 0)), _MAV)
        drift = summ.get("latest_drift", 0.0)
        self._kpi_drift.update(
            f"{drift:.4f}",
            _RED if drift > 0.1 else (_YLW if drift > 0.05 else _GRN))
        self._kpi_trades.update(str(summ.get("latest_trades", 0)), _BLU)
        cost = summ.get("latest_cost", 0.0)
        self._kpi_cost.update(
            f"¥{cost:,.0f}" if cost else "---",
            _YLW if cost > 0 else _MUT)
        if plan is not None:
            ok = plan.is_cost_effective
            self._kpi_cost_ok.update("✓ YES" if ok else "✗ NO",
                                     _GRN if ok else _RED)
        else:
            self._kpi_cost_ok.update("---", _MUT)

    def _render_trade_table(self, plan) -> None:
        self._trade_tbl.setRowCount(0)
        for t in sorted(plan.trades,
                        key=lambda x: abs(x.delta_amount), reverse=True):
            row = self._trade_tbl.rowCount()
            self._trade_tbl.insertRow(row)
            dc  = _GRN if t.delta_amount > 0 else _RED
            dir_lbl = "▲ 增配" if t.delta_amount > 0 else "▼ 减配"
            self._trade_tbl.setItem(row, 0, _item(t.alpha_id,               _MAV))
            self._trade_tbl.setItem(row, 1, _item(f"{t.prev_ratio:.4f}",    _MUT))
            self._trade_tbl.setItem(row, 2, _item(f"{t.target_ratio:.4f}",  _FG))
            self._trade_tbl.setItem(row, 3, _item(f"{t.delta_ratio:+.4f}",  dc))
            self._trade_tbl.setItem(row, 4, _item(f"¥{t.delta_amount:+,.0f}", dc))
            self._trade_tbl.setItem(row, 5, _item(dir_lbl,                  dc))

        cost = plan.cost_estimate
        self._cost_lbl.setText(
            f"换手: ¥{plan.total_turnover:,.0f}  |  "
            f"佣金: ¥{cost.get('commission',0):,.0f}  |  "
            f"滑点: ¥{cost.get('slippage',0):,.0f}  |  "
            f"总成本: ¥{cost.get('total',0):,.0f}  |  "
            f"批次: {len(plan.batches)}  |  触发: {plan.trigger.value}")

    def _render_history_table(self, history: list[dict]) -> None:
        self._hist_tbl.setRowCount(0)
        sc_map = {"planned": _YLW, "approved": _GRN, "cancelled": _RED}
        tc_map = {"manual": _MAV, "scheduled": _BLU, "risk": _RED, "score": _ORG}
        for rec in reversed(history):
            row = self._hist_tbl.rowCount()
            self._hist_tbl.insertRow(row)
            sc = sc_map.get(rec.get("status", ""), _MUT)
            tc = tc_map.get(rec.get("trigger", ""), _MUT)
            self._hist_tbl.setItem(row, 0, _item(rec.get("record_id",""),        _MUT))
            self._hist_tbl.setItem(row, 1, _item(rec.get("plan_id",""),          _MUT))
            self._hist_tbl.setItem(row, 2, _item(rec.get("trigger",""),          tc))
            self._hist_tbl.setItem(row, 3, _item(rec.get("status",""),           sc))
            self._hist_tbl.setItem(row, 4, _item(rec.get("n_trades",""),         _FG))
            self._hist_tbl.setItem(row, 5, _item(
                f"¥{rec.get('turnover',0):,.0f}",  _FG))
            self._hist_tbl.setItem(row, 6, _item(
                f"¥{rec.get('cost',0):,.0f}",      _YLW))
            self._hist_tbl.setItem(row, 7, _item(rec.get("created_at",""),       _MUT))
