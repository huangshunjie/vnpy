"""
market_reality_ai/ui/failure_tab.py

Phase 6: Failure Mode Analysis Engine Tab — complete implementation.
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from ..constant import APP_NAME
from ..event import (
    EVENT_FAILURE_MODE_DETECTED, EVENT_FAILURE_REPORT_READY,
)

_BG="#1e1e2e";_DARK="#181825";_BORDER="#45475a";_FG="#cdd6f4"
_MUT="#6c7086";_HEAD="#313244";_GRN="#a6e3a1";_YLW="#f9e2af"
_RED="#f38ba8";_ORG="#fab387";_MAV="#cba6f7";_CYN="#89dceb"
_TEA="#94e2d5"

_SEV_COLORS={1:_GRN,2:_YLW,3:_ORG,4:_RED,5:"#ff0000"}
_SEV_NAMES={1:"LOW",2:"MEDIUM",3:"HIGH",4:"CRITICAL",5:"FATAL"}

def _lbl(t,s=""):
    w=QtWidgets.QLabel(t); w.setStyleSheet(s); return w


class FailureTab(QtWidgets.QWidget):
    """Phase 6: Failure Mode Analysis Engine tab."""

    def __init__(self, main_engine=None, event_engine=None, parent=None):
        super().__init__(parent)
        self._engine = main_engine.get_engine(APP_NAME) if main_engine else None
        self._event_engine = event_engine
        self._subscriptions = []
        self._init_ui()
        if event_engine:
            for ev, fn in [
                (EVENT_FAILURE_MODE_DETECTED, self._on_failure),
                (EVENT_FAILURE_REPORT_READY,  self._on_report),
            ]:
                event_engine.register(ev, fn)
                self._subscriptions.append((ev, fn))

    def _init_ui(self):
        self.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(self)
        vb.setContentsMargins(10,10,10,10); vb.setSpacing(8)

        top = QtWidgets.QHBoxLayout(); top.setSpacing(8)
        top.addWidget(self._build_controls(),   stretch=1)
        top.addWidget(self._build_status_card(),stretch=0)
        vb.addLayout(top)

        mid = QtWidgets.QHBoxLayout(); mid.setSpacing(8)
        mid.addWidget(self._build_active_table(), stretch=2)
        mid.addWidget(self._build_cascade_panel(), stretch=1)
        vb.addLayout(mid)

        vb.addWidget(self._build_event_log(), stretch=1)

        self._status_lbl = _lbl(
            '"Not to simulate profit — to simulate death"',
            f"color:{_MUT};font-size:9px;font-style:italic;"
            f"border:none;background:transparent;")
        vb.addWidget(self._status_lbl)

    # ── control panel ─────────────────────────────────────────────────
    def _build_controls(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                        f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(14,12,14,12); vb.setSpacing(8)
        vb.addWidget(_lbl("Failure Mode Analysis Controls",
            f"color:{_RED};font-size:11px;font-weight:bold;"
            f"border:none;background:transparent;"))

        # context sliders / spinboxes
        grid = QtWidgets.QGridLayout(); grid.setSpacing(6)
        self._ctx: dict[str, QtWidgets.QWidget] = {}

        def _dspin(lo, hi, val, step=1.0):
            s = QtWidgets.QDoubleSpinBox()
            s.setRange(lo, hi); s.setValue(val); s.setSingleStep(step)
            s.setStyleSheet(
                f"QDoubleSpinBox{{background:{_BG};color:{_FG};"
                f"border:1px solid {_BORDER};border-radius:3px;"
                f"padding:2px 6px;font-size:9px;min-width:80px;}}")
            return s

        params = [
            ("latency_ms",      "Latency (ms)",      0.0,  50000.0, 100.0,  500.0),
            ("rejection_rate",  "Rejection Rate",     0.0,  1.0,     0.0,    0.05),
            ("fill_rate",       "Fill Rate",          0.0,  1.0,     0.95,   0.05),
            ("spread_bps",      "Spread (bps)",       0.0,  500.0,   5.0,    5.0),
            ("market_depth",    "Market Depth",       0.0,  1.0,     0.9,    0.05),
            ("drawdown",        "Drawdown",           0.0,  0.99,    0.05,   0.01),
            ("leverage",        "Leverage",           0.5,  20.0,    1.5,    0.5),
            ("signal_quality",  "Signal Quality",     0.0,  1.0,     0.8,    0.05),
            ("cpu_pct",         "CPU %",              0.0,  100.0,   30.0,   5.0),
            ("mem_pct",         "Memory %",           0.0,  100.0,   40.0,   5.0),
        ]
        for i, (key, label, lo, hi, val, step) in enumerate(params):
            r, c = divmod(i, 2)
            grid.addWidget(_lbl(f"{label}:",
                f"color:{_MUT};font-size:8px;"
                f"border:none;background:transparent;"),
                r, c*3)
            sp = _dspin(lo, hi, val, step)
            grid.addWidget(sp, r, c*3+1)
            self._ctx[key] = sp

        vb.addLayout(grid)

        # regime selector
        reg_row = QtWidgets.QHBoxLayout(); reg_row.setSpacing(8)
        reg_row.addWidget(_lbl("Regime:",
            f"color:{_MUT};font-size:9px;border:none;background:transparent;"))
        self._regime_cb = QtWidgets.QComboBox()
        self._regime_cb.setStyleSheet(
            f"QComboBox{{background:{_BG};color:{_FG};"
            f"border:1px solid {_BORDER};border-radius:3px;"
            f"padding:2px 8px;font-size:9px;}}"
            f"QComboBox::drop-down{{border:none;}}"
            f"QComboBox QAbstractItemView{{background:{_HEAD};color:{_FG};"
            f"border:1px solid {_BORDER};}}")
        for regime in ["normal","stressed","illiquid","crisis"]:
            self._regime_cb.addItem(regime)
        reg_row.addWidget(self._regime_cb); reg_row.addStretch()
        vb.addLayout(reg_row)

        # buttons
        btn_row = QtWidgets.QHBoxLayout(); btn_row.setSpacing(8)
        for label, color, slot in [
            ("▶  Analyze Failures", _RED,  self._run_analyze),
            ("⟳  Get Report",      _ORG,  self._get_report),
            ("⟳  Detect Cascade",  _MAV,  self._detect_cascade),
            ("✕  Clear Failures",  _MUT,  self._clear_failures),
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

    # ── status card ───────────────────────────────────────────────────
    def _build_status_card(self):
        w = QtWidgets.QWidget(); w.setFixedWidth(190)
        w.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                        f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(14,14,14,14); vb.setSpacing(8)
        vb.addWidget(_lbl("Failure Status",
            f"color:{_RED};font-size:10px;font-weight:bold;"
            f"border:none;background:transparent;"))

        self._fatal_banner = _lbl("⬡  SYSTEM OK",
            f"color:{_GRN};font-size:12px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._fatal_banner.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        vb.addWidget(self._fatal_banner)

        self._fkpis: dict[str, QtWidgets.QLabel] = {}
        for key, lbl, color in [
            ("active",    "Active Failures", _RED),
            ("max_sev",   "Max Severity",    _ORG),
            ("cascade",   "Cascade Risk",    _MAV),
            ("depth",     "Cascade Depth",   _MAV),
            ("score",     "System Score",    _RED),
        ]:
            cell = QtWidgets.QWidget()
            cell.setStyleSheet("background:transparent;border:none;")
            cv = QtWidgets.QVBoxLayout(cell)
            cv.setContentsMargins(0,0,0,0); cv.setSpacing(1)
            cv.addWidget(_lbl(lbl,
                f"color:{_MUT};font-size:8px;"
                f"border:none;background:transparent;"))
            lv = _lbl("--",
                f"color:{color};font-size:13px;font-weight:bold;"
                f"border:none;background:transparent;")
            cv.addWidget(lv); self._fkpis[key]=lv; vb.addWidget(cell)

        # fatal combos list
        vb.addWidget(_lbl("Fatal Combos:",
            f"color:{_MUT};font-size:8px;"
            f"border:none;background:transparent;"))
        self._fatal_list = QtWidgets.QListWidget()
        self._fatal_list.setFixedHeight(60)
        self._fatal_list.setStyleSheet(
            f"QListWidget{{background:{_BG};color:{_RED};"
            f"border:1px solid {_BORDER};border-radius:2px;"
            f"font-size:8px;}}"
            f"QListWidget::item{{padding:2px 4px;}}")
        vb.addWidget(self._fatal_list)
        vb.addStretch()
        return w

    # ── active failures table ─────────────────────────────────────────
    def _build_active_table(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                        f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(10,8,10,8); vb.setSpacing(4)
        vb.addWidget(_lbl("Active Failure Modes",
            f"color:{_RED};font-size:10px;font-weight:bold;"
            f"border:none;background:transparent;"))
        cols=["Failure ID","Type","Severity","Trigger",
              "Value","Score","Cascade Risk","Impact"]
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
        for i,w_ in enumerate([90,120,75,110,70,60,85,0]):
            self._table.setColumnWidth(i, w_)
        vb.addWidget(self._table)
        return w

    # ── cascade panel ─────────────────────────────────────────────────
    def _build_cascade_panel(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                        f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(12,10,12,10); vb.setSpacing(6)
        vb.addWidget(_lbl("Cascade Analysis",
            f"color:{_MAV};font-size:10px;font-weight:bold;"
            f"border:none;background:transparent;"))

        self._cascade_txt = QtWidgets.QPlainTextEdit()
        self._cascade_txt.setReadOnly(True)
        self._cascade_txt.setFont(QtGui.QFont("Consolas", 8))
        self._cascade_txt.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_MAV};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        self._cascade_txt.setPlainText(
            "No cascade analysis yet.\n\nRun 'Analyze Failures' or\n'Detect Cascade' to see results.")
        vb.addWidget(self._cascade_txt)
        return w

    # ── event log ────────────────────────────────────────────────────
    def _build_event_log(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_HEAD};border-radius:5px;"
                        f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(10,8,10,8); vb.setSpacing(4)
        hdr = QtWidgets.QHBoxLayout()
        hdr.addWidget(_lbl("Failure Event Log",
            f"color:{_YLW};font-size:10px;font-weight:bold;"
            f"border:none;background:transparent;"))
        hdr.addStretch()
        clr = QtWidgets.QPushButton("Clear")
        clr.setFixedHeight(22)
        clr.setStyleSheet(
            f"QPushButton{{background:{_BORDER};color:{_FG};"
            f"border:none;border-radius:3px;font-size:8px;padding:0 6px;}}")
        clr.clicked.connect(lambda: self._event_log.clear())
        hdr.addWidget(clr)
        vb.addLayout(hdr)
        self._event_log = QtWidgets.QPlainTextEdit()
        self._event_log.setReadOnly(True)
        self._event_log.setMaximumBlockCount(500)
        self._event_log.setFont(QtGui.QFont("Consolas", 8))
        self._event_log.setFixedHeight(100)
        self._event_log.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        vb.addWidget(self._event_log)
        return w

    # ── slots ─────────────────────────────────────────────────────────
    def _run_analyze(self):
        if not self._engine: return
        ctx = {k: w.value() for k, w in self._ctx.items()}
        ctx["regime"] = self._regime_cb.currentText()
        self._set_status("Analyzing failure modes ...", _YLW)
        try:
            r = self._engine.analyze_failure_modes(ctx)
            self._populate(r)
            n  = r.get("failure_count", 0)
            ft = r.get("is_fatal", False)
            color = _RED if ft else (_ORG if n > 0 else _GRN)
            self._set_status(
                f"Done: {n} failure(s)  "
                f"cascade={r.get('cascade_risk',0):.3f}  "
                f"fatal={'YES' if ft else 'no'}  "
                f"score={r.get('system_score',0):.1f}", color)
        except Exception as e:
            self._set_status(f"Error: {e}", _RED)

    def _get_report(self):
        if not self._engine: return
        try:
            r = self._engine.get_failure_report()
            self._populate_cascade(r)
            self._set_status("Report refreshed", _GRN)
        except Exception as e:
            self._set_status(f"Error: {e}", _RED)

    def _detect_cascade(self):
        if not self._engine: return
        try:
            r = self._engine.detect_cascade()
            lines = [
                f"Cascade Active: {r.get('cascade_active', False)}",
                f"Cascade Risk:   {r.get('cascade_risk', 0):.4f}",
                f"Cascade Depth:  {r.get('cascade_depth', 0)}",
                f"Fatal:          {r.get('fatal', False)}",
                "",
                "Fatal Combos:",
            ]
            for combo in r.get("fatal_combos", []):
                lines.append(f"  !! {combo}")
            if not r.get("fatal_combos"):
                lines.append("  (none)")
            self._cascade_txt.setPlainText("\n".join(lines))
            self._set_status(
                f"Cascade risk={r.get('cascade_risk',0):.4f}  "
                f"depth={r.get('cascade_depth',0)}  "
                f"fatal={r.get('fatal',False)}", _MAV)
        except Exception as e:
            self._set_status(f"Error: {e}", _RED)

    def _clear_failures(self):
        if self._engine:
            try: self._engine.clear_failures()
            except Exception: pass
        self._table.setRowCount(0)
        self._fatal_list.clear()
        self._cascade_txt.setPlainText(
            "Cleared. Run analysis to detect new failures.")
        self._event_log.clear()
        self._update_status_card({})
        self._set_status("Cleared", _MUT)

    def _set_status(self, msg, color=_MUT):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(
            f"color:{color};font-size:9px;font-style:italic;"
            f"border:none;background:transparent;")

    # ── populate helpers ──────────────────────────────────────────────
    def _populate(self, r: dict):
        self._table.setRowCount(0)
        for fm in r.get("active_modes", []):
            self._append_failure(fm)
        self._update_status_card(r)
        self._populate_cascade(r)
        self._log_event(r)

    def _append_failure(self, fm: dict):
        row = self._table.rowCount()
        self._table.insertRow(row)
        sev   = fm.get("severity", 1)
        sc    = _SEV_COLORS.get(sev, _FG)
        snm   = _SEV_NAMES.get(sev, "LOW")
        cr    = fm.get("cascade_risk", 0.0)
        vals = [
            (fm.get("failure_id","")[:12],          _MUT),
            (fm.get("mode_type",""),                 sc),
            (snm,                                    sc),
            (fm.get("trigger",""),                   _YLW),
            (f"{fm.get('trigger_value',0):.4f}",     _FG),
            (f"{fm.get('severity_score',0):.1f}",    sc),
            (f"{cr:.3f}", _RED if cr > 0.5 else (_ORG if cr > 0.2 else _FG)),
            (fm.get("impact","")[:40],               _MUT),
        ]
        for c, (val, color) in enumerate(vals):
            item = QtWidgets.QTableWidgetItem(val)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QtGui.QColor(color))
            self._table.setItem(row, c, item)

    def _update_status_card(self, r: dict):
        fs    = r.get("failure_state", {})
        n     = r.get("failure_count",  fs.get("active_count",  0))
        ms    = r.get("max_severity",   fs.get("max_severity",  1))
        cr    = r.get("cascade_risk",   fs.get("cascade_risk",  0.0))
        dep   = r.get("cascade_depth",  fs.get("cascade_depth", 0))
        sc    = r.get("system_score",   fs.get("system_score",  0.0))
        fatal = r.get("is_fatal",       fs.get("is_fatal",      False))

        combos = r.get("fatal_combos", [])
        if fatal:
            self._fatal_banner.setText("!! FATAL COMBINATION !!")
            self._fatal_banner.setStyleSheet(
                f"color:{_RED};font-size:12px;font-weight:bold;"
                f"border:none;background:transparent;")
        elif n > 0:
            self._fatal_banner.setText(f"⚠  {n} FAILURE(S) ACTIVE")
            self._fatal_banner.setStyleSheet(
                f"color:{_ORG};font-size:12px;font-weight:bold;"
                f"border:none;background:transparent;")
        else:
            self._fatal_banner.setText("⬡  SYSTEM OK")
            self._fatal_banner.setStyleSheet(
                f"color:{_GRN};font-size:12px;font-weight:bold;"
                f"border:none;background:transparent;")

        ms_c  = _SEV_COLORS.get(ms if isinstance(ms,int) else 1, _GRN)
        cr_c  = _RED if cr > 0.5 else (_ORG if cr > 0.2 else _GRN)
        sc_c  = _RED if sc > 70 else (_ORG if sc > 40 else _GRN)
        ms_nm = _SEV_NAMES.get(ms if isinstance(ms,int) else 1, "LOW")

        for key, val, color in [
            ("active",  str(n),             _RED if n > 0 else _GRN),
            ("max_sev", ms_nm,              ms_c),
            ("cascade", f"{cr:.3f}",        cr_c),
            ("depth",   str(dep),           _MAV if dep > 0 else _MUT),
            ("score",   f"{sc:.1f}",        sc_c),
        ]:
            lv = self._fkpis.get(key)
            if lv:
                lv.setText(val)
                lv.setStyleSheet(
                    f"color:{color};font-size:13px;font-weight:bold;"
                    f"border:none;background:transparent;")

        self._fatal_list.clear()
        for combo in combos:
            it = QtWidgets.QListWidgetItem(f"!! {combo}")
            it.setForeground(QtGui.QColor(_RED))
            self._fatal_list.addItem(it)

    def _populate_cascade(self, r: dict):
        lines = [
            f"Cascade Active: {r.get('cascade_active', False)}",
            f"Cascade Risk:   {r.get('cascade_risk', 0.0):.4f}",
            f"Cascade Depth:  {r.get('cascade_depth', 0)}",
            f"Is Fatal:       {r.get('is_fatal', False)}",
            f"System Score:   {r.get('system_score', 0.0):.1f}",
            f"Active Types:   {r.get('active_types', [])}",
            "",
            "Fatal Combinations:",
        ]
        for combo in r.get("fatal_combos", []):
            lines.append(f"  !! {combo}")
        if not r.get("fatal_combos"):
            lines.append("  (none)")
        lines.append("")
        lines.append("Summary:")
        lines.append(r.get("summary", "--"))
        self._cascade_txt.setPlainText("\n".join(lines))

    def _log_event(self, r: dict):
        from datetime import datetime
        ts  = str(datetime.now())[11:19]
        n   = r.get("failure_count", 0)
        ft  = r.get("is_fatal", False)
        cr  = r.get("cascade_risk", 0.0)
        sc  = r.get("system_score", 0.0)
        tag = "FATAL" if ft else ("WARN" if n > 0 else "OK")
        color = _RED if ft else (_ORG if n > 0 else _GRN)
        line  = (f"[{ts}] [{tag}]  "
                 f"n={n}  cascade={cr:.3f}  score={sc:.1f}")
        self._event_log.appendHtml(
            f'<span style="color:{color};">{line}</span>')
        sb = self._event_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ── event handlers ────────────────────────────────────────────────
    def _on_failure(self, event):
        d = event.data or {}
        if d.get("status") == "ok":
            self._populate(d)

    def _on_report(self, event):
        d = event.data or {}
        if d.get("status") == "ok":
            self._populate_cascade(d)

    def closeEvent(self, event):
        if self._event_engine:
            for ev, fn in self._subscriptions:
                try: self._event_engine.unregister(ev, fn)
                except Exception: pass
        super().closeEvent(event)
