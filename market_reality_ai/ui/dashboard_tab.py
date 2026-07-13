"""
market_reality_ai/ui/dashboard_tab.py

Phase 6: Reality Simulation Dashboard — system-wide overview.
"""
from __future__ import annotations
from datetime import datetime

from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import APP_NAME
from ..event import (
    EVENT_EXECUTION_SIMULATED, EVENT_STRESS_TEST_COMPLETED,
    EVENT_WALKFORWARD_COMPLETED, EVENT_FAILURE_MODE_DETECTED,
    EVENT_SURVIVAL_SCORE_UPDATED,
    EVENT_REALITY_STARTED, EVENT_REALITY_STOPPED,
)

_BG="#1e1e2e";_DARK="#181825";_BORDER="#45475a";_FG="#cdd6f4"
_MUT="#6c7086";_HEAD="#313244";_GRN="#a6e3a1";_YLW="#f9e2af"
_RED="#f38ba8";_ORG="#fab387";_MAV="#cba6f7";_CYN="#89dceb"
_TEA="#94e2d5";_BLUE="#89b4fa"

def _lbl(t, s=""):
    w=QtWidgets.QLabel(t); w.setStyleSheet(s); return w

def _sep():
    f=QtWidgets.QFrame()
    f.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    f.setStyleSheet(f"background:{_BORDER};border:none;"); return f


class DashboardTab(QtWidgets.QWidget):
    """Phase 6: System-wide simulation overview dashboard."""

    def __init__(self, main_engine=None, event_engine=None, parent=None):
        super().__init__(parent)
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine = main_engine.get_engine(APP_NAME) if main_engine else None
        self._subscriptions = []
        self._init_ui()
        if event_engine:
            for ev, fn in [
                (EVENT_REALITY_STARTED,       self._on_started),
                (EVENT_REALITY_STOPPED,       self._on_stopped),
                (EVENT_EXECUTION_SIMULATED,   self._on_exec),
                (EVENT_STRESS_TEST_COMPLETED, self._on_stress),
                (EVENT_WALKFORWARD_COMPLETED, self._on_wf),
                (EVENT_FAILURE_MODE_DETECTED, self._on_failure),
                (EVENT_SURVIVAL_SCORE_UPDATED,self._on_score),
            ]:
                event_engine.register(ev, fn)
                self._subscriptions.append((ev, fn))

    def _init_ui(self):
        self.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(self)
        vb.setContentsMargins(10,10,10,10); vb.setSpacing(8)
        vb.addWidget(self._build_survival_panel())
        cards = QtWidgets.QHBoxLayout(); cards.setSpacing(8)
        self._mod_cards: dict[str, dict] = {}
        for key, title, color in [
            ("execution","Execution Reality",_YLW),
            ("impact",   "Market Impact",    _CYN),
            ("stress",   "Stress Testing",   _ORG),
            ("wf",       "Walk-Forward",     _MAV),
            ("failure",  "Failure Mode",     _RED),
        ]:
            cards.addWidget(self._build_module_card(key, title, color))
        vb.addLayout(cards)
        vb.addWidget(self._build_metrics_table())

    def _build_survival_panel(self):
        w = QtWidgets.QWidget(); w.setFixedHeight(90)
        w.setStyleSheet(f"background:{_HEAD};border-radius:6px;"
                        f"border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(20,10,20,10); h.setSpacing(20)
        score_w = QtWidgets.QWidget()
        score_w.setStyleSheet("background:transparent;border:none;")
        sv = QtWidgets.QVBoxLayout(score_w)
        sv.setContentsMargins(0,0,0,0); sv.setSpacing(2)
        sv.addWidget(_lbl("SYSTEM SURVIVAL SCORE",
            f"color:{_MUT};font-size:9px;font-weight:bold;"
            f"border:none;background:transparent;"))
        self._big_score = _lbl("--",
            f"color:{_GRN};font-size:36px;font-weight:bold;"
            f"border:none;background:transparent;")
        sv.addWidget(self._big_score)
        h.addWidget(score_w)
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        sep.setStyleSheet(f"background:{_BORDER};border:none;")
        h.addWidget(sep)
        for key, label, color in [
            ("grade", "Grade",         _GRN),
            ("phase", "Active Phase",  _YLW),
            ("status","Engine Status", _CYN),
        ]:
            cell = QtWidgets.QWidget()
            cell.setStyleSheet("background:transparent;border:none;")
            cv = QtWidgets.QVBoxLayout(cell)
            cv.setContentsMargins(0,0,0,0); cv.setSpacing(2)
            cv.addWidget(_lbl(label,
                f"color:{_MUT};font-size:9px;"
                f"border:none;background:transparent;"))
            lv = _lbl("--",
                f"color:{color};font-size:16px;font-weight:bold;"
                f"border:none;background:transparent;")
            cv.addWidget(lv)
            setattr(self, f"_dash_{key}", lv)
            h.addWidget(cell)
        h.addStretch()
        self._dash_phase.setText("Phase 5")
        self._dash_status.setText("IDLE")
        return w

    def _build_module_card(self, key, title, color):
        card = QtWidgets.QWidget()
        card.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                           f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(card)
        vb.setContentsMargins(12,10,12,10); vb.setSpacing(4)
        vb.addWidget(_lbl(title,
            f"color:{color};font-size:10px;font-weight:bold;"
            f"border:none;background:transparent;"))
        vb.addWidget(_sep())
        dot_row = QtWidgets.QHBoxLayout(); dot_row.setSpacing(6)
        dot = _lbl("●",f"color:{_BORDER};font-size:12px;"
                   f"border:none;background:transparent;")
        stat = _lbl("inactive",f"color:{_MUT};font-size:9px;"
                    f"border:none;background:transparent;")
        dot_row.addWidget(dot); dot_row.addWidget(stat); dot_row.addStretch()
        vb.addLayout(dot_row)
        metrics: dict[str, QtWidgets.QLabel] = {}
        rows_map = {
            "execution":[("Simulations","--"),("Avg Slip","--"),("Fill Rate","--")],
            "impact":   [("Estimates",  "--"),("Avg Cost","--"),("Avg Temp", "--")],
            "stress":   [("Tests Run",  "--"),("Score",   "--"),("Grade",    "--")],
            "wf":       [("Windows",    "--"),("Avg Gap", "--"),("Gap Score","--")],
            "failure":  [("Active",     "--"),("Cascade", "--"),("Fatal",    "--")],
        }
        for label, default in rows_map.get(key, []):
            row = QtWidgets.QHBoxLayout(); row.setSpacing(4)
            row.addWidget(_lbl(f"{label}:",
                f"color:{_MUT};font-size:8px;border:none;background:transparent;"))
            row.addStretch()
            val = _lbl(default,
                f"color:{color};font-size:9px;font-weight:bold;"
                f"border:none;background:transparent;")
            row.addWidget(val)
            metrics[label] = val
            vb.addLayout(row)
        vb.addStretch()
        self._mod_cards[key] = {"dot":dot,"status":stat,
                                 "metrics":metrics,"color":color}
        return card

    def _build_metrics_table(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                        f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(12,8,12,8); vb.setSpacing(6)
        vb.addWidget(_lbl("Full System Metrics",
            f"color:{_YLW};font-size:10px;font-weight:bold;"
            f"border:none;background:transparent;"))
        cols = ["Metric","Ph2 Execution","Ph3 Impact",
                "Ph4 Stress","Ph4 WalkFwd","Ph5 Failure"]
        self._metrics_table = QtWidgets.QTableWidget(5, len(cols))
        self._metrics_table.setHorizontalHeaderLabels(cols)
        self._metrics_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._metrics_table.verticalHeader().setVisible(False)
        self._metrics_table.horizontalHeader().setStretchLastSection(True)
        self._metrics_table.setShowGrid(False)
        self._metrics_table.setAlternatingRowColors(True)
        self._metrics_table.setFixedHeight(142)
        self._metrics_table.setStyleSheet(
            f"QTableWidget{{background:{_BG};color:{_FG};"
            f"border:none;font-size:9px;}}"
            f"QTableWidget::item{{padding:3px 6px;}}"
            f"QTableWidget::item:alternate{{background:#1a1a2e;}}"
            f"QHeaderView::section{{background:{_HEAD};color:{_MUT};"
            f"border:none;border-right:1px solid {_BORDER};"
            f"font-size:9px;padding:3px 6px;}}")
        for i, w_ in enumerate([130,90,90,110,90,90]):
            self._metrics_table.setColumnWidth(i, w_)
        for r, row_data in enumerate([
            ("Simulations / Estimates","--","--","--","--","--"),
            ("Avg Slippage / Impact",  "--","--","--","--","--"),
            ("Fill Rate / Score",      "--","--","--","--","--"),
            ("Rejection / Grade",      "--","--","--","--","--"),
            ("Gap / Cascade / Fatal",  "--","--","--","--","--"),
        ]):
            for c, val in enumerate(row_data):
                item = QtWidgets.QTableWidgetItem(val)
                item.setTextAlignment(
                    QtCore.Qt.AlignmentFlag.AlignCenter)
                self._metrics_table.setItem(r, c, item)
        vb.addWidget(self._metrics_table)
        self._last_updated = _lbl("Last updated: --",
            f"color:{_MUT};font-size:8px;"
            f"border:none;background:transparent;")
        vb.addWidget(self._last_updated)
        return w

    def _set_card_active(self, key, active):
        c = self._mod_cards.get(key)
        if not c: return
        color = c["color"] if active else _BORDER
        c["dot"].setStyleSheet(
            f"color:{color};font-size:12px;"
            f"border:none;background:transparent;")
        c["status"].setText("active" if active else "inactive")
        c["status"].setStyleSheet(
            f"color:{color};font-size:9px;"
            f"border:none;background:transparent;")

    def _set_card_metric(self, key, metric, value):
        c = self._mod_cards.get(key)
        if c:
            m = c["metrics"].get(metric)
            if m: m.setText(value)

    def _set_table_cell(self, row, col, val, color=_FG):
        item = QtWidgets.QTableWidgetItem(val)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QtGui.QColor(color))
        self._metrics_table.setItem(row, col, item)

    def _now(self): return str(datetime.now())[11:19]

    def _on_started(self, event):
        d = event.data or {}
        self._dash_status.setText("RUNNING")
        self._dash_status.setStyleSheet(
            f"color:{_GRN};font-size:16px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._dash_phase.setText(f"Phase {d.get('phase',5)}")

    def _on_stopped(self, event):
        self._dash_status.setText("IDLE")
        self._dash_status.setStyleSheet(
            f"color:{_MUT};font-size:16px;font-weight:bold;"
            f"border:none;background:transparent;")

    def _on_exec(self, event):
        d  = event.data or {}
        es = d.get("execution_state", {})
        n   = es.get("total_simulations", 0)
        sl  = es.get("avg_slippage_bps",  0.0)
        fr  = es.get("avg_fill_rate",     0.0)
        rej = es.get("rejection_rate",    0.0)
        self._set_card_active("execution", True)
        self._set_card_metric("execution","Simulations",str(n))
        self._set_card_metric("execution","Avg Slip",f"{sl:.2f}bps")
        self._set_card_metric("execution","Fill Rate",f"{fr:.1%}")
        self._set_table_cell(0,1,str(n))
        self._set_table_cell(1,1,f"{sl:.2f}bps",_YLW)
        self._set_table_cell(2,1,f"{fr:.1%}",_GRN)
        self._set_table_cell(3,1,f"{rej:.1%}",_RED if rej>0.1 else _FG)
        self._last_updated.setText(f"Last updated: {self._now()}")

    def _on_stress(self, event):
        d  = event.data or {}
        st = d.get("stress_state", {})
        n  = st.get("total_tests",  0)
        sc = st.get("system_score", 0.0)
        gr = st.get("system_grade", "F")
        gc = {"S":_GRN,"A":_TEA,"B":_YLW,"C":_ORG,"F":_RED}.get(gr,_MUT)
        self._set_card_active("stress", True)
        self._set_card_metric("stress","Tests Run",str(n))
        self._set_card_metric("stress","Score",f"{sc:.1f}")
        self._set_card_metric("stress","Grade",gr)
        self._set_table_cell(0,3,str(n))
        self._set_table_cell(1,3,f"{sc:.1f}",gc)
        self._set_table_cell(2,3,gr,gc)
        self._last_updated.setText(f"Last updated: {self._now()}")

    def _on_wf(self, event):
        d  = event.data or {}
        n  = d.get("total_windows",    0)
        ag = d.get("avg_reality_gap",  0.0)
        sc = d.get("reality_gap_score",0.0)
        self._set_card_active("wf", True)
        self._set_card_metric("wf","Windows",  str(n))
        self._set_card_metric("wf","Avg Gap",  f"{ag:.1f}bps")
        self._set_card_metric("wf","Gap Score", f"{sc:.1f}")
        self._set_table_cell(0,4,str(n))
        gap_c = _RED if abs(ag)>50 else (_YLW if abs(ag)>20 else _GRN)
        self._set_table_cell(4,4,f"{ag:.1f}bps",gap_c)
        self._last_updated.setText(f"Last updated: {self._now()}")

    def _on_failure(self, event):
        d  = event.data or {}
        fs = d.get("failure_state", {})
        n  = fs.get("active_count", 0)
        cr = fs.get("cascade_risk", 0.0)
        ft = fs.get("is_fatal",     False)
        self._set_card_active("failure", n > 0)
        self._set_card_metric("failure","Active",  str(n))
        self._set_card_metric("failure","Cascade", f"{cr:.3f}")
        self._set_card_metric("failure","Fatal",   "YES" if ft else "no")
        self._set_table_cell(0,5,str(n),_RED if n>0 else _FG)
        cr_c = _RED if cr>0.5 else (_ORG if cr>0.2 else _FG)
        self._set_table_cell(3,5,f"{cr:.3f}",cr_c)
        self._set_table_cell(4,5,"FATAL" if ft else "--",
                              _RED if ft else _FG)
        self._last_updated.setText(f"Last updated: {self._now()}")

    def _on_score(self, event):
        d     = event.data or {}
        score = d.get("score")
        grade = d.get("grade","F")
        if score is not None:
            gc = {"S":_GRN,"A":_TEA,"B":_YLW,"C":_ORG,"F":_RED}.get(grade,_MUT)
            self._big_score.setText(f"{score:.1f}")
            self._big_score.setStyleSheet(
                f"color:{gc};font-size:36px;font-weight:bold;"
                f"border:none;background:transparent;")
            self._dash_grade.setText(grade)
            self._dash_grade.setStyleSheet(
                f"color:{gc};font-size:16px;font-weight:bold;"
                f"border:none;background:transparent;")

    def closeEvent(self, event):
        if self._event_engine:
            for ev, fn in self._subscriptions:
                try: self._event_engine.unregister(ev, fn)
                except Exception: pass
        super().closeEvent(event)
