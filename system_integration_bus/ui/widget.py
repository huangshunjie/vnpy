"""
system_integration_bus/ui/widget.py

SystemBusWidget — 系统集成总线监控主窗口。
布局：左侧控制面板 + 右侧 4-Tab（总览/管道/健康/消息流）
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine
from ..constant import APP_NAME
from ..event import EVENT_BUS_MESSAGE, EVENT_PIPELINE_CYCLE

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _BLUE = "#89b4fa"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"
_RED = "#f38ba8"; _MAV = "#cba6f7"; _HEAD = "#313244"; _CYN = "#89dceb"
_TEA = "#94e2d5"; _ORG = "#fab387"
_STATUS_COLOR = {
    "idle": _MUT, "running": _GRN, "paused": _YLW,
    "degraded": _ORG, "stopped": _RED,
}
_HEALTH_COLOR = {
    "healthy": _GRN, "degraded": _YLW, "offline": _RED, "unknown": _MUT,
}
_TBL = (
    "QTableWidget{background:#181825;color:#cdd6f4;border:1px solid #45475a;"
    "gridline-color:#45475a;font-size:11px;}"
    "QTableWidget::item{padding:3px 6px;}"
    "QTableWidget::item:alternate{background:#1e1e2e;}"
    "QTableWidget::item:selected{background:#45475a;}"
    "QHeaderView::section{background:#313244;color:#6c7086;border:none;"
    "border-bottom:1px solid #45475a;padding:4px 6px;font-size:10px;}"
)
_FLOW_TEXT = (
    "  External World\n"
    "       |\n"
    "  +----+-------------------------------------------+\n"
    "  | Stage 1  INGEST    DataIntelligence AI         |\n"
    "  +----+-------------------------------------------+\n"
    "       |  eDI_DataFused\n"
    "  +----+-------------------------------------------+\n"
    "  | Stage 2  SIGNAL    Alpha + Regime              |\n"
    "  +----+-------------------------------------------+\n"
    "       |  eAlphaFactory.live / eMarketRegimeChanged\n"
    "  +----+-------------------------------------------+\n"
    "  | Stage 3  ALLOCATE  Portfolio + Capital + Risk  |\n"
    "  +----+-------------------------------------------+\n"
    "       |  ePortfolio.rebalance / eRiskAlert\n"
    "  +----+-------------------------------------------+\n"
    "  | Stage 4  EXECUTE   Execution + EI              |\n"
    "  +----+-------------------------------------------+\n"
    "       |  eFillUpdate / eExecutionCompleted\n"
    "  +----+-------------------------------------------+\n"
    "  | Stage 5  LEARN     AdaptiveLearning            |\n"
    "  +----+-------------------------------------------+\n"
    "       |  eAL_SystemAdapted --> AlphaFactory (feedback)"
)


def _lbl(t, s=""):
    w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w


def _sep():
    s = QtWidgets.QFrame()
    s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    s.setStyleSheet("border:none;border-top:1px solid #45475a;background:transparent;")
    return s


class SystemBusWidget(QtWidgets.QMainWindow):
    """System Integration Bus 监控主窗口。"""

    widget_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = main_engine.get_engine(APP_NAME)
        self._init_ui()
        self._init_menu()
        self._register_events()
        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self._on_refresh)
        self._refresh_timer.start(3000)

    # ── UI construction ───────────────────────────────────────────────
    def _init_ui(self):
        self.setWindowTitle("System Integration Bus  系统集成总线")
        self.resize(1440, 860)
        self.setStyleSheet(f"background:{_BG}; color:{_FG};")
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        h = QtWidgets.QHBoxLayout(central)
        h.setContentsMargins(8, 8, 8, 8); h.setSpacing(8)
        h.addWidget(self._build_left(), stretch=0)
        h.addWidget(self._build_tabs(), stretch=1)

    def _build_left(self):
        panel = QtWidgets.QWidget(); panel.setFixedWidth(220)
        panel.setStyleSheet(
            f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(12, 14, 12, 14); vb.setSpacing(10)
        vb.addWidget(_lbl("System Bus",
                          f"color:{_CYN};font-weight:bold;font-size:13px;border:none;"))
        vb.addWidget(_sep())
        self._status_labels: dict[str, QtWidgets.QLabel] = {}
        for key, label in [
            ("status","Bus Status"),("uptime","Uptime"),("messages","Messages"),
            ("forwarded","Forwarded"),("dropped","Dropped"),("cycles","Cycles"),
            ("avg_cycle","Avg ms"),("healthy","Healthy"),
            ("offline","Offline"),("risk_gate","Risk Gate"),
        ]:
            row_w = QtWidgets.QWidget()
            row_w.setStyleSheet("background:transparent;border:none;")
            rh = QtWidgets.QHBoxLayout(row_w); rh.setContentsMargins(0,0,0,0)
            lk = QtWidgets.QLabel(label)
            lk.setStyleSheet(
                f"color:{_MUT};font-size:10px;border:none;background:transparent;")
            lk.setFixedWidth(80)
            lv = QtWidgets.QLabel("--")
            lv.setStyleSheet(
                f"color:{_FG};font-size:11px;font-weight:bold;"
                f"border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            rh.addWidget(lk); rh.addStretch(); rh.addWidget(lv)
            self._status_labels[key] = lv; vb.addWidget(row_w)
        vb.addStretch()
        for label, color, slot in [
            ("Start Bus", _GRN, self._on_start),
            ("Stop Bus",  _RED, self._on_stop),
            ("New Cycle", _YLW, self._on_force_cycle),
            ("Refresh",   _MUT, self._on_refresh),
        ]:
            muted = color == _MUT
            btn = QtWidgets.QPushButton(label)
            btn.setStyleSheet(
                f"QPushButton{{background:{'transparent' if muted else color};"
                f"color:{'#6c7086' if muted else '#1e1e2e'};"
                f"font-weight:bold;"
                f"border:{'1px solid #45475a' if muted else 'none'};"
                f"border-radius:4px;padding:7px;font-size:11px;}}"
                f"QPushButton:hover{{background:{_HEAD if muted else color};"
                f"color:{_FG if muted else '#1e1e2e'};}}")
            btn.clicked.connect(slot); vb.addWidget(btn)
        return panel

    def _build_tabs(self):
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane{{background:{_DARK};border:1px solid {_BORDER};"
            f"border-radius:4px;}}"
            f"QTabBar::tab{{background:{_HEAD};color:{_MUT};padding:8px 14px;"
            f"font-size:11px;border:none;border-bottom:2px solid transparent;"
            f"margin-right:2px;}}"
            f"QTabBar::tab:selected{{color:{_FG};border-bottom:2px solid {_CYN};}}"
            f"QTabBar::tab:hover{{color:{_FG};background:{_BORDER};}}")
        tabs.addTab(self._build_overview_tab(), "Overview")
        tabs.addTab(self._build_pipeline_tab(), "Pipeline")
        tabs.addTab(self._build_health_tab(),   "Health")
        tabs.addTab(self._build_stream_tab(),   "Stream")
        self._tabs = tabs
        return tabs

    def _build_overview_tab(self):
        w = QtWidgets.QWidget(); w.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(16, 16, 16, 16); vb.setSpacing(10)
        vb.addWidget(_lbl("Pipeline Architecture",
                          f"color:{_CYN};font-size:12px;font-weight:bold;border:none;"))
        flow = QtWidgets.QLabel(_FLOW_TEXT)
        flow.setFont(QtGui.QFont("Consolas", 10))
        flow.setStyleSheet(
            f"color:{_TEA};border:1px solid {_BORDER};"
            f"border-radius:4px;padding:14px;background:{_BG};")
        vb.addWidget(flow); vb.addStretch()
        return w

    def _build_pipeline_tab(self):
        w = QtWidgets.QWidget(); w.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(10, 10, 10, 10); vb.setSpacing(8)
        vb.addWidget(_lbl("Pipeline Cycle History",
                          f"color:{_YLW};font-size:11px;font-weight:bold;border:none;"))
        cols = ["Cycle","Started","Duration ms","Stages Done",
                "Stages Skipped","Messages","OK"]
        self._pipeline_tbl = QtWidgets.QTableWidget(0, len(cols))
        self._pipeline_tbl.setHorizontalHeaderLabels(cols)
        self._pipeline_tbl.verticalHeader().setVisible(False)
        self._pipeline_tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._pipeline_tbl.setAlternatingRowColors(True)
        self._pipeline_tbl.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._pipeline_tbl.horizontalHeader().setStretchLastSection(True)
        self._pipeline_tbl.setStyleSheet(_TBL)
        vb.addWidget(self._pipeline_tbl)
        return w

    def _build_health_tab(self):
        w = QtWidgets.QWidget(); w.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(10, 10, 10, 10); vb.setSpacing(8)
        vb.addWidget(_lbl("Engine Health Monitor",
                          f"color:{_GRN};font-size:11px;font-weight:bold;border:none;"))
        cols = ["Engine","Status","Messages","Errors","Latency ms","Last Seen"]
        self._health_tbl = QtWidgets.QTableWidget(0, len(cols))
        self._health_tbl.setHorizontalHeaderLabels(cols)
        self._health_tbl.verticalHeader().setVisible(False)
        self._health_tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._health_tbl.setAlternatingRowColors(True)
        self._health_tbl.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._health_tbl.horizontalHeader().setStretchLastSection(True)
        self._health_tbl.setStyleSheet(_TBL)
        vb.addWidget(self._health_tbl)
        return w

    def _build_stream_tab(self):
        w = QtWidgets.QWidget(); w.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(10, 10, 10, 10); vb.setSpacing(8)
        vb.addWidget(_lbl("Live Message Stream",
                          f"color:{_MAV};font-size:11px;font-weight:bold;border:none;"))
        self._stream = QtWidgets.QPlainTextEdit()
        self._stream.setReadOnly(True)
        self._stream.setFont(QtGui.QFont("Consolas", 10))
        self._stream.setStyleSheet(
            f"QPlainTextEdit{{background:{_BG};color:{_MAV};"
            f"border:1px solid {_BORDER};border-radius:3px;}}")
        self._stream.setPlainText("  Waiting for bus messages...")
        vb.addWidget(self._stream)
        return w

    def _init_menu(self):
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar{{background:{_DARK};color:{_FG};border:none;}}"
            f"QMenuBar::item:selected{{background:{_HEAD};}}"
            f"QMenu{{background:{_DARK};color:{_FG};border:1px solid {_BORDER};}}"
            f"QMenu::item:selected{{background:{_HEAD};}}")
        m = mb.addMenu("Bus")
        m.addAction("Start").triggered.connect(self._on_start)
        m.addAction("Stop").triggered.connect(self._on_stop)
        m.addSeparator()
        m.addAction("Force New Cycle").triggered.connect(self._on_force_cycle)
        m.addAction("Health Check").triggered.connect(self._on_health_check)
        m.addSeparator()
        m.addAction("Close").triggered.connect(self.close)

    def _register_events(self):
        self._event_engine.register(EVENT_BUS_MESSAGE,    self._on_bus_msg_event)
        self._event_engine.register(EVENT_PIPELINE_CYCLE, self._on_cycle_event)

    def _on_bus_msg_event(self, event):
        d = event.data or {}
        line = (f"  [{d.get('stage','?'):<10}]"
                f" ch={d.get('channel','?'):<18}"
                f" src={d.get('source','?'):<26}"
                f" ev={d.get('event_type','?')}")
        self._stream.appendPlainText(line)
        sb = self._stream.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_cycle_event(self, event):
        self._append_pipeline_row(event.data or {})

    def _on_start(self):
        if self._engine:
            self._engine.init(); self._engine.start(); self._on_refresh()

    def _on_stop(self):
        if self._engine:
            self._engine.stop(); self._on_refresh()

    def _on_force_cycle(self):
        if self._engine: self._engine.force_cycle()

    def _on_health_check(self):
        if self._engine:
            self._engine.check_health(); self._refresh_health()

    def _on_refresh(self):
        if self._engine is None: return
        try:
            summ = self._engine.get_summary()
            hs = summ.get("health", {}); ps = summ.get("pipeline", {})
            s  = summ.get("status", "--")
            lbl = self._status_labels
            lbl["status"].setText(s)
            sc = {"idle":_MUT,"running":_GRN,"paused":_YLW,
                  "degraded":_ORG,"stopped":_RED}.get(s, _FG)
            lbl["status"].setStyleSheet(
                f"color:{sc};font-size:11px;font-weight:bold;"
                f"border:none;background:transparent;")
            lbl["uptime"].setText(f'{summ.get("uptime",0):.0f}s')
            lbl["messages"].setText(str(summ.get("total_messages",0)))
            lbl["forwarded"].setText(str(summ.get("forwarded",0)))
            lbl["dropped"].setText(str(summ.get("dropped",0)))
            lbl["cycles"].setText(str(ps.get("cycle_count",0)))
            lbl["avg_cycle"].setText(f'{ps.get("avg_cycle_ms",0):.1f}')
            lbl["healthy"].setText(str(hs.get("healthy",0)))
            offline_n = hs.get("offline", 0)
            lbl["offline"].setText(str(offline_n))
            if offline_n > 0:
                lbl["offline"].setStyleSheet(
                    f"color:{_RED};font-size:11px;font-weight:bold;"
                    f"border:none;background:transparent;")
            lbl["risk_gate"].setText("OPEN" if summ.get("risk_gate_open") else "closed")
            self._refresh_health()
        except Exception:
            pass

    def _refresh_health(self):
        if self._engine is None: return
        records = self._engine.get_engine_health()
        self._health_tbl.setRowCount(0)
        hc = {"healthy":_GRN,"degraded":_YLW,"offline":_RED,"unknown":_MUT}
        for name, rec in sorted(records.items()):
            row = self._health_tbl.rowCount()
            self._health_tbl.insertRow(row)
            sc = hc.get(rec.status.value, _FG)
            cells = [rec.engine_name, rec.status.value,
                     str(rec.message_count), str(rec.error_count),
                     f"{rec.latency_ms:.1f}", str(rec.last_seen)[:16]]
            for col, txt in enumerate(cells):
                it = QtWidgets.QTableWidgetItem(txt)
                it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if col == 1: it.setForeground(QtGui.QColor(sc))
                self._health_tbl.setItem(row, col, it)

    def _append_pipeline_row(self, d: dict):
        tbl = self._pipeline_tbl
        row = tbl.rowCount(); tbl.insertRow(row)
        sc = _GRN if d.get("success") else _RED
        cells = [
            str(d.get("cycle_num","")), str(d.get("started_at",""))[:16],
            str(d.get("duration_ms","")),
            " | ".join(d.get("stages_done", [])),
            " | ".join(d.get("stages_skipped", [])),
            str(d.get("total_messages","")),
            "OK" if d.get("success") else "FAIL",
        ]
        for col, txt in enumerate(cells):
            it = QtWidgets.QTableWidgetItem(txt)
            it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if col == 6: it.setForeground(QtGui.QColor(sc))
            tbl.setItem(row, col, it)
        tbl.scrollToBottom()

    def closeEvent(self, event):
        self._refresh_timer.stop()
        try:
            self._event_engine.unregister(EVENT_BUS_MESSAGE, self._on_bus_msg_event)
            self._event_engine.unregister(EVENT_PIPELINE_CYCLE, self._on_cycle_event)
        except Exception:
            pass
        super().closeEvent(event)
