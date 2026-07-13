"""
market_regime_ai/ui/dashboard_tab.py  (Phase 4)

DashboardTab — 总览面板（完整实现）。
"""

from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui

_PANEL  = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_GRN    = "#a6e3a1"
_RED    = "#f38ba8"
_YLW    = "#f9e2af"
_MAV    = "#cba6f7"
_ORG    = "#fab387"
_CYN    = "#89dceb"

_REGIME_COLORS = {
    "bull": _GRN, "bear": _RED, "sideways": _YLW,
    "high_vol": _ORG, "low_liq": _CYN, "unknown": _MUT,
}
_ACTION_COLORS = {
    "REBALANCE_NOW": _RED, "REDUCE_EXPOSURE": _ORG,
    "TIGHTEN_RISK": _YLW, "INCREASE_EXPOSURE": _GRN, "MAINTAIN": _MUT,
}


class DashboardTab(QtWidgets.QWidget):
    """总览面板（Phase 4）。"""

    def __init__(self, engine=None, parent=None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._init_ui()

    def set_engine(self, engine) -> None:
        self._engine = engine

    def _init_ui(self) -> None:
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)
        root.addWidget(self._build_top_row())
        mid = QtWidgets.QHBoxLayout()
        mid.setSpacing(10)
        mid.addWidget(self._build_decision_panel(), stretch=1)
        mid.addWidget(self._build_factor_panel(),   stretch=1)
        root.addLayout(mid)
        root.addWidget(self._build_history_panel(), stretch=1)
        root.addWidget(self._build_action_bar())

    # ── 顶部状态行 ────────────────────────────────────────────────────

    def _build_top_row(self):
        row = QtWidgets.QWidget()
        row.setFixedHeight(100)
        row.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(24, 12, 24, 12)
        h.setSpacing(48)
        self._regime_blk = self._kpi("Market Regime", "UNKNOWN", _MUT, "22px")
        self._conf_blk   = self._kpi("Confidence",    "---",     _MUT)
        self._rec_blk    = self._kpi("Strategy",       "NEUTRAL", _MUT)
        self._action_blk = self._kpi("Action",         "MAINTAIN",_MUT, "16px")
        self._uptime_blk = self._kpi("Uptime",         "---",     _MUT)
        for w in [self._regime_blk, self._conf_blk, self._rec_blk,
                  self._action_blk, self._uptime_blk]:
            h.addWidget(w)
        h.addStretch()
        return row

    def _kpi(self, title, value, color, size="15px"):
        w = QtWidgets.QWidget()
        w.setStyleSheet("border: none; background: transparent;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        tl = QtWidgets.QLabel(title)
        tl.setStyleSheet(f"color: {_MUT}; font-size: 9px; border: none;")
        vl = QtWidgets.QLabel(value)
        vl.setStyleSheet(
            f"color: {color}; font-size: {size}; font-weight: bold; border: none;")
        v.addWidget(tl)
        v.addWidget(vl)
        w._vl = vl
        return w

    # ── 决策信号面板 ──────────────────────────────────────────────────

    def _build_decision_panel(self):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)
        title = QtWidgets.QLabel("Decision Signal  决策信号")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(title)
        v.addWidget(self._sep())
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(8)
        self._cap_lbl  = self._signal_card("Capital Adj",       "1.000", _FG)
        self._risk_lbl = self._signal_card("Risk Adj",          "1.000", _FG)
        self._pos_lbl  = self._signal_card("Position Limit",    "1.000", _FG)
        self._urg_lbl  = self._signal_card("Rebalance Urgency", "0.000", _FG)
        grid.addWidget(self._cap_lbl,  0, 0)
        grid.addWidget(self._risk_lbl, 0, 1)
        grid.addWidget(self._pos_lbl,  1, 0)
        grid.addWidget(self._urg_lbl,  1, 1)
        v.addLayout(grid)
        v.addStretch()
        return panel

    def _signal_card(self, title, value, color):
        card = QtWidgets.QWidget()
        card.setStyleSheet(
            f"background: #11111b; border-radius: 6px; border: 1px solid {_BORDER};")
        cv = QtWidgets.QVBoxLayout(card)
        cv.setContentsMargins(10, 8, 10, 8)
        cv.setSpacing(2)
        tl = QtWidgets.QLabel(title)
        tl.setStyleSheet(f"color: {_MUT}; font-size: 9px; border: none;")
        vl = QtWidgets.QLabel(value)
        vl.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: bold; border: none;")
        vl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        cv.addWidget(tl)
        cv.addWidget(vl)
        card._vl = vl
        return card

    # ── 因子总览面板 ────────────────────────────────────────────────

    def _build_factor_panel(self):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(10)
        title = QtWidgets.QLabel("Factor Overview  因子总览")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(title)
        v.addWidget(self._sep())
        self._vol_card   = self._factor_card("Volatility", "NORMAL", _FG)
        self._trend_card = self._factor_card("Trend",       "FLAT",   _FG)
        self._liq_card   = self._factor_card("Liquidity",   "NORMAL", _FG)
        self._stab_card  = self._factor_card("Stability",   "---",    _FG)
        for c in [self._vol_card, self._trend_card,
                  self._liq_card, self._stab_card]:
            v.addWidget(c)
        v.addStretch()
        return panel

    def _factor_card(self, title, value, color):
        card = QtWidgets.QWidget()
        card.setFixedHeight(52)
        card.setStyleSheet(
            f"background: #11111b; border-radius: 6px; border: 1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(card)
        h.setContentsMargins(12, 6, 12, 6)
        tl = QtWidgets.QLabel(title)
        tl.setStyleSheet(f"color: {_MUT}; font-size: 10px; border: none;")
        vl = QtWidgets.QLabel(value)
        vl.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: bold; border: none;")
        h.addWidget(tl)
        h.addStretch()
        h.addWidget(vl)
        card._vl = vl
        return card

    # ── 历史表 ──────────────────────────────────────────────────────

    def _build_history_panel(self):
        panel = QtWidgets.QWidget()
        panel.setStyleSheet(
            f"background: {_PANEL}; border-radius: 8px; border: 1px solid {_BORDER};")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(6)
        title = QtWidgets.QLabel("Decision History  决策历史")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 11px; font-weight: bold; border: none;")
        v.addWidget(title)
        v.addWidget(self._sep())
        self._hist_table = QtWidgets.QTableWidget(0, 7)
        self._hist_table.setHorizontalHeaderLabels(
            ["状态", "策略", "资本调整", "风险调整", "仓位上限", "紧迫度", "行动"])
        self._hist_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch)
        self._hist_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._hist_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._hist_table.verticalHeader().setVisible(False)
        self._hist_table.setAlternatingRowColors(True)
        self._hist_table.setMaximumHeight(180)
        self._hist_table.setStyleSheet(
            f"QTableWidget {{ background: #11111b; color: {_FG}; "
            f"border: 1px solid {_BORDER}; gridline-color: {_BORDER}; font-size: 11px; }}"
            f"QHeaderView::section {{ background: #313244; color: {_MUT}; "
            f"padding: 4px; border: none; font-size: 10px; }}"
            f"QTableWidget::item:alternate {{ background: #181825; }}"
        )
        v.addWidget(self._hist_table)
        return panel

    # ── 操作栏 ──────────────────────────────────────────────────────

    def _build_action_bar(self):
        bar = QtWidgets.QWidget()
        bar.setFixedHeight(44)
        h = QtWidgets.QHBoxLayout(bar)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        detect_btn  = self._btn("Detect & Decide  全链路检测", _MAV)
        refresh_btn = self._btn("Refresh  刷新", _MUT)
        detect_btn.clicked.connect(self._on_detect)
        refresh_btn.clicked.connect(self.refresh)
        h.addWidget(detect_btn)
        h.addWidget(refresh_btn)
        h.addStretch()
        self._status_lbl = QtWidgets.QLabel("")
        self._status_lbl.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        h.addWidget(self._status_lbl)
        return bar

    def _btn(self, text, color):
        b = QtWidgets.QPushButton(text)
        b.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {color}; "
            f"border: 1px solid {color}; border-radius: 4px; "
            f"padding: 6px 18px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {color}22; }}"
            f"QPushButton:pressed {{ background: {color}44; }}"
        )
        return b

    def _sep(self):
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border: none; border-top: 1px solid {_BORDER};")
        return s

    # ── 刷新逻辑 ────────────────────────────────────────────────────

    def refresh(self) -> None:
        if self._engine is None:
            return
        try:
            self._refresh_top()
            self._refresh_decision()
            self._refresh_factors()
            self._refresh_history()
        except Exception:
            pass

    def _refresh_top(self) -> None:
        try:
            summ = self._engine.get_summary()
        except Exception:
            return
        regime = summ.get("current_regime", "unknown")
        color  = _REGIME_COLORS.get(regime, _MUT)
        self._regime_blk._vl.setText(regime.upper())
        self._regime_blk._vl.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: bold; border: none;")
        conf = summ.get("confidence", 0.0)
        self._conf_blk._vl.setText(f"{conf:.1%}")
        self._rec_blk._vl.setText(summ.get("recommendation", "neutral").upper())
        action = summ.get("action", "MAINTAIN")
        ac = _ACTION_COLORS.get(action, _MUT)
        self._action_blk._vl.setText(action)
        self._action_blk._vl.setStyleSheet(
            f"color: {ac}; font-size: 16px; font-weight: bold; border: none;")
        uptime = summ.get("uptime", 0.0)
        h2, r = divmod(int(uptime), 3600)
        m2, s2 = divmod(r, 60)
        self._uptime_blk._vl.setText(f"{h2:02d}:{m2:02d}:{s2:02d}")

    def _refresh_decision(self) -> None:
        try:
            sig = self._engine.get_decision_signal()
        except Exception:
            return
        cap  = sig.capital_adjustment
        risk = sig.risk_adjustment
        pos  = sig.position_limit
        urg  = sig.rebalance_urgency
        cap_color  = _GRN if cap  > 1.0 else (_RED if cap  < 0.8 else _FG)
        risk_color = _GRN if risk > 1.0 else (_RED if risk < 0.7 else _FG)
        urg_color  = _RED if urg  > 0.6 else (_YLW if urg  > 0.3 else _GRN)
        self._cap_lbl._vl.setText(f"{cap:.3f}x")
        self._cap_lbl._vl.setStyleSheet(
            f"color: {cap_color}; font-size: 18px; font-weight: bold; border: none;")
        self._risk_lbl._vl.setText(f"{risk:.3f}x")
        self._risk_lbl._vl.setStyleSheet(
            f"color: {risk_color}; font-size: 18px; font-weight: bold; border: none;")
        self._pos_lbl._vl.setText(f"{pos:.3f}x")
        self._urg_lbl._vl.setText(f"{urg:.3f}")
        self._urg_lbl._vl.setStyleSheet(
            f"color: {urg_color}; font-size: 18px; font-weight: bold; border: none;")

    def _refresh_factors(self) -> None:
        try:
            factors = self._engine.get_factor_states()
        except Exception:
            return
        self._vol_card._vl.setText(
            factors.get("volatility", {}).get("regime",    "normal").upper())
        self._trend_card._vl.setText(
            factors.get("trend",      {}).get("direction", "flat"  ).upper())
        self._liq_card._vl.setText(
            factors.get("liquidity",  {}).get("level",     "normal").upper())
        try:
            rs = self._engine.get_regime_state()
            self._stab_card._vl.setText(f"{rs.stability:.1%}")
        except Exception:
            pass

    def _refresh_history(self) -> None:
        try:
            records = self._engine.get_decision_history(limit=15)
        except Exception:
            return
        self._hist_table.setRowCount(0)
        for rec in reversed(records):
            row = self._hist_table.rowCount()
            self._hist_table.insertRow(row)
            regime = rec.get("regime", "")
            action = rec.get("action", "MAINTAIN")
            rc = _REGIME_COLORS.get(regime, _MUT)
            ac = _ACTION_COLORS.get(action, _MUT)
            items  = [
                regime.upper(),
                rec.get("recommendation", "").upper(),
                f"{rec.get('capital_adjustment', 1.0):.3f}x",
                f"{rec.get('risk_adjustment',    1.0):.3f}x",
                f"{rec.get('position_limit',     1.0):.3f}x",
                f"{rec.get('rebalance_urgency',  0.0):.3f}",
                action,
            ]
            colors = [rc, _FG, _FG, _FG, _FG, _FG, ac]
            for col, (text, color) in enumerate(zip(items, colors)):
                item = QtWidgets.QTableWidgetItem(text)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                item.setForeground(QtGui.QColor(color))
                self._hist_table.setItem(row, col, item)

    # ── 操作 / 事件回调 ─────────────────────────────────────────────

    def _on_detect(self) -> None:
        if self._engine is None:
            return
        try:
            self._engine.detect_regime()
            self.refresh()
            self._status_lbl.setText("Detection complete.")
        except Exception as e:
            self._status_lbl.setText(f"Error: {e}")

    def update_from_event(self, data: dict) -> None:
        try:
            regime = data.get("regime", "unknown")
            color  = _REGIME_COLORS.get(regime, _MUT)
            self._regime_blk._vl.setText(regime.upper())
            self._regime_blk._vl.setStyleSheet(
                f"color: {color}; font-size: 22px; font-weight: bold; border: none;")
            self._conf_blk._vl.setText(
                f"{float(data.get('confidence_score', 0.0)):.1%}")
            self._rec_blk._vl.setText(
                data.get("recommendation", "neutral").upper())
        except Exception:
            pass

    def update_decision_from_event(self, data: dict) -> None:
        try:
            cap    = float(data.get("capital_adjustment", 1.0))
            risk   = float(data.get("risk_adjustment",    1.0))
            pos    = float(data.get("position_limit",     1.0))
            urg    = float(data.get("rebalance_urgency",  0.0))
            action = data.get("action", "MAINTAIN")
            ac     = _ACTION_COLORS.get(action, _MUT)
            cap_c  = _GRN if cap  > 1.0 else (_RED if cap  < 0.8 else _FG)
            risk_c = _GRN if risk > 1.0 else (_RED if risk < 0.7 else _FG)
            urg_c  = _RED if urg  > 0.6 else (_YLW if urg  > 0.3 else _GRN)
            self._cap_lbl._vl.setText(f"{cap:.3f}x")
            self._cap_lbl._vl.setStyleSheet(
                f"color: {cap_c}; font-size: 18px; font-weight: bold; border: none;")
            self._risk_lbl._vl.setText(f"{risk:.3f}x")
            self._risk_lbl._vl.setStyleSheet(
                f"color: {risk_c}; font-size: 18px; font-weight: bold; border: none;")
            self._pos_lbl._vl.setText(f"{pos:.3f}x")
            self._urg_lbl._vl.setText(f"{urg:.3f}")
            self._urg_lbl._vl.setStyleSheet(
                f"color: {urg_c}; font-size: 18px; font-weight: bold; border: none;")
            self._action_blk._vl.setText(action)
            self._action_blk._vl.setStyleSheet(
                f"color: {ac}; font-size: 16px; font-weight: bold; border: none;")
        except Exception:
            pass
