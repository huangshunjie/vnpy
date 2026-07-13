"""
quant_os/ui/lifecycle_tab.py

LifecycleTab — Alpha / Strategy 生命周期可视化面板（Phase 3）。
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from ..model.lifecycle_model import AlphaState, StrategyState

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_ORG      = "#fab387"

_ALPHA_STATE_COLOR = {
    AlphaState.GENERATED.value: _BLU,
    AlphaState.VALIDATED.value: _GRN,
    AlphaState.LIVE.value:      _GRN,
    AlphaState.DEGRADED.value:  _YLW,
    AlphaState.RETIRED.value:   _MUT,
}
_STRAT_STATE_COLOR = {
    StrategyState.BACKTEST.value: _BLU,
    StrategyState.PAPER.value:    _YLW,
    StrategyState.LIVE.value:     _GRN,
    StrategyState.DISABLED.value: _MUT,
}

_ALPHA_FLOW = ["GENERATED", "VALIDATED", "LIVE", "DEGRADED", "RETIRED"]
_STRAT_FLOW = ["BACKTEST", "PAPER", "LIVE", "DISABLED"]

_ALPHA_COLS = [
    ("Alpha ID",  90), ("因子名称", 120), ("状态", 80),
    ("验证评分",  70), ("创建时间", 140), ("更新时间", 140),
    ("天数",      50), ("备注",    150),
]
_STRAT_COLS = [
    ("Strategy ID", 90), ("策略名称", 120), ("状态", 80),
    ("回测Sharpe",  80), ("实盘Sharpe", 80), ("关联Alpha", 90),
    ("创建时间",   140), ("备注",      120),
]


def _item(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    it.setForeground(QtGui.QColor(color))
    return it


def _item_left(text: str, color: str = _FG) -> QtWidgets.QTableWidgetItem:
    from vnpy.trader.ui import QtGui
    it = QtWidgets.QTableWidgetItem(str(text))
    it.setTextAlignment(
        QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter
    )
    it.setForeground(QtGui.QColor(color))
    return it


class LifecycleTab(QtWidgets.QWidget):
    """Alpha / Strategy 生命周期可视化 Tab（Phase 3）。"""

    def __init__(self, os_engine=None, parent=None) -> None:
        super().__init__(parent)
        self._os_engine = os_engine
        self._init_ui()

    def set_os_engine(self, os_engine) -> None:
        self._os_engine = os_engine

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_kpi_bar())
        root.addWidget(self._build_flow_bar())
        sp = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        sp.addWidget(self._build_alpha_panel())
        sp.addWidget(self._build_strategy_panel())
        sp.setSizes([580, 580])
        root.addWidget(sp, stretch=1)
        root.addWidget(self._build_action_bar())

    def _build_kpi_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(66)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(16, 6, 16, 6)
        h.setSpacing(24)
        kpis = [
            ("Alpha 总数",     "0", _FG),
            ("Alpha Live",     "0", _GRN),
            ("Alpha Degraded", "0", _YLW),
            ("Alpha Retired",  "0", _MUT),
            ("Strategy 总数",  "0", _FG),
            ("Strategy Live",  "0", _GRN),
            ("Strategy Paper", "0", _YLW),
        ]
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for name, val, color in kpis:
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
            self._kpi[name] = lv
            h.addLayout(col)
        h.addStretch()
        return bar

    def _build_flow_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(38)
        bar.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(16, 4, 16, 4)
        colors_a = [_BLU, _GRN, _GRN, _YLW, _MUT]
        colors_s = [_BLU, _YLW, _GRN, _MUT]

        def lbl(t, c):
            l = QtWidgets.QLabel(t)
            l.setStyleSheet(f"color: {c}; font-size: 11px; font-weight: bold;")
            return l

        h.addWidget(lbl("Alpha：", _MUT))
        for i, (st, c) in enumerate(zip(_ALPHA_FLOW, colors_a)):
            h.addWidget(lbl(st, c))
            if i < len(_ALPHA_FLOW) - 1:
                h.addWidget(lbl("→", _BORDER))
        h.addWidget(lbl("   |   Strategy：", _MUT))
        for i, (st, c) in enumerate(zip(_STRAT_FLOW, colors_s)):
            h.addWidget(lbl(st, c))
            if i < len(_STRAT_FLOW) - 1:
                h.addWidget(lbl("→", _BORDER))
        h.addStretch()
        return bar

    def _build_alpha_panel(self) -> 'QtWidgets.QWidget':
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("Alpha 生命周期")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._tbl_alpha = QtWidgets.QTableWidget(0, len(_ALPHA_COLS))
        self._tbl_alpha.setHorizontalHeaderLabels([c[0] for c in _ALPHA_COLS])
        for i, (_, w_) in enumerate(_ALPHA_COLS):
            self._tbl_alpha.setColumnWidth(i, w_)
        self._tbl_alpha.horizontalHeader().setStretchLastSection(True)
        self._tbl_alpha.verticalHeader().setVisible(False)
        self._tbl_alpha.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_alpha.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_alpha.setStyleSheet("font-size: 12px;")
        v.addWidget(self._tbl_alpha, stretch=1)
        return w

    def _build_strategy_panel(self) -> 'QtWidgets.QWidget':
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(3)
        lbl = QtWidgets.QLabel("Strategy 生命周期")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._tbl_strat = QtWidgets.QTableWidget(0, len(_STRAT_COLS))
        self._tbl_strat.setHorizontalHeaderLabels([c[0] for c in _STRAT_COLS])
        for i, (_, w_) in enumerate(_STRAT_COLS):
            self._tbl_strat.setColumnWidth(i, w_)
        self._tbl_strat.horizontalHeader().setStretchLastSection(True)
        self._tbl_strat.verticalHeader().setVisible(False)
        self._tbl_strat.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tbl_strat.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._tbl_strat.setStyleSheet("font-size: 12px;")
        v.addWidget(self._tbl_strat, stretch=1)
        return w

    def _build_action_bar(self) -> 'QtWidgets.QWidget':
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
                f" padding: 4px 10px; font-size: 11px; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            b.clicked.connect(slot)
            return b
        h.addWidget(_btn("验证 Alpha: Validate", _GRN, self._alpha_validate))
        h.addWidget(_btn("上线 Alpha: Go Live",  _GRN, self._alpha_live))
        h.addWidget(_btn("降级 Alpha: Degrade",  _YLW, self._alpha_degrade))
        h.addWidget(_btn("退役 Alpha: Retire",   _RED, self._alpha_retire))
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        sep.setStyleSheet("color: #45475a;")
        sep.setFixedWidth(1)
        h.addWidget(sep)
        h.addWidget(_btn("模拟 Strat: Paper",   _YLW, self._strat_paper))
        h.addWidget(_btn("实盘 Strat: Live",    _GRN, self._strat_live))
        h.addWidget(_btn("禁用 Strat: Disable", _RED, self._strat_disable))
        h.addStretch()
        btn_r = QtWidgets.QPushButton("刷新")
        btn_r.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 4px 12px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {_BORDER}33; }}"
        )
        btn_r.clicked.connect(self.refresh)
        h.addWidget(btn_r)
        return bar

    # ------------------------------------------------------------------ #
    #  公开接口
    # ------------------------------------------------------------------ #

    def refresh(self) -> None:
        if self._os_engine is None:
            return
        lm = self._os_engine.lifecycle_manager
        self._refresh_alpha_table(lm.get_all_alphas())
        self._refresh_strat_table(lm.get_all_strategies())
        self._refresh_kpi(lm)

    def on_lifecycle_change(self, event_type: str, data: dict) -> None:
        self.refresh()

    # ------------------------------------------------------------------ #
    #  Alpha 操作
    # ------------------------------------------------------------------ #

    def _selected_alpha_id(self):
        row = self._tbl_alpha.currentRow()
        if row < 0:
            return None
        it = self._tbl_alpha.item(row, 0)
        return it.text() if it else None

    def _alpha_validate(self) -> None:
        aid = self._selected_alpha_id()
        if aid and self._os_engine:
            self._os_engine.advance_alpha(aid, AlphaState.VALIDATED, reason="手动 Validated")
            self.refresh()

    def _alpha_live(self) -> None:
        aid = self._selected_alpha_id()
        if aid and self._os_engine:
            self._os_engine.advance_alpha(aid, AlphaState.LIVE, reason="手动 Live")
            self.refresh()

    def _alpha_degrade(self) -> None:
        aid = self._selected_alpha_id()
        if aid and self._os_engine:
            self._os_engine.advance_alpha(aid, AlphaState.DEGRADED, reason="手动 Degraded")
            self.refresh()

    def _alpha_retire(self) -> None:
        aid = self._selected_alpha_id()
        if aid and self._os_engine:
            self._os_engine.retire_alpha(aid, reason="手动退役")
            self.refresh()

    # ------------------------------------------------------------------ #
    #  Strategy 操作
    # ------------------------------------------------------------------ #

    def _selected_strategy_id(self):
        row = self._tbl_strat.currentRow()
        if row < 0:
            return None
        it = self._tbl_strat.item(row, 0)
        return it.text() if it else None

    def _strat_paper(self) -> None:
        sid = self._selected_strategy_id()
        if sid and self._os_engine:
            self._os_engine.advance_strategy(sid, StrategyState.PAPER, reason="手动 Paper")
            self.refresh()

    def _strat_live(self) -> None:
        sid = self._selected_strategy_id()
        if sid and self._os_engine:
            self._os_engine.advance_strategy(sid, StrategyState.LIVE, reason="手动 Live")
            self.refresh()

    def _strat_disable(self) -> None:
        sid = self._selected_strategy_id()
        if sid and self._os_engine:
            self._os_engine.disable_strategy(sid, reason="手动禁用")
            self.refresh()

    # ------------------------------------------------------------------ #
    #  内部渲染
    # ------------------------------------------------------------------ #

    def _refresh_alpha_table(self, alphas) -> None:
        self._tbl_alpha.setRowCount(0)
        for a in alphas:
            row = self._tbl_alpha.rowCount()
            self._tbl_alpha.insertRow(row)
            sc = _ALPHA_STATE_COLOR.get(a.state.value, _FG)
            vs_c = _GRN if a.validation_score >= 60 else _YLW
            self._tbl_alpha.setItem(row, 0, _item(a.alpha_id,                    _MUT))
            self._tbl_alpha.setItem(row, 1, _item_left(a.factor_name,            _FG))
            self._tbl_alpha.setItem(row, 2, _item(a.state.value.upper(),         sc))
            self._tbl_alpha.setItem(row, 3, _item(f"{a.validation_score:.1f}",   vs_c))
            self._tbl_alpha.setItem(row, 4, _item(str(a.created_at)[:19],        _MUT))
            self._tbl_alpha.setItem(row, 5, _item(str(a.updated_at)[:19],        _MUT))
            self._tbl_alpha.setItem(row, 6, _item(f"{a.age_days:.1f}",           _FG))
            self._tbl_alpha.setItem(row, 7, _item_left(a.notes or "---",         _MUT))

    def _refresh_strat_table(self, strats) -> None:
        self._tbl_strat.setRowCount(0)
        for s in strats:
            row = self._tbl_strat.rowCount()
            self._tbl_strat.insertRow(row)
            sc   = _STRAT_STATE_COLOR.get(s.state.value, _FG)
            sh_c = _GRN if s.backtest_sharpe >= 1.0 else (_YLW if s.backtest_sharpe >= 0.5 else _RED)
            ls_c = _GRN if s.live_sharpe >= 1.0 else _MUT
            self._tbl_strat.setItem(row, 0, _item(s.strategy_id,                 _MUT))
            self._tbl_strat.setItem(row, 1, _item_left(s.strategy_name,          _FG))
            self._tbl_strat.setItem(row, 2, _item(s.state.value.upper(),         sc))
            self._tbl_strat.setItem(row, 3, _item(f"{s.backtest_sharpe:.2f}",    sh_c))
            self._tbl_strat.setItem(row, 4, _item(f"{s.live_sharpe:.2f}",        ls_c))
            self._tbl_strat.setItem(row, 5, _item(s.alpha_id or "---",           _MUT))
            self._tbl_strat.setItem(row, 6, _item(str(s.created_at)[:19],        _MUT))
            self._tbl_strat.setItem(row, 7, _item_left(s.notes or "---",         _MUT))

    def _refresh_kpi(self, lm) -> None:
        alphas = lm.get_all_alphas()
        strats = lm.get_all_strategies()
        self._kpi["Alpha 总数"    ].setText(str(len(alphas)))
        self._kpi["Alpha Live"    ].setText(str(sum(1 for a in alphas if a.state == AlphaState.LIVE)))
        self._kpi["Alpha Degraded"].setText(str(sum(1 for a in alphas if a.state == AlphaState.DEGRADED)))
        self._kpi["Alpha Retired" ].setText(str(sum(1 for a in alphas if a.state == AlphaState.RETIRED)))
        self._kpi["Strategy 总数" ].setText(str(len(strats)))
        self._kpi["Strategy Live" ].setText(str(sum(1 for s in strats if s.state == StrategyState.LIVE)))
        self._kpi["Strategy Paper"].setText(str(sum(1 for s in strats if s.state == StrategyState.PAPER)))
