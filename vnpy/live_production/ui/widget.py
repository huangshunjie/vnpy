"""
live_production/ui/widget.py

LiveProductionWidget — Live Production System 主窗口（Phase 1 骨架）。

布局：
  左侧（200px）：系统状态面板（占位）
  右侧：TabWidget（6 个空 Tab）
    1. 系统状态 System Status
    2. 订单同步 Order Sync
    3. 恢复系统 Recovery
    4. 故障切换 Failover
    5. 健康监控 Health Monitor
    6. 日志 Logs
"""

from __future__ import annotations

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import APP_NAME, TradingState, SystemHealthState
from ..event import (
    EVENT_PROD_START,
    EVENT_PROD_STOP,
    EVENT_STATE_CHANGE,
    EVENT_HEALTH_UPDATE,
)
from .status_tab   import StatusTab
from .order_tab    import OrderTab
from .recovery_tab import RecoveryTab
from .failover_tab import FailoverTab
from .health_tab   import HealthTab
from .log_tab      import LogTab

_DARK_BG  = "#1e1e2e"
_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"

_STATE_COLOR = {
    TradingState.INIT.value:     _MUT,
    TradingState.RUNNING.value:  _GRN,
    TradingState.DEGRADED.value: _YLW,
    TradingState.RECOVERY.value: _BLU,
    TradingState.STOPPED.value:  _RED,
}
_HEALTH_COLOR = {
    SystemHealthState.HEALTHY.value:  _GRN,
    SystemHealthState.WARNING.value:  _YLW,
    SystemHealthState.CRITICAL.value: _RED,
    SystemHealthState.UNKNOWN.value:  _MUT,
}


class LiveProductionWidget(QtWidgets.QMainWindow):
    """Live Production System 主窗口（Phase 1 骨架）。"""

    _signal_start  = QtCore.Signal(Event)
    _signal_stop   = QtCore.Signal(Event)
    _signal_state  = QtCore.Signal(Event)
    _signal_health = QtCore.Signal(Event)

    def __init__(
        self,
        main_engine:  MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__()
        self.main_engine  = main_engine
        self.event_engine = event_engine
        self.lp_engine    = main_engine.get_engine(APP_NAME)

        self._status_tab:   StatusTab   | None = None
        self._order_tab:    OrderTab    | None = None
        self._recovery_tab: RecoveryTab | None = None
        self._failover_tab: FailoverTab | None = None
        self._health_tab:   HealthTab   | None = None
        self._log_tab:      LogTab      | None = None

        self._lp_engine_ref = self.lp_engine
        self._init_ui()
        self._register_signals()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        self.setWindowTitle("实盘生产系统  Live Production System")
        self.setMinimumSize(1200, 720)
        self.setStyleSheet(f"QMainWindow {{ background: {_DARK_BG}; }}")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_left_panel(), stretch=0)
        root.addWidget(self._build_tab_widget(), stretch=1)

    def _build_left_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(200)
        panel.setStyleSheet(
            f"background: {_PANEL_BG}; border-radius: 6px;"
            f" border: 1px solid {_BORDER};"
        )
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        title = QtWidgets.QLabel("实盘生产系统")
        title.setStyleSheet(
            f"color: {_BLU}; font-size: 13px; font-weight: bold; border: none;")
        v.addWidget(title)

        sub = QtWidgets.QLabel("Live Production System")
        sub.setStyleSheet(f"color: {_MUT}; font-size: 10px; border: none;")
        v.addWidget(sub)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(
            f"color: {_BORDER}; border: none; border-top: 1px solid {_BORDER};")
        v.addWidget(sep)

        # 状态指示行
        self._lbl_state  = self._row(v, "交易状态  State", "INIT",    _MUT)
        self._lbl_health = self._row(v, "系统健康  Health", "UNKNOWN", _MUT)
        self._lbl_uptime = self._row(v, "运行时长  Uptime", "—",       _MUT)

        v.addStretch()

        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep2.setStyleSheet(
            f"color: {_BORDER}; border: none; border-top: 1px solid {_BORDER};")
        v.addWidget(sep2)

        # 控制按钮
        for label, color, slot in [
            ("▶ 启动  Start",  _GRN, self._on_start),
            ("■ 停止  Stop",   _RED, self._on_stop),
        ]:
            btn = QtWidgets.QPushButton(label)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color};"
                f" border: 1px solid {color}; border-radius: 4px;"
                f" padding: 6px 0px; font-size: 12px; border-style: solid; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            btn.clicked.connect(slot)
            v.addWidget(btn)

        return panel

    def _build_tab_widget(self) -> QtWidgets.QTabWidget:
        tabs = QtWidgets.QTabWidget()
        pane_style = (
            f"QTabWidget::pane {{ border: 1px solid {_BORDER}; border-radius: 4px; }}"
            f"QTabBar::tab {{ background: {_PANEL_BG}; color: {_MUT};"
            f" padding: 6px 16px; border-radius: 3px; }}"
            f"QTabBar::tab:selected {{ background: {_DARK_BG}; color: {_FG}; }}"
        )
        tabs.setStyleSheet(pane_style)

        eng = getattr(self.lp_engine, "_engine", None)

        self._status_tab   = StatusTab(engine=eng)
        self._order_tab    = OrderTab(engine=eng)
        self._recovery_tab = RecoveryTab(engine=eng)
        self._failover_tab = FailoverTab(engine=eng)
        self._health_tab   = HealthTab(engine=eng)
        self._log_tab      = LogTab(engine=eng)

        tabs.addTab(self._status_tab,   "系统状态 System Status")
        tabs.addTab(self._order_tab,    "订单同步 Order Sync")
        tabs.addTab(self._recovery_tab, "恢复系统 Recovery")
        tabs.addTab(self._failover_tab, "故障切换 Failover")
        tabs.addTab(self._health_tab,   "健康监控 Health Monitor")
        tabs.addTab(self._log_tab,      "日志 Logs")

        return tabs

    # ------------------------------------------------------------------ #
    #  信号注册
    # ------------------------------------------------------------------ #

    def _register_signals(self) -> None:
        self._signal_start.connect(self._on_event_start)
        self._signal_stop.connect(self._on_event_stop)
        self._signal_state.connect(self._on_event_state)
        self._signal_health.connect(self._on_event_health)

        reg = self.event_engine.register
        reg(EVENT_PROD_START,   self._signal_start.emit)
        reg(EVENT_PROD_STOP,    self._signal_stop.emit)
        reg(EVENT_STATE_CHANGE, self._signal_state.emit)
        reg(EVENT_HEALTH_UPDATE, self._signal_health.emit)

    def closeEvent(self, event) -> None:
        unreg = self.event_engine.unregister
        unreg(EVENT_PROD_START,    self._signal_start.emit)
        unreg(EVENT_PROD_STOP,     self._signal_stop.emit)
        unreg(EVENT_STATE_CHANGE,  self._signal_state.emit)
        unreg(EVENT_HEALTH_UPDATE, self._signal_health.emit)
        super().closeEvent(event)

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_start(self) -> None:
        if self.lp_engine:
            self.lp_engine.init()
            self.lp_engine.start()
            self._wire_tabs()
            if self._log_tab:
                self._log_tab.append("[INFO] Live Production System 已启动。")

    def _on_stop(self) -> None:
        if self.lp_engine:
            self.lp_engine.stop()
            if self._log_tab:
                self._log_tab.append("[INFO] Live Production System 已停止。")

    # ------------------------------------------------------------------ #
    #  事件回调
    # ------------------------------------------------------------------ #

    def _on_event_start(self, event: Event) -> None:
        self._lbl_state.setText("RUNNING")
        self._lbl_state.setStyleSheet(
            f"color: {_GRN}; font-size: 12px; font-weight: bold;")
        if self._log_tab:
            self._log_tab.append(f"[EVENT] {EVENT_PROD_START}")

    def _on_event_stop(self, event: Event) -> None:
        self._lbl_state.setText("STOPPED")
        self._lbl_state.setStyleSheet(
            f"color: {_RED}; font-size: 12px; font-weight: bold;")
        if self._log_tab:
            self._log_tab.append(f"[EVENT] {EVENT_PROD_STOP}")

    def _on_event_state(self, event: Event) -> None:
        data      = event.data or {}
        new_state = data.get("new_state", "")
        color     = _STATE_COLOR.get(new_state, _MUT)
        self._lbl_state.setText(new_state.upper())
        self._lbl_state.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: bold;")
        if self._log_tab:
            reason = data.get("reason", "")
            self._log_tab.append(
                f"[STATE] {data.get('old_state','')} → {new_state}  {reason}"
            )
        if self._status_tab:
            self._status_tab.refresh()
        _eng = getattr(self._lp_engine_ref, "_engine", None)
        if _eng:
            self._lbl_uptime.setText(f"{_eng.uptime_seconds:.0f}s")

    def _on_event_health(self, event: Event) -> None:
        data   = event.data or {}
        health = data.get("health_state", "unknown")
        color  = _HEALTH_COLOR.get(health, _MUT)
        self._lbl_health.setText(health.upper())
        self._lbl_health.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: bold;")
        if self._health_tab:
            self._health_tab.refresh()

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    def _wire_tabs(self) -> None:
        eng = getattr(self.lp_engine, "_engine", None)
        if eng is None:
            return
        for tab in (self._status_tab, self._order_tab, self._recovery_tab,
                    self._failover_tab, self._health_tab, self._log_tab):
            if tab is not None:
                tab.set_engine(eng)

    def _row(
        self,
        layout,
        label: str,
        value: str,
        color: str,
    ) -> QtWidgets.QLabel:
        row = QtWidgets.QWidget()
        row.setStyleSheet("border: none;")
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        ln = QtWidgets.QLabel(label)
        ln.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        lv = QtWidgets.QLabel(value)
        lv.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: bold;")
        h.addWidget(ln)
        h.addStretch()
        h.addWidget(lv)
        layout.addWidget(row)
        return lv
