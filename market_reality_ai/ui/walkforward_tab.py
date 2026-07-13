"""
market_reality_ai/ui/walkforward_tab.py

Phase 6: Walk-Forward Reality Engine Tab — complete implementation.
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import APP_NAME
from ..event import (
    EVENT_WALKFORWARD_STARTED, EVENT_WALKFORWARD_UPDATED,
    EVENT_WALKFORWARD_COMPLETED,
)

_BG="#1e1e2e";_DARK="#181825";_BORDER="#45475a";_FG="#cdd6f4"
_MUT="#6c7086";_HEAD="#313244";_GRN="#a6e3a1";_YLW="#f9e2af"
_RED="#f38ba8";_ORG="#fab387";_MAV="#cba6f7";_CYN="#89dceb"
_TEA="#94e2d5"
_RC={"low_vol":_TEA,"normal":_GRN,"stressed":_YLW,"crisis":_RED}

def _lbl(t,s=""):
    w=QtWidgets.QLabel(t); w.setStyleSheet(s); return w


class WalkForwardTab(QtWidgets.QWidget):
    """Phase 6: Walk-Forward Reality Engine tab."""

    def __init__(self, main_engine=None, event_engine=None, parent=None):
        super().__init__(parent)
        self._engine = main_engine.get_engine(APP_NAME) if main_engine else None
        self._event_engine = event_engine
        self._subscriptions = []
        self._init_ui()
        if event_engine:
            for ev, fn in [
                (EVENT_WALKFORWARD_STARTED,   self._on_started),
                (EVENT_WALKFORWARD_UPDATED,   self._on_updated),
                (EVENT_WALKFORWARD_COMPLETED, self._on_completed),
            ]:
                event_engine.register(ev, fn)
                self._subscriptions.append((ev, fn))

    def _init_ui(self):
        self.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(self)
        vb.setContentsMargins(10,10,10,10); vb.setSpacing(8)
        top = QtWidgets.QHBoxLayout(); top.setSpacing(8)
        top.addWidget(self._build_controls(), stretch=1)
        top.addWidget(self._build_summary_card(), stretch=0)
        vb.addLayout(top)
        vb.addWidget(self._build_window_table(), stretch=1)
        self._status_lbl = _lbl("Ready",
            f"color:{_MUT};font-size:9px;border:none;background:transparent;")
        vb.addWidget(self._status_lbl)

    def _build_controls(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                        f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(14,12,14,12); vb.setSpacing(8)
        vb.addWidget(_lbl("Walk-Forward Parameters",
            f"color:{_YLW};font-size:11px;font-weight:bold;"
            f"border:none;background:transparent;"))
        grid = QtWidgets.QGridLayout(); grid.setSpacing(8)
        self._spins: dict[str, QtWidgets.QSpinBox] = {}
        for row, (lbl, key, val, lo, hi) in enumerate([
            ("Window Days", "window_days", 60,  5, 252),
            ("Step Days",   "step_days",   10,  1,  60),
            ("Num Windows", "n_windows",   12,  2,  52),
        ]):
            grid.addWidget(_lbl(f"{lbl}:",
                f"color:{_MUT};font-size:9px;"
                f"border:none;background:transparent;"), row, 0)
            sp = QtWidgets.QSpinBox()
            sp.setRange(lo, hi); sp.setValue(val)
            sp.setStyleSheet(
                f"QSpinBox{{background:{_BG};color:{_FG};"
                f"border:1px solid {_BORDER};border-radius:3px;"
                f"padding:2px 6px;font-size:9px;}}")
            grid.addWidget(sp, row, 1)
            self._spins[key] = sp
        vb.addLayout(grid)
        btn_row = QtWidgets.QHBoxLayout(); btn_row.setSpacing(8)
        for label, color, slot in [
            ("▶  Run Walk-Forward", _GRN, self._run_wf),
            ("⟳  Refresh State",   _MAV, self._refresh),
            ("✕  Clear",           _MUT, self._clear_table),
        ]:
            b = QtWidgets.QPushButton(label); b.setFixedHeight(28)
            b.setStyleSheet(
                f"QPushButton{{background:{color};color:#1e1e2e;"
                f"font-weight:bold;border:none;border-radius:3px;"
                f"padding:0 10px;font-size:9px;}}"
                f"QPushButton:disabled{{background:{_BORDER};color:{_MUT};}}")
            b.clicked.connect(slot); btn_row.addWidget(b)
        btn_row.addStretch(); vb.addLayout(btn_row)
        return w

    def _build_summary_card(self):
        w = QtWidgets.QWidget(); w.setFixedWidth(200)
        w.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                        f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(14,14,14,14); vb.setSpacing(6)
        vb.addWidget(_lbl("Reality Gap Summary",
            f"color:{_MAV};font-size:10px;font-weight:bold;"
            f"border:none;background:transparent;"))
        self._kpis: dict[str, QtWidgets.QLabel] = {}
        for key, lbl, color in [
            ("gap_score","Gap Score",    _GRN),
            ("avg_gap",  "Avg Gap(bps)", _YLW),
            ("worst_gap","Worst Gap",    _RED),
            ("best_gap", "Best Gap",     _GRN),
            ("n_windows","Windows",      _CYN),
        ]:
            cell = QtWidgets.QWidget()
            cell.setStyleSheet("background:transparent;border:none;")
            cv = QtWidgets.QVBoxLayout(cell)
            cv.setContentsMargins(0,0,0,0); cv.setSpacing(1)
            cv.addWidget(_lbl(lbl,f"color:{_MUT};font-size:8px;"
                f"border:none;background:transparent;"))
            lv = _lbl("--",f"color:{color};font-size:13px;"
                f"font-weight:bold;border:none;background:transparent;")
            cv.addWidget(lv); self._kpis[key] = lv; vb.addWidget(cell)
        vb.addWidget(_lbl("Regime Breakdown",
            f"color:{_MUT};font-size:8px;"
            f"border:none;background:transparent;"))
        self._rtable = QtWidgets.QTableWidget(4, 2)
        self._rtable.setHorizontalHeaderLabels(["Regime","Avg Gap"])
        self._rtable.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._rtable.verticalHeader().setVisible(False)
        self._rtable.horizontalHeader().setStretchLastSection(True)
        self._rtable.setShowGrid(False); self._rtable.setFixedHeight(98)
        self._rtable.setStyleSheet(
            f"QTableWidget{{background:{_BG};color:{_FG};"
            f"border:none;font-size:8px;}}"
            f"QTableWidget::item{{padding:2px 4px;}}"
            f"QHeaderView::section{{background:{_HEAD};color:{_MUT};"
            f"border:none;font-size:8px;padding:2px 4px;}}")
        self._rtable.setColumnWidth(0, 75)
        for r, reg in enumerate(["low_vol","normal","stressed","crisis"]):
            it0 = QtWidgets.QTableWidgetItem(reg)
            it0.setForeground(QtGui.QColor(_RC.get(reg,_FG)))
            it1 = QtWidgets.QTableWidgetItem("--")
            it1.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self._rtable.setItem(r,0,it0); self._rtable.setItem(r,1,it1)
        vb.addWidget(self._rtable); vb.addStretch()
        return w

    def _build_window_table(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                        f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(10,8,10,8); vb.setSpacing(4)
        vb.addWidget(_lbl("Rolling Windows",
            f"color:{_YLW};font-size:10px;font-weight:bold;"
            f"border:none;background:transparent;"))
        cols=["Window","Start","End","Regime","Backtest Ret",
              "Realized Ret","Gap(bps)","Slip Drag","Impact Drag","Trades"]
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
            f"QTableWidget::item{{padding:3px 6px;}}"
            f"QTableWidget::item:alternate{{background:#1a1a2e;}}"
            f"QTableWidget::item:selected{{background:{_HEAD};}}"
            f"QHeaderView::section{{background:{_HEAD};color:{_MUT};"
            f"border:none;border-right:1px solid {_BORDER};"
            f"font-size:9px;padding:3px 6px;}}")
        for i, w_ in enumerate([90,80,80,75,90,90,70,75,80,50]):
            self._table.setColumnWidth(i, w_)
        vb.addWidget(self._table)
        return w

    def _run_wf(self):
        if not self._engine: return
        wd = self._spins["window_days"].value()
        sd = self._spins["step_days"].value()
        nw = self._spins["n_windows"].value()
        self._set_status(f"Running {nw} windows ...", _YLW)
        try:
            r = self._engine.run_walk_forward(
                window_days=wd, step_days=sd, n_windows=nw, seed=42)
            self._populate(r)
            self._set_status(
                f"Done: {nw} windows  "
                f"avg_gap={r.get('avg_reality_gap',0):.1f}bps  "
                f"score={r.get('reality_gap_score',0):.1f}", _GRN)
        except Exception as e:
            self._set_status(f"Error: {e}", _RED)

    def _refresh(self):
        if not self._engine: return
        try:
            r = self._engine.get_walkforward_state()
            self._update_kpis(r)
        except Exception as e:
            self._set_status(f"Error: {e}", _RED)

    def _clear_table(self):
        self._table.setRowCount(0)

    def _set_status(self, msg, color=_MUT):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(
            f"color:{color};font-size:9px;border:none;background:transparent;")

    def _populate(self, r: dict):
        self._table.setRowCount(0)
        for win in r.get("windows", []):
            self._append_window(win)
        self._update_kpis(r)

    def _append_window(self, w: dict):
        row = self._table.rowCount()
        self._table.insertRow(row)
        regime = w.get("regime", "normal")
        rc     = _RC.get(regime, _FG)
        gap    = w.get("reality_gap_bps", 0.0)
        bt     = w.get("backtest_return",  0.0)
        rz     = w.get("realized_return",  0.0)
        gc     = _RED if gap > 50 else (_YLW if gap > 20 else _GRN)
        vals = [
            (w.get("window_id","")[:10],               _MUT),
            (w.get("start_date",""),                    _FG),
            (w.get("end_date",""),                      _FG),
            (regime,                                    rc),
            (f"{bt:.2%}",  _GRN if bt > 0 else _RED),
            (f"{rz:.2%}",  _GRN if rz > 0 else _RED),
            (f"{gap:.1f}", gc),
            (f"{w.get('slippage_drag_bps',0):.1f}", _YLW),
            (f"{w.get('impact_drag_bps',0):.1f}",   _ORG),
            (str(w.get("n_trades", 0)),              _CYN),
        ]
        for c, (val, color) in enumerate(vals):
            item = QtWidgets.QTableWidgetItem(val)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QtGui.QColor(color))
            self._table.setItem(row, c, item)
        self._table.scrollToBottom()

    def _update_kpis(self, r: dict):
        ag = r.get("avg_reality_gap",   0.0)
        sc = r.get("reality_gap_score", 0.0)
        wg = r.get("worst_gap",         0.0)
        bg = r.get("best_gap",          0.0)
        n  = r.get("total_windows",     0)
        gap_c = _RED if abs(ag) > 50 else (_YLW if abs(ag) > 20 else _GRN)
        sc_c  = _GRN if sc > 70 else (_YLW if sc > 50 else _RED)
        for key, val, color in [
            ("gap_score", f"{sc:.1f}", sc_c),
            ("avg_gap",   f"{ag:.1f}", gap_c),
            ("worst_gap", f"{wg:.1f}", _RED),
            ("best_gap",  f"{bg:.1f}", _GRN),
            ("n_windows", str(n),      _CYN),
        ]:
            lv = self._kpis.get(key)
            if lv:
                lv.setText(val)
                lv.setStyleSheet(
                    f"color:{color};font-size:13px;font-weight:bold;"
                    f"border:none;background:transparent;")
        rbd = r.get("regime_breakdown", {})
        for row, reg in enumerate(["low_vol","normal","stressed","crisis"]):
            val  = rbd.get(reg)
            txt  = f"{val:.1f}bps" if val is not None else "--"
            clr  = _RC.get(reg, _FG)
            item = QtWidgets.QTableWidgetItem(txt)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QtGui.QColor(clr))
            self._rtable.setItem(row, 1, item)

    def _on_started(self, event):
        d = event.data or {}
        self._set_status(
            f"Running {d.get('n_windows','?')} windows ...", _YLW)

    def _on_updated(self, event):
        self._update_kpis(event.data or {})

    def _on_completed(self, event):
        d = event.data or {}
        self._update_kpis(d)
        self._set_status(
            f"Completed: {d.get('total_windows',0)} windows  "
            f"avg={d.get('avg_reality_gap',0):.1f}bps  "
            f"score={d.get('reality_gap_score',0):.1f}", _GRN)

    def closeEvent(self, event):
        if self._event_engine:
            for ev, fn in self._subscriptions:
                try: self._event_engine.unregister(ev, fn)
                except Exception: pass
        super().closeEvent(event)
