"""
market_reality_ai/ui/widget.py

Market Reality Simulation System — 主窗口骨架。
Phase 1: 完整 UI 骨架，所有 Tab 为空占位符，Logs Tab 即时可用。
"""
from __future__ import annotations
from datetime import datetime

from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine

from ..constant import APP_NAME
from ..event import (
    EVENT_REALITY_STARTED, EVENT_REALITY_STOPPED,
    EVENT_REALITY_LOG, EVENT_REALITY_WARNING, EVENT_REALITY_CRITICAL,
    EVENT_EXECUTION_SIMULATED,
    EVENT_STRESS_TEST_STARTED, EVENT_STRESS_TEST_COMPLETED,
    EVENT_WALKFORWARD_UPDATED, EVENT_WALKFORWARD_COMPLETED,
    EVENT_FAILURE_MODE_DETECTED, EVENT_FAILURE_REPORT_READY,
    EVENT_SURVIVAL_SCORE_UPDATED,
)
from .dashboard_tab   import DashboardTab
from .stress_tab      import StressTab
from .walkforward_tab import WalkForwardTab
from .failure_tab     import FailureTab

_BG  = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"
_FG  = "#cdd6f4"; _MUT  = "#6c7086"; _HEAD   = "#313244"
_GRN = "#a6e3a1"; _YLW  = "#f9e2af"; _RED    = "#f38ba8"
_ORG = "#fab387"; _MAV  = "#cba6f7"; _CYN    = "#89dceb"
_TEA = "#94e2d5"; _BLUE = "#89b4fa"


def _lbl(t, s=""):
    w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w


def _btn(t, color, slot, h=32, fs=11):
    b = QtWidgets.QPushButton(t); b.setFixedHeight(h)
    b.setStyleSheet(
        f"QPushButton{{background:{color};color:#1e1e2e;font-weight:bold;"
        f"border:none;border-radius:4px;padding:0 14px;font-size:{fs}px;}}"
        f"QPushButton:hover{{opacity:0.85;}}"
        f"QPushButton:disabled{{background:#45475a;color:#6c7086;}}")
    b.clicked.connect(slot); return b


def _placeholder(title, subtitle="", phase=2):
    w = QtWidgets.QWidget(); w.setStyleSheet(f"background:{_DARK};")
    vb = QtWidgets.QVBoxLayout(w)
    vb.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    for txt, sty in [
        ("⬡",   f"color:{_BORDER};font-size:56px;border:none;"),
        (title,  f"color:{_FG};font-size:16px;font-weight:bold;border:none;"),
        (subtitle or f"Implemented in Phase {phase}",
                 f"color:{_MUT};font-size:11px;border:none;"),
        (f"[ Phase {phase} ]",
                 f"color:{_YLW};font-size:10px;border:none;"),
    ]:
        lbl = _lbl(txt, sty + "background:transparent;")
        lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        vb.addWidget(lbl)
    return w


class _LogTab(QtWidgets.QWidget):
    """Simulation Log Stream — active from Phase 1."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(self)
        vb.setContentsMargins(10, 8, 10, 8); vb.setSpacing(6)
        hdr = QtWidgets.QHBoxLayout()
        hdr.addWidget(_lbl("Simulation Log Stream",
                           f"color:{_YLW};font-size:11px;"
                           f"font-weight:bold;border:none;"))
        hdr.addStretch()
        hdr.addWidget(_btn("Clear", _MUT,
                           lambda: self._txt.clear(), h=24, fs=9))
        vb.addLayout(hdr)
        self._txt = QtWidgets.QPlainTextEdit()
        self._txt.setReadOnly(True); self._txt.setMaximumBlockCount(2000)
        self._txt.setFont(QtGui.QFont("Consolas", 9))
        self._txt.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        vb.addWidget(self._txt)

    def append(self, line: str, level: str = "INFO") -> None:
        c = {"INFO": _MUT, "WARNING": _YLW,
             "CRITICAL": _RED, "ERROR": _RED}.get(level, _MUT)
        self._txt.appendHtml(f'<span style="color:{c};">{line}</span>')
        sb = self._txt.verticalScrollBar(); sb.setValue(sb.maximum())


class RealitySimulationWidget(QtWidgets.QMainWindow):
    """
    Market Reality Simulation System — 主控台主窗口。

    Phase 1 骨架:
      顶部: 状态条 (status / phase / survival score / grade / session)
      左侧: 仿真状态面板 (module list + survival score stub)
      右侧: 6-Tab (Dashboard / Execution / Stress /
                    Walk-Forward / Failure Mode / Logs)
      Tab 1-5: _placeholder()   ← Phase 2–5 填充
      Tab 6:   _LogTab()        ← Phase 1 即时可用
    """

    widget_name = APP_NAME

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = main_engine.get_engine(APP_NAME)
        self._init_ui()
        self._init_menu()
        self._register_events()

    def _init_ui(self) -> None:
        self.setWindowTitle(
            "Market Reality AI  市场现实仿真系统  [ Phase 5 ]")
        self.resize(1440, 880)
        self.setStyleSheet(f"background:{_BG};color:{_FG};")
        central = QtWidgets.QWidget(); self.setCentralWidget(central)
        outer = QtWidgets.QVBoxLayout(central)
        outer.setContentsMargins(8, 8, 8, 8); outer.setSpacing(8)
        outer.addWidget(self._build_status_bar())
        body = QtWidgets.QHBoxLayout(); body.setSpacing(8)
        body.addWidget(self._build_left_panel(), stretch=0)
        body.addWidget(self._build_tabs(),        stretch=1)
        outer.addLayout(body)

    # ── status bar ────────────────────────────────────────────────────
    def _build_status_bar(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget(); w.setFixedHeight(68)
        w.setStyleSheet(
            f"background:{_DARK};border-radius:6px;"
            f"border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(20, 8, 20, 8); h.setSpacing(22)
        h.addWidget(_lbl("Market Reality AI",
                         f"color:{_RED};font-size:14px;font-weight:bold;"
                         f"border:none;background:transparent;"))
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        sep.setStyleSheet(f"color:{_BORDER};background:transparent;")
        h.addWidget(sep)
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for key, txt, color in [
            ("status",  "Engine Status",  _CYN),
            ("phase",   "Active Phase",   _YLW),
            ("score",   "Survival Score", _GRN),
            ("grade",   "Grade",          _MAV),
        ]:
            cell = QtWidgets.QWidget()
            cell.setStyleSheet("background:transparent;border:none;")
            cv = QtWidgets.QVBoxLayout(cell)
            cv.setContentsMargins(0, 0, 0, 0); cv.setSpacing(2)
            lk = _lbl(txt,
                       f"color:{_MUT};font-size:9px;"
                       f"border:none;background:transparent;")
            lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = _lbl("--",
                       f"color:{color};font-size:14px;font-weight:bold;"
                       f"border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv)
            self._kpi[key] = lv; h.addWidget(cell)
        h.addStretch()
        bc = QtWidgets.QVBoxLayout(); bc.setSpacing(6)
        bc.addWidget(_btn("▶  Start Engine", _GRN,
                          self._on_engine_start, h=26, fs=10))
        bc.addWidget(_btn("■  Stop Engine",  _RED,
                          self._on_engine_stop,  h=26, fs=10))
        h.addLayout(bc)
        self._ts_lbl = _lbl("--",
                             f"color:{_MUT};font-size:8px;"
                             f"border:none;background:transparent;")
        self._ts_lbl.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight |
            QtCore.Qt.AlignmentFlag.AlignBottom)
        h.addWidget(self._ts_lbl)
        return w

    def _update_kpi_status(self, status: str) -> None:
        sc = {"idle": _MUT, "running": _GRN, "completed": _BLUE,
              "failed": _RED, "aborted": _ORG, "paused": _YLW}.get(status, _FG)
        self._kpi["status"].setText(status.upper())
        self._kpi["status"].setStyleSheet(
            f"color:{sc};font-size:14px;font-weight:bold;"
            f"border:none;background:transparent;")

    # ── left panel ────────────────────────────────────────────────────
    def _build_left_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget(); panel.setFixedWidth(215)
        panel.setStyleSheet(
            f"background:{_DARK};border-radius:6px;"
            f"border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(12, 14, 12, 14); vb.setSpacing(10)
        vb.addWidget(_lbl("Simulation State",
                          f"color:{_CYN};font-size:11px;font-weight:bold;"
                          f"border:none;background:transparent;"))
        # current phase card
        ph_w = QtWidgets.QWidget()
        ph_w.setStyleSheet(f"background:{_HEAD};border-radius:4px;border:none;")
        ph_vb = QtWidgets.QVBoxLayout(ph_w)
        ph_vb.setContentsMargins(8, 8, 8, 8); ph_vb.setSpacing(3)
        ph_vb.addWidget(_lbl("Current Phase",
                             f"color:{_MUT};font-size:9px;border:none;background:transparent;"))
        self._phase_lbl = _lbl("Phase 1  —  Architecture",
                                f"color:{_YLW};font-size:10px;font-weight:bold;"
                                f"border:none;background:transparent;")
        ph_vb.addWidget(self._phase_lbl)
        vb.addWidget(ph_w)
        vb.addWidget(_lbl("Simulation Modules",
                          f"color:{_MUT};font-size:9px;font-weight:bold;"
                          f"border:none;background:transparent;"))
        self._mod_dots: dict[str, QtWidgets.QLabel] = {}
        for mod, phase in [
            ("Execution Reality", 2),
            ("Market Impact",     3),
            ("Stress Testing",    4),
            ("Walk-Forward",      4),
            ("Failure Mode",      5),
        ]:
            row = QtWidgets.QWidget()
            row.setStyleSheet("background:transparent;border:none;")
            rh = QtWidgets.QHBoxLayout(row)
            rh.setContentsMargins(0, 0, 0, 0); rh.setSpacing(6)
            dot = _lbl("●", f"color:{_MUT};font-size:10px;border:none;background:transparent;")
            nm  = _lbl(mod,  f"color:{_MUT};font-size:9px;border:none;background:transparent;")
            tag = _lbl(f"P{phase}", f"color:{_BORDER};font-size:8px;border:none;background:transparent;")
            rh.addWidget(dot); rh.addWidget(nm); rh.addStretch(); rh.addWidget(tag)
            vb.addWidget(row)
            self._mod_dots[mod] = dot
        vb.addStretch()
        # survival score stub
        sc_w = QtWidgets.QWidget()
        sc_w.setStyleSheet(f"background:{_HEAD};border-radius:4px;border:none;")
        sc_vb = QtWidgets.QVBoxLayout(sc_w)
        sc_vb.setContentsMargins(8, 8, 8, 8); sc_vb.setSpacing(3)
        sc_vb.addWidget(_lbl("System Survival Score",
                             f"color:{_MUT};font-size:9px;border:none;background:transparent;"))
        self._score_lbl = _lbl("—  (Phase 4)",
                                f"color:{_MUT};font-size:13px;font-weight:bold;"
                                f"border:none;background:transparent;")
        sc_vb.addWidget(self._score_lbl)
        vb.addWidget(sc_w)
        vb.addSpacing(4)
        vb.addWidget(_lbl("[ Phase 1: no simulation active ]",
                          f"color:{_BORDER};font-size:8px;border:none;background:transparent;"))
        return panel

    # ── tabs ───────────────────────────────────────────────────────────
    def _build_tabs(self) -> QtWidgets.QTabWidget:
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane{{background:{_DARK};"
            f"border:1px solid {_BORDER};border-radius:4px;}}"
            f"QTabBar::tab{{background:{_HEAD};color:{_MUT};"
            f"border:1px solid {_BORDER};border-bottom:none;"
            f"padding:6px 14px;font-size:10px;}}"
            f"QTabBar::tab:selected{{background:{_DARK};"
            f"color:{_FG};border-top:2px solid {_RED};}}"
            f"QTabBar::tab:hover{{background:{_BORDER};}}")
        self._dashboard_tab = DashboardTab(
            self._main_engine, self._event_engine)
        tabs.addTab(self._dashboard_tab, "Dashboard")
        tabs.addTab(
            _placeholder("Execution Reality Simulator",
                         "Slippage · Fill · Latency · Rejection", 2),
            "Execution Reality")
        self._stress_tab = StressTab(
            self._main_engine, self._event_engine)
        tabs.addTab(self._stress_tab, "Stress Test")
        self._wf_tab = WalkForwardTab(
            self._main_engine, self._event_engine)
        tabs.addTab(self._wf_tab, "Walk-Forward")
        self._failure_tab = FailureTab(
            self._main_engine, self._event_engine)
        tabs.addTab(self._failure_tab, "Failure Mode")
        self._log_tab = _LogTab()
        tabs.addTab(self._log_tab, "Logs")
        self._tabs = tabs
        return tabs
    def _init_menu(self) -> None:
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar{{background:{_DARK};color:{_FG};border:none;}}"
            f"QMenuBar::item:selected{{background:{_HEAD};}}"
            f"QMenu{{background:{_DARK};color:{_FG};"
            f"border:1px solid {_BORDER};}}"
            f"QMenu::item:selected{{background:{_HEAD};}}")
        m = mb.addMenu("Simulation")
        m.addAction("Start Engine").triggered.connect(self._on_engine_start)
        m.addAction("Stop Engine").triggered.connect(self._on_engine_stop)
        m.addSeparator()
        m.addAction("Run Stress Test  [Phase 4]").triggered.connect(
            self._on_run_stress)
        m.addAction("Run All Stress Scenarios").triggered.connect(
            self._on_run_all_stress)
        m.addAction("Walk-Forward Analysis  [Phase 4]").triggered.connect(
            self._on_run_wf)
        m.addAction("Failure Analysis  [Phase 5]").triggered.connect(
            self._on_analyze_failures)
        m.addAction("Get Survival Score").triggered.connect(
            self._on_get_score)
        m.addAction("Simulate Execution  [Phase 2]").setEnabled(False)
        m.addSeparator()
        m.addAction("Close").triggered.connect(self.close)
        mh = mb.addMenu("About")
        mh.addAction("Market Reality AI  v1.0 Phase 5").setEnabled(False)
        mh.addAction(
            "Not to simulate profit — to simulate death").setEnabled(False)

    # ── VeighNa events ─────────────────────────────────────────────────
    def _register_events(self) -> None:
        self._subscribed_events = [
            EVENT_REALITY_STARTED, EVENT_REALITY_STOPPED,
            EVENT_REALITY_LOG, EVENT_REALITY_WARNING, EVENT_REALITY_CRITICAL,
            EVENT_EXECUTION_SIMULATED,
            EVENT_STRESS_TEST_STARTED, EVENT_STRESS_TEST_COMPLETED,
            EVENT_WALKFORWARD_UPDATED, EVENT_WALKFORWARD_COMPLETED,
            EVENT_FAILURE_MODE_DETECTED, EVENT_FAILURE_REPORT_READY,
            EVENT_SURVIVAL_SCORE_UPDATED,
        ]
        for ev in self._subscribed_events:
            self._event_engine.register(ev, self._on_event)

    def _on_event(self, event) -> None:
        et = event.type; d = event.data or {}
        if et == EVENT_REALITY_STARTED:
            self._update_kpi_status("running")
            self._log_tab.append(
                f"[{str(datetime.now())[11:19]}]  Engine started", "INFO")
        elif et == EVENT_REALITY_STOPPED:
            self._update_kpi_status("idle")
            self._log_tab.append(
                f"[{str(datetime.now())[11:19]}]  Engine stopped", "INFO")
        elif et in (EVENT_REALITY_LOG,):
            self._log_tab.append(d.get("line",""), d.get("level","INFO"))
        elif et == EVENT_REALITY_WARNING:
            self._log_tab.append(d.get("line",""), "WARNING")
        elif et == EVENT_REALITY_CRITICAL:
            self._log_tab.append(d.get("line",""), "CRITICAL")
        elif et == EVENT_SURVIVAL_SCORE_UPDATED:
            score = d.get("score"); grade = d.get("grade","F")
            sc_txt = f"{score:.1f}" if score is not None else "--"
            gc = {"S":_GRN,"A":_TEA,"B":_YLW,"C":_ORG,"F":_RED}.get(grade, _MUT)
            self._kpi["score"].setText(sc_txt)
            self._kpi["grade"].setText(grade)
            self._kpi["grade"].setStyleSheet(
                f"color:{gc};font-size:14px;font-weight:bold;"
                f"border:none;background:transparent;")
            self._score_lbl.setText(f"{sc_txt}  [{grade}]")
            self._score_lbl.setStyleSheet(
                f"color:{gc};font-size:13px;font-weight:bold;"
                f"border:none;background:transparent;")
        self._ts_lbl.setText(f"Updated: {str(datetime.now())[11:19]}")

    # ── slots ──────────────────────────────────────────────────────────
    def _on_engine_start(self) -> None:
        if self._engine is None: return
        self._engine.init(); self._engine.start()
        self._update_kpi_status("running")
        self._kpi["phase"].setText("Phase 5")
        self._log_tab.append(
            f"[{str(datetime.now())[11:19]}]  "
            f"[SYSTEM]  Engine started — Phase 1 active", "INFO")

    def _on_engine_stop(self) -> None:
        if self._engine: self._engine.stop()
        self._update_kpi_status("idle")
        self._log_tab.append(
            f"[{str(datetime.now())[11:19]}]  "
            f"[SYSTEM]  Engine stopped", "INFO")

    # ── Phase 4/5 menu slots ─────────────────────────────────────────
    def _on_run_stress(self) -> None:
        if self._engine is None: return
        try:
            r = self._engine.run_stress_test("flash_crash", seed=42)
            self._log_tab.append(
                f"[{str(__import__('datetime').datetime.now())[11:19]}]  "
                f"[STRESS]  flash_crash  grade={r.get('survival_grade','?')}  "
                f"score={r.get('survival_score',0):.1f}", "INFO")
        except Exception as e:
            self._log_tab.append(f"[STRESS] Error: {e}", "ERROR")

    def _on_run_all_stress(self) -> None:
        if self._engine is None: return
        try:
            r    = self._engine.run_all_stress_scenarios()
            sc_d = r.get("survival_score", {})
            self._log_tab.append(
                f"[{str(__import__('datetime').datetime.now())[11:19]}]  "
                f"[STRESS]  All 6 scenarios  "
                f"score={sc_d.get('score',0):.1f}  "
                f"grade={sc_d.get('grade','F')}", "INFO")
        except Exception as e:
            self._log_tab.append(f"[STRESS] Error: {e}", "ERROR")

    def _on_run_wf(self) -> None:
        if self._engine is None: return
        try:
            r = self._engine.run_walk_forward(n_windows=12, seed=42)
            self._log_tab.append(
                f"[{str(__import__('datetime').datetime.now())[11:19]}]  "
                f"[WF]  {r.get('total_windows',0)} windows  "
                f"avg_gap={r.get('avg_reality_gap',0):.1f}bps  "
                f"score={r.get('reality_gap_score',0):.1f}", "INFO")
        except Exception as e:
            self._log_tab.append(f"[WF] Error: {e}", "ERROR")

    def _on_analyze_failures(self) -> None:
        if self._engine is None: return
        try:
            r = self._engine.analyze_failure_modes({})
            self._log_tab.append(
                f"[{str(__import__('datetime').datetime.now())[11:19]}]  "
                f"[FAILURE]  count={r.get('failure_count',0)}  "
                f"cascade={r.get('cascade_risk',0):.3f}  "
                f"fatal={r.get('is_fatal',False)}", "INFO")
        except Exception as e:
            self._log_tab.append(f"[FAILURE] Error: {e}", "ERROR")

    def _on_get_score(self) -> None:
        if self._engine is None: return
        try:
            sc = self._engine.get_survival_score()
            self._log_tab.append(
                f"[{str(__import__('datetime').datetime.now())[11:19]}]  "
                f"[SCORE]  score={sc.get('score',0):.1f}  "
                f"grade={sc.get('grade','F')}", "INFO")
        except Exception as e:
            self._log_tab.append(f"[SCORE] Error: {e}", "ERROR")

    def closeEvent(self, event) -> None:
        for ev in getattr(self, "_subscribed_events", []):
            try: self._event_engine.unregister(ev, self._on_event)
            except Exception: pass
        super().closeEvent(event)
