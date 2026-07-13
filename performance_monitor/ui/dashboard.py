"""
performance_monitor/ui/dashboard.py

PerformanceDashboard — 系统级实时监控主窗口。

布局:
  顶部: KPI 总览条 (健康分 / 吞吐量 / 延迟 / 活跃模块 / 告警数)
  中部: 16模块卡片网格 (4列 × 4行)
  底部: 告警面板 + 指标历史表格
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine
from ..constant import APP_NAME, MONITORED_MODULES, ModuleStatus, AlertLevel
from ..event import EVENT_SNAPSHOT_UPDATED, EVENT_ALERT_CRITICAL, EVENT_ALERT_FATAL

_BG = "#1e1e2e"; _DARK = "#181825"; _BORDER = "#45475a"; _FG = "#cdd6f4"
_MUT = "#6c7086"; _GRN = "#a6e3a1"; _YLW = "#f9e2af"; _RED = "#f38ba8"
_MAV = "#cba6f7"; _HEAD = "#313244"; _CYN = "#89dceb"; _ORG = "#fab387"
_TEA = "#94e2d5"; _BLUE = "#89b4fa"

_STATUS_BG = {
    "active":   "#1a3a2a",
    "idle":     "#2a2a1a",
    "degraded": "#3a2a1a",
    "offline":  "#3a1a1a",
    "unknown":  "#1e1e2e",
}
_STATUS_BORDER = {
    "active":   _GRN,
    "idle":     _YLW,
    "degraded": _ORG,
    "offline":  _RED,
    "unknown":  _BORDER,
}
_STATUS_COLOR = {
    "active":   _GRN,
    "idle":     _YLW,
    "degraded": _ORG,
    "offline":  _RED,
    "unknown":  _MUT,
}
_ALERT_COLOR = {
    AlertLevel.INFO:     _BLUE,
    AlertLevel.WARNING:  _YLW,
    AlertLevel.CRITICAL: _ORG,
    AlertLevel.FATAL:    _RED,
}
_MODULE_LABEL = {
    "data_intelligence_ai":          "DIL",
    "alpha_factory_2":               "Alpha",
    "market_regime_ai":              "Regime",
    "portfolio_engine":              "Portfolio",
    "capital_allocation_ai":         "Capital",
    "risk_engine_2":                 "Risk",
    "strategy_lifecycle_ai":         "Strategy",
    "execution_engine":              "Execution",
    "execution_intelligence_ai":     "Exec-Intel",
    "adaptive_learning_ai":          "Learning",
    "global_portfolio_intelligence": "GlobalPort",
    "live_production":               "Live",
    "quant_os":                      "QuantOS",
    "factor_research":               "Factor",
    "research_validation":           "Research",
    "system_integration_bus":        "SIBus",
}
_TBL = (
    "QTableWidget{background:#181825;color:#cdd6f4;border:1px solid #45475a;"
    "gridline-color:#45475a;font-size:10px;}"
    "QTableWidget::item{padding:2px 5px;}"
    "QTableWidget::item:alternate{background:#1e1e2e;}"
    "QHeaderView::section{background:#313244;color:#6c7086;border:none;"
    "border-bottom:1px solid #45475a;padding:3px 5px;font-size:9px;}"
)


def _lbl(t, s=""):
    w = QtWidgets.QLabel(t); w.setStyleSheet(s); return w


class _ModuleCard(QtWidgets.QWidget):
    """单个模块的状态卡片。"""

    def __init__(self, module: str, parent=None):
        super().__init__(parent)
        self._module = module
        self._status = "unknown"
        self.setFixedSize(168, 110)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(
            f"background:{_STATUS_BG['unknown']};"
            f"border:1px solid {_BORDER};border-radius:6px;")
        vb = QtWidgets.QVBoxLayout(self)
        vb.setContentsMargins(8, 6, 8, 6); vb.setSpacing(3)

        top = QtWidgets.QHBoxLayout()
        label = _MODULE_LABEL.get(self._module, self._module[:10])
        self._name_lbl = QtWidgets.QLabel(label)
        self._name_lbl.setStyleSheet(
            f"color:{_FG};font-weight:bold;font-size:11px;"
            f"border:none;background:transparent;")
        self._status_dot = QtWidgets.QLabel("●")
        self._status_dot.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        top.addWidget(self._name_lbl)
        top.addStretch()
        top.addWidget(self._status_dot)
        vb.addLayout(top)

        self._status_lbl = QtWidgets.QLabel("unknown")
        self._status_lbl.setStyleSheet(
            f"color:{_MUT};font-size:9px;border:none;background:transparent;")
        vb.addWidget(self._status_lbl)

        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(0, 2, 0, 0); grid.setSpacing(1)
        self._kv: dict[str, QtWidgets.QLabel] = {}
        for row, (key, lbl_txt) in enumerate([
            ("lat",  "Lat ms"),
            ("tput", "Evt/min"),
            ("err",  "ErrRate"),
            ("evts", "Events"),
        ]):
            lk = QtWidgets.QLabel(lbl_txt)
            lk.setStyleSheet(
                f"color:{_MUT};font-size:8px;border:none;background:transparent;")
            lv = QtWidgets.QLabel("--")
            lv.setStyleSheet(
                f"color:{_TEA};font-size:9px;font-weight:bold;"
                f"border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            grid.addWidget(lk, row, 0)
            grid.addWidget(lv, row, 1)
            self._kv[key] = lv
        vb.addLayout(grid)

    def refresh(self, m_dict: dict):
        status = m_dict.get("status", "unknown")
        if status != self._status:
            self._status = status
            bg     = _STATUS_BG.get(status, _STATUS_BG["unknown"])
            border = _STATUS_BORDER.get(status, _BORDER)
            self.setStyleSheet(
                f"background:{bg};border:1px solid {border};border-radius:6px;")
        dot_c = _STATUS_COLOR.get(status, _MUT)
        self._status_dot.setStyleSheet(
            f"color:{dot_c};font-size:10px;border:none;background:transparent;")
        self._status_lbl.setText(status)
        self._status_lbl.setStyleSheet(
            f"color:{dot_c};font-size:9px;border:none;background:transparent;")

        lat  = m_dict.get("avg_latency_1m", 0.0)
        tput = m_dict.get("throughput_1m",  0.0)
        err  = m_dict.get("error_rate_1m",  0.0)
        evts = m_dict.get("event_count",    0)

        lat_c = _GRN if lat < 500 else (_YLW if lat < 2000 else _RED)
        err_c = _GRN if err < 0.05 else (_YLW if err < 0.20 else _RED)

        self._kv["lat"].setText(f"{lat:.0f}")
        self._kv["lat"].setStyleSheet(
            f"color:{lat_c};font-size:9px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._kv["tput"].setText(f"{tput:.1f}")
        self._kv["err"].setText(f"{err:.1%}")
        self._kv["err"].setStyleSheet(
            f"color:{err_c};font-size:9px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._kv["evts"].setText(str(evts))


class PerformanceDashboard(QtWidgets.QMainWindow):
    """全系统实时监控 Dashboard 主窗口。"""

    widget_name = APP_NAME

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = main_engine.get_engine(APP_NAME)
        self._cards: dict[str, _ModuleCard] = {}
        self._init_ui()
        self._init_menu()
        self._register_events()
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(5000)   # 5-second auto-refresh

    def _init_ui(self):
        self.setWindowTitle("Performance Monitor  全系统实时监控")
        self.resize(1500, 900)
        self.setStyleSheet(f"background:{_BG}; color:{_FG};")
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        vb = QtWidgets.QVBoxLayout(central)
        vb.setContentsMargins(8,8,8,8); vb.setSpacing(8)
        vb.addWidget(self._build_kpi_bar())
        vb.addWidget(self._build_cards_grid(), stretch=1)
        vb.addWidget(self._build_bottom_panel())

    def _build_kpi_bar(self):
        w = QtWidgets.QWidget(); w.setFixedHeight(72)
        w.setStyleSheet(
            f"background:{_DARK};border-radius:5px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(20,8,20,8); h.setSpacing(24)
        self._kpi: dict[str, QtWidgets.QLabel] = {}
        for key, txt, color in [
            ("health","Health Score",_GRN),("throughput","Events/min",_TEA),
            ("latency","Avg Lat ms",_YLW),("active","Active Mods",_BLUE),
            ("offline","Offline",_RED),("alerts","Alerts",_MAV),
            ("events","Total Events",_FG),("errors","Total Errors",_ORG),
        ]:
            cell = QtWidgets.QWidget()
            cell.setStyleSheet("background:transparent;border:none;")
            cv = QtWidgets.QVBoxLayout(cell)
            cv.setContentsMargins(0,0,0,0); cv.setSpacing(2)
            lk = QtWidgets.QLabel(txt)
            lk.setStyleSheet(
                f"color:{_MUT};font-size:9px;border:none;background:transparent;")
            lk.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            lv = QtWidgets.QLabel("--")
            lv.setStyleSheet(
                f"color:{color};font-size:15px;font-weight:bold;"
                f"border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            cv.addWidget(lk); cv.addWidget(lv)
            self._kpi[key] = lv; h.addWidget(cell)
        h.addStretch()
        self._refresh_lbl = QtWidgets.QLabel("--")
        self._refresh_lbl.setStyleSheet(
            f"color:{_MUT};font-size:9px;border:none;background:transparent;")
        h.addWidget(self._refresh_lbl)
        return w

    def _build_cards_grid(self):
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea{{background:transparent;border:none;}}"
            f"QScrollBar:vertical{{background:{_DARK};width:8px;border:none;}}"
            f"QScrollBar::handle:vertical{{background:{_BORDER};border-radius:4px;}}")
        inner = QtWidgets.QWidget(); inner.setStyleSheet("background:transparent;")
        grid  = QtWidgets.QGridLayout(inner)
        grid.setContentsMargins(4,4,4,4); grid.setSpacing(8)
        for idx, mod in enumerate(MONITORED_MODULES):
            card = _ModuleCard(mod)
            self._cards[mod] = card
            grid.addWidget(card, idx // 4, idx % 4)
        scroll.setWidget(inner)
        return scroll

    def _build_bottom_panel(self):
        w = QtWidgets.QWidget(); w.setFixedHeight(200)
        w.setStyleSheet("background:transparent;")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0,0,0,0); h.setSpacing(8)
        h.addWidget(self._build_alert_table(),   stretch=1)
        h.addWidget(self._build_metrics_table(), stretch=1)
        return w

    def _build_alert_table(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:4px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(8,6,8,6); vb.setSpacing(4)
        vb.addWidget(_lbl("Active Alerts",
                          f"color:{_MAV};font-size:10px;font-weight:bold;border:none;"))
        cols = ["Module","Level","Message","Fired At"]
        self._alert_tbl = QtWidgets.QTableWidget(0, len(cols))
        self._alert_tbl.setHorizontalHeaderLabels(cols)
        self._alert_tbl.verticalHeader().setVisible(False)
        self._alert_tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._alert_tbl.setAlternatingRowColors(True)
        self._alert_tbl.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._alert_tbl.horizontalHeader().setStretchLastSection(True)
        self._alert_tbl.setStyleSheet(_TBL)
        vb.addWidget(self._alert_tbl)
        return w

    def _build_metrics_table(self):
        w = QtWidgets.QWidget()
        w.setStyleSheet(
            f"background:{_DARK};border-radius:4px;border:1px solid {_BORDER};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setContentsMargins(8,6,8,6); vb.setSpacing(4)
        vb.addWidget(_lbl("Module Metrics (by Event Count)",
                          f"color:{_YLW};font-size:10px;font-weight:bold;border:none;"))
        cols = ["Module","Status","Events","Errors",
                "Avg Lat ms","P95 ms","Tput/min","ErrRate"]
        self._metric_tbl = QtWidgets.QTableWidget(0, len(cols))
        self._metric_tbl.setHorizontalHeaderLabels(cols)
        self._metric_tbl.verticalHeader().setVisible(False)
        self._metric_tbl.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._metric_tbl.setAlternatingRowColors(True)
        self._metric_tbl.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._metric_tbl.horizontalHeader().setStretchLastSection(True)
        self._metric_tbl.setStyleSheet(_TBL)
        vb.addWidget(self._metric_tbl)
        return w

    def _init_menu(self):
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar{{background:{_DARK};color:{_FG};border:none;}}"
            f"QMenuBar::item:selected{{background:{_HEAD};}}"
            f"QMenu{{background:{_DARK};color:{_FG};border:1px solid {_BORDER};}}"
            f"QMenu::item:selected{{background:{_HEAD};}}")
        m = mb.addMenu("Monitor")
        m.addAction("Start").triggered.connect(self._on_start)
        m.addAction("Stop").triggered.connect(self._on_stop)
        m.addSeparator()
        m.addAction("Force Update").triggered.connect(self._on_tick)
        m.addAction("Resolve All Alerts").triggered.connect(self._on_resolve_all)
        m.addSeparator()
        m.addAction("Close").triggered.connect(self.close)

    def _register_events(self):
        self._event_engine.register(EVENT_SNAPSHOT_UPDATED, self._on_snapshot_event)
        self._event_engine.register(EVENT_ALERT_CRITICAL,   self._on_alert_event)
        self._event_engine.register(EVENT_ALERT_FATAL,      self._on_alert_event)

    def _on_snapshot_event(self, event):
        d = event.data or {}
        hs = d.get("health_score", 100.0)
        hs_c = _GRN if hs >= 80 else (_YLW if hs >= 50 else _RED)
        self._kpi["health"].setText(f"{hs:.1f}")
        self._kpi["health"].setStyleSheet(
            f"color:{hs_c};font-size:15px;font-weight:bold;"
            f"border:none;background:transparent;")
        self._kpi["active"].setText(str(d.get("active_count","--")))
        off = d.get("offline_count", 0)
        self._kpi["offline"].setText(str(off))
        if off > 0:
            self._kpi["offline"].setStyleSheet(
                f"color:{_RED};font-size:15px;font-weight:bold;"
                f"border:none;background:transparent;")
        self._kpi["alerts"].setText(str(d.get("active_alerts", 0)))

    def _on_alert_event(self, event):
        QtWidgets.QApplication.beep()
        self._update_alerts()

    def _on_start(self):
        if self._engine:
            self._engine.init(); self._engine.start()

    def _on_stop(self):
        if self._engine: self._engine.stop()

    def _on_resolve_all(self):
        if self._engine:
            for mod in MONITORED_MODULES:
                self._engine.resolve_module_alerts(mod)
            self._update_alerts()

    def _on_tick(self):
        if self._engine is None: return
        try:
            snap = self._engine.update()
            self._refresh_dashboard(snap)
        except Exception:
            pass

    def _refresh_dashboard(self, snap):
        summ = self._engine.get_summary()
        hs   = summ.get("health_score", 100.0)
        hs_c = _GRN if hs >= 80 else (_YLW if hs >= 50 else _RED)
        kpi  = self._kpi
        kpi["health"].setText(f"{hs:.1f}")
        kpi["health"].setStyleSheet(
            f"color:{hs_c};font-size:15px;font-weight:bold;"
            f"border:none;background:transparent;")
        kpi["throughput"].setText(f'{summ.get("system_throughput",0):.1f}')
        kpi["latency"].setText(f'{summ.get("avg_latency_ms",0):.0f}')
        kpi["active"].setText(str(summ.get("active_count",0)))
        off = summ.get("offline_count", 0)
        kpi["offline"].setText(str(off))
        if off > 0:
            kpi["offline"].setStyleSheet(
                f"color:{_RED};font-size:15px;font-weight:bold;"
                f"border:none;background:transparent;")
        alrt = summ.get("alerts", {})
        kpi["alerts"].setText(str(alrt.get("active_total",0)))
        kpi["events"].setText(str(summ.get("total_events",0)))
        kpi["errors"].setText(str(summ.get("total_errors",0)))
        self._refresh_lbl.setText(f"Last: {str(snap.taken_at)[:19]}")
        for mod, card in self._cards.items():
            m_dict = snap.modules.get(mod, {})
            if m_dict: card.refresh(m_dict)
        self._update_metrics_table(snap)
        self._update_alerts()

    def _update_metrics_table(self, snap):
        mods_sorted = sorted(snap.modules.items(),
                              key=lambda x: x[1].get("event_count",0), reverse=True)
        self._metric_tbl.setRowCount(0)
        sc_map = {"active":_GRN,"idle":_YLW,"degraded":_ORG,
                  "offline":_RED,"unknown":_MUT}
        for mod, d in mods_sorted:
            row = self._metric_tbl.rowCount(); self._metric_tbl.insertRow(row)
            st  = d.get("status","unknown")
            sc  = sc_map.get(st, _FG)
            err = d.get("error_rate_1m", 0.0)
            ec  = _GRN if err < 0.05 else (_YLW if err < 0.2 else _RED)
            cells = [
                _MODULE_LABEL.get(mod, mod), st,
                str(d.get("event_count",0)), str(d.get("error_count",0)),
                f'{d.get("avg_latency_1m",0):.1f}',
                f'{d.get("p95_latency_1m",0):.1f}',
                f'{d.get("throughput_1m",0):.1f}',
                f'{err:.1%}',
            ]
            for col, txt in enumerate(cells):
                it = QtWidgets.QTableWidgetItem(txt)
                it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if col == 1: it.setForeground(QtGui.QColor(sc))
                if col == 7: it.setForeground(QtGui.QColor(ec))
                self._metric_tbl.setItem(row, col, it)

    def _update_alerts(self):
        if self._engine is None: return
        alerts = self._engine.get_active_alerts()
        self._alert_tbl.setRowCount(0)
        lc_map = {"info":_BLUE,"warning":_YLW,"critical":_ORG,"fatal":_RED}
        for a in reversed(alerts[-30:]):
            row = self._alert_tbl.rowCount(); self._alert_tbl.insertRow(row)
            lc = lc_map.get(a.level.value, _FG)
            cells = [a.module, a.level.value, a.message, str(a.fired_at)[:16]]
            for col, txt in enumerate(cells):
                it = QtWidgets.QTableWidgetItem(txt)
                it.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                if col == 1: it.setForeground(QtGui.QColor(lc))
                self._alert_tbl.setItem(row, col, it)

    def closeEvent(self, event):
        self._timer.stop()
        try:
            self._event_engine.unregister(EVENT_SNAPSHOT_UPDATED, self._on_snapshot_event)
            self._event_engine.unregister(EVENT_ALERT_CRITICAL,   self._on_alert_event)
            self._event_engine.unregister(EVENT_ALERT_FATAL,      self._on_alert_event)
        except Exception:
            pass
        super().closeEvent(event)
