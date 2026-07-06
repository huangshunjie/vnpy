"""
market_reality_ai/ui/stress_tab.py

Phase 6: Stress Testing Engine Tab — complete implementation.
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import APP_NAME
from ..event import (
    EVENT_STRESS_TEST_STARTED, EVENT_STRESS_TEST_COMPLETED,
    EVENT_SURVIVAL_SCORE_UPDATED,
)

_BG="#1e1e2e";_DARK="#181825";_BORDER="#45475a";_FG="#cdd6f4"
_MUT="#6c7086";_HEAD="#313244";_GRN="#a6e3a1";_YLW="#f9e2af"
_RED="#f38ba8";_ORG="#fab387";_MAV="#cba6f7";_CYN="#89dceb"
_TEA="#94e2d5"
_GRADE_COLORS={"S":_GRN,"A":_TEA,"B":_YLW,"C":_ORG,"F":_RED}
_SCENARIOS=[
    ("flash_crash","Flash Crash"),
    ("liquidity_dry_up","Liquidity Dry-Up"),
    ("extreme_volatility","Extreme Volatility"),
    ("regime_collapse","Regime Collapse"),
    ("correlation_breakdown","Correlation Breakdown"),
    ("fat_tail_event","Fat Tail Event"),
]

def _lbl(t,s=""):
    w=QtWidgets.QLabel(t); w.setStyleSheet(s); return w


class StressTab(QtWidgets.QWidget):
    """Phase 6: Stress Testing Engine tab."""

    def __init__(self, main_engine=None, event_engine=None, parent=None):
        super().__init__(parent)
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine = main_engine.get_engine(APP_NAME) if main_engine else None
        self._subscriptions = []
        self._init_ui()
        if event_engine:
            for ev, fn in [
                (EVENT_STRESS_TEST_STARTED,   self._on_started),
                (EVENT_STRESS_TEST_COMPLETED, self._on_completed),
                (EVENT_SURVIVAL_SCORE_UPDATED,self._on_score),
            ]:
                event_engine.register(ev, fn)
                self._subscriptions.append((ev, fn))

    def _init_ui(self):
        self.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(self)
        vb.setContentsMargins(10,10,10,10); vb.setSpacing(8)
        top = QtWidgets.QHBoxLayout(); top.setSpacing(8)
        top.addWidget(self._build_controls(), stretch=1)
        top.addWidget(self._build_score_card(), stretch=0)
        vb.addLayout(top)
        vb.addWidget(self._build_results_table(), stretch=1)
        self._status_lbl = _lbl("Ready",
            f"color:{_MUT};font-size:9px;border:none;background:transparent;")
        vb.addWidget(self._status_lbl)

    def _build_controls(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                        f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(14,12,14,12); vb.setSpacing(8)
        vb.addWidget(_lbl("Stress Scenario Controls",
            f"color:{_YLW};font-size:11px;font-weight:bold;"
            f"border:none;background:transparent;"))
        sc_row = QtWidgets.QHBoxLayout(); sc_row.setSpacing(8)
        sc_row.addWidget(_lbl("Scenario:",
            f"color:{_MUT};font-size:9px;border:none;background:transparent;"))
        self._scenario_cb = QtWidgets.QComboBox()
        self._scenario_cb.setStyleSheet(
            f"QComboBox{{background:{_BG};color:{_FG};"
            f"border:1px solid {_BORDER};border-radius:3px;"
            f"padding:2px 8px;font-size:9px;}}"
            f"QComboBox::drop-down{{border:none;}}"
            f"QComboBox QAbstractItemView{{background:{_HEAD};color:{_FG};"
            f"border:1px solid {_BORDER};}}")
        for val, label in _SCENARIOS:
            self._scenario_cb.addItem(label, userData=val)
        sc_row.addWidget(self._scenario_cb, stretch=1)
        vb.addLayout(sc_row)
        btn_row = QtWidgets.QHBoxLayout(); btn_row.setSpacing(8)
        for label, color, slot in [
            ("▶  Run Scenario", _GRN, self._run_single),
            ("⟳  Run All (6)",  _YLW, self._run_all),
            ("⟳  Get Score",    _MAV, self._get_score),
            ("✕  Clear",        _MUT, self._clear_table),
        ]:
            b = QtWidgets.QPushButton(label)
            b.setFixedHeight(28)
            b.setStyleSheet(
                f"QPushButton{{background:{color};color:#1e1e2e;"
                f"font-weight:bold;border:none;border-radius:3px;"
                f"padding:0 10px;font-size:9px;}}"
                f"QPushButton:disabled{{background:{_BORDER};color:{_MUT};}}")
            b.clicked.connect(slot)
            btn_row.addWidget(b)
        vb.addLayout(btn_row)
        cfg_row = QtWidgets.QHBoxLayout(); cfg_row.setSpacing(12)
        cfg_row.addWidget(_lbl("Portfolio Value:",
            f"color:{_MUT};font-size:9px;border:none;background:transparent;"))
        self._pv_spin = QtWidgets.QDoubleSpinBox()
        self._pv_spin.setRange(100_000, 100_000_000)
        self._pv_spin.setValue(1_000_000); self._pv_spin.setSingleStep(100_000)
        self._pv_spin.setStyleSheet(
            f"QDoubleSpinBox{{background:{_BG};color:{_FG};"
            f"border:1px solid {_BORDER};border-radius:3px;"
            f"padding:2px 6px;font-size:9px;}}")
        cfg_row.addWidget(self._pv_spin); cfg_row.addStretch()
        vb.addLayout(cfg_row)
        return w

    def _build_score_card(self):
        w = QtWidgets.QWidget(); w.setFixedWidth(180)
        w.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                        f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(14,14,14,14); vb.setSpacing(6)
        vb.addWidget(_lbl("System Survival",
            f"color:{_CYN};font-size:10px;font-weight:bold;"
            f"border:none;background:transparent;"))
        self._score_big = _lbl("--",
            f"color:{_GRN};font-size:32px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._score_big.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        vb.addWidget(self._score_big)
        self._grade_lbl = _lbl("--",
            f"color:{_GRN};font-size:20px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._grade_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        vb.addWidget(self._grade_lbl)
        self._worst_lbl = _lbl("Worst: --",
            f"color:{_MUT};font-size:9px;"
            f"border:none;background:transparent;")
        self._worst_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        vb.addWidget(self._worst_lbl)
        self._n_lbl = _lbl("Scenarios: 0",
            f"color:{_MUT};font-size:9px;"
            f"border:none;background:transparent;")
        self._n_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        vb.addWidget(self._n_lbl)
        vb.addStretch()
        return w

    def _build_results_table(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                        f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(10,8,10,8); vb.setSpacing(4)
        vb.addWidget(_lbl("Scenario Results",
            f"color:{_YLW};font-size:10px;font-weight:bold;"
            f"border:none;background:transparent;"))
        cols = ["Scenario","Max Drawdown","Survival Rate",
                "Exec Degradation","Fill Rate","Slippage(bps)","Score","Grade"]
        self._table = QtWidgets.QTableWidget(0, len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setStyleSheet(
            f"QTableWidget{{background:{_BG};color:{_FG};"
            f"border:none;font-size:9px;}}"
            f"QTableWidget::item{{padding:4px 8px;}}"
            f"QTableWidget::item:alternate{{background:#1a1a2e;}}"
            f"QTableWidget::item:selected{{background:{_HEAD};}}"
            f"QHeaderView::section{{background:{_HEAD};color:{_MUT};"
            f"border:none;border-right:1px solid {_BORDER};"
            f"font-size:9px;padding:4px 8px;}}")
        for i, w_ in enumerate([140,90,90,105,75,95,55,45]):
            self._table.setColumnWidth(i, w_)
        vb.addWidget(self._table)
        return w

    def _run_single(self):
        if not self._engine: return
        sc = self._scenario_cb.currentData()
        self._set_status(f"Running {sc} ...", _YLW)
        try:
            self._engine._stress_engine.configure(
                portfolio_value=self._pv_spin.value())
            r = self._engine.run_stress_test(sc, seed=42)
            self._append_result(r)
            self._set_status(
                f"Done: {sc}  score={r.get("survival_score",0):.1f}", _GRN)
        except Exception as e:
            self._set_status(f"Error: {e}", _RED)

    def _run_all(self):
        if not self._engine: return
        self._set_status("Running all 6 scenarios ...", _YLW)
        try:
            r    = self._engine.run_all_stress_scenarios()
            for res in r.get("scenarios", []):
                self._append_result(res)
            sc_d = r.get("survival_score", {})
            self._update_score(sc_d.get("score"), sc_d.get("grade","F"),
                               sc_d.get("worst_grade","F"),
                               sc_d.get("n_scenarios",0))
            self._set_status(
                f"All 6 complete  score={sc_d.get("score",0):.1f}"
                f"  grade={sc_d.get("grade","F")}", _GRN)
        except Exception as e:
            self._set_status(f"Error: {e}", _RED)

    def _get_score(self):
        if not self._engine: return
        try:
            sc = self._engine.get_survival_score()
            self._update_score(sc.get("score"), sc.get("grade","F"),
                               sc.get("worst_grade","F"),
                               sc.get("n_scenarios",0))
        except Exception as e:
            self._set_status(f"Error: {e}", _RED)

    def _clear_table(self):
        self._table.setRowCount(0)

    def _set_status(self, msg, color=_MUT):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(
            f"color:{color};font-size:9px;border:none;background:transparent;")

    def _append_result(self, d: dict):
        row = self._table.rowCount()
        self._table.insertRow(row)
        grade = d.get("survival_grade","F")
        gc    = _GRADE_COLORS.get(grade, _MUT)
        mdd   = d.get("max_drawdown", 0)
        surv  = d.get("survival_rate", 0)
        ed    = d.get("exec_degradation", 0)
        fr    = d.get("fill_rate_under_stress", 0)
        vals  = [
            (d.get("scenario_name", d.get("scenario_type","--")), _FG),
            (f"{mdd:.1%}",  _RED if mdd > 0.3 else _YLW),
            (f"{surv:.1%}", _GRN if surv > 0.8 else _YLW),
            (f"{ed:.3f}",   _RED if ed > 0.5 else _ORG),
            (f"{fr:.1%}",   _YLW if fr < 0.5 else _GRN),
            (f"{d.get('avg_slippage_stress_bps',0):.1f}", _ORG),
            (f"{d.get('survival_score',0):.1f}", gc),
            (grade, gc),
        ]
        for c, (val, color) in enumerate(vals):
            item = QtWidgets.QTableWidgetItem(val)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QtGui.QColor(color))
            self._table.setItem(row, c, item)
        self._table.scrollToBottom()

    def _update_score(self, score, grade, worst, n):
        if score is None: return
        gc = _GRADE_COLORS.get(grade, _MUT)
        wc = _GRADE_COLORS.get(worst, _MUT)
        self._score_big.setText(f"{score:.1f}")
        self._score_big.setStyleSheet(
            f"color:{gc};font-size:32px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._grade_lbl.setText(grade)
        self._grade_lbl.setStyleSheet(
            f"color:{gc};font-size:20px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._worst_lbl.setText(f"Worst: {worst}")
        self._worst_lbl.setStyleSheet(
            f"color:{wc};font-size:9px;border:none;background:transparent;")
        self._n_lbl.setText(f"Scenarios: {n}")

    def _on_started(self, event):
        d = event.data or {}
        self._set_status(f"Running {d.get('scenario','...')} ...", _YLW)

    def _on_completed(self, event):
        d = event.data or {}
        if d.get("status") == "ok":
            self._append_result(d)

    def _on_score(self, event):
        d = event.data or {}
        self._update_score(d.get("score"), d.get("grade","F"),
                           d.get("worst_grade","F"),
                           d.get("n_scenarios",0))

    def closeEvent(self, event):
        if self._event_engine:
            for ev, fn in self._subscriptions:
                try: self._event_engine.unregister(ev, fn)
                except Exception: pass
        super().closeEvent(event)
