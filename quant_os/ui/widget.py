"""
quant_os/ui/widget.py

QuantOSWidget — Quant OS 主窗口（Phase 5 最终版）。
"""

from __future__ import annotations

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import APP_NAME, OsState
from ..engine.system_controller import SystemHealth
from ..event import (
    EVENT_OS_START, EVENT_OS_STOP,
    EVENT_MODULE_REGISTERED, EVENT_LIFECYCLE_CHANGE,
    EVENT_STRATEGY_TRIGGER, EVENT_SYSTEM_LOG,
)
from .dashboard_tab import DashboardTab
from .lifecycle_tab import LifecycleTab
from .strategy_tab  import StrategyTab
from .module_tab    import ModuleTab
from .control_tab   import ControlTab
from .log_tab       import LogTab

_DARK_BG  = "#1e1e2e"
_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"

_HEALTH_COLOR = {
    SystemHealth.HEALTHY.value:  _GRN,
    SystemHealth.DEGRADED.value: _YLW,
    SystemHealth.CRITICAL.value: _RED,
    SystemHealth.STOPPED.value:  _MUT,
}


class QuantOSWidget(QtWidgets.QMainWindow):
    """Quant OS 主窗口（Phase 5 最终版）。"""

    _signal_log       = QtCore.Signal(Event)
    _signal_start     = QtCore.Signal(Event)
    _signal_stop      = QtCore.Signal(Event)
    _signal_module    = QtCore.Signal(Event)
    _signal_lifecycle = QtCore.Signal(Event)
    _signal_trigger   = QtCore.Signal(Event)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self.main_engine  = main_engine
        self.event_engine = event_engine
        self.os_engine    = main_engine.get_engine(APP_NAME)

        self._dashboard_tab:  DashboardTab | None = None
        self._lifecycle_tab:  LifecycleTab | None = None
        self._strategy_tab:   StrategyTab  | None = None
        self._module_tab:     ModuleTab    | None = None
        self._control_tab:    ControlTab   | None = None
        self._log_tab:        LogTab       | None = None

        self._init_ui()
        self._register_signals()

    def _init_ui(self) -> None:
        self.setWindowTitle("Quant OS \u2014 \u91cf\u5316\u64cd\u4f5c\u7cfb\u7edf")
        self.setMinimumSize(1200, 720)
        self.setStyleSheet(f"QMainWindow {{ background: {_DARK_BG}; }}")
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)
        root.addWidget(self._build_status_panel(), stretch=0)
        root.addWidget(self._build_tab_widget(),   stretch=1)

    def _build_status_panel(self):
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(220)
        panel.setStyleSheet(
            f"background: {_PANEL_BG}; border-radius: 6px;"
            f" border: 1px solid {_BORDER};"
        )
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)
        title = QtWidgets.QLabel("Quant OS  状态")
        title.setStyleSheet(
            f"color: {_BLU}; font-size: 13px; font-weight: bold; border: none;")
        v.addWidget(title)
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(
            f"color: {_BORDER}; border: none; border-top: 1px solid {_BORDER};")
        v.addWidget(sep)
        self._lbl_os_state   = self._status_row(v, "OS 状态",    "IDLE",    _MUT)
        self._lbl_health     = self._status_row(v, "系统健康",   "STOPPED", _MUT)
        self._lbl_modules    = self._status_row(v, "已注册模块", "0",       _MUT)
        self._lbl_running    = self._status_row(v, "运行中",     "0",       _GRN)
        self._lbl_errors     = self._status_row(v, "错误模块",   "0",       _MUT)
        self._lbl_alpha_live = self._status_row(v, "Alpha Live", "0",       _BLU)
        self._lbl_strat_live = self._status_row(v, "Strat Live", "0",       _BLU)
        self._lbl_triggers   = self._status_row(v, "触发次数",   "0",       _YLW)
        self._lbl_uptime     = self._status_row(v, "运行时长",   "---",     _MUT)
        v.addStretch()
        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep2.setStyleSheet(
            f"color: {_BORDER}; border: none; border-top: 1px solid {_BORDER};")
        v.addWidget(sep2)
        for label, color, slot in [
            ("▶ 启动 OS  Start",  _GRN, self._on_btn_start),
            ("⏸ 暂停 OS  Pause",  _YLW, self._on_btn_pause),
            ("▶ 恢复 OS  Resume", _BLU, self._on_btn_resume),
            ("■ 停止 OS  Stop",   _RED, self._on_btn_stop),
        ]:
            btn = QtWidgets.QPushButton(label)
            btn.setStyleSheet(self._btn_style(color))
            btn.clicked.connect(slot)
            v.addWidget(btn)
        return panel

    def _build_tab_widget(self):
        tabs = QtWidgets.QTabWidget()
        pane_style = (
            f"QTabWidget::pane {{ border: 1px solid {_BORDER}; border-radius: 4px; }}"
            f"QTabBar::tab {{ background: {_PANEL_BG}; color: {_MUT};"
            f" padding: 6px 16px; border-radius: 3px; }}"
            f"QTabBar::tab:selected {{ background: {_DARK_BG}; color: {_FG}; }}"
        )
        tabs.setStyleSheet(pane_style)
        inner = getattr(self.os_engine, "_os_engine", None)
        self._dashboard_tab = DashboardTab(os_engine=inner)
        self._lifecycle_tab = LifecycleTab(os_engine=inner)
        self._strategy_tab  = StrategyTab(os_engine=inner)
        self._module_tab    = ModuleTab(os_engine=inner)
        self._control_tab   = ControlTab(os_engine=inner)
        self._log_tab       = LogTab(os_engine=inner)
        tabs.addTab(self._dashboard_tab, "总览 Dashboard")
        tabs.addTab(self._lifecycle_tab, "生命周期 Lifecycle")
        tabs.addTab(self._strategy_tab,  "调度 Orchestration")
        tabs.addTab(self._module_tab,    "模块注册 Module Registry")
        tabs.addTab(self._control_tab,   "系统控制 Control Panel")
        tabs.addTab(self._log_tab,       "日志 Logs")
        return tabs

    def _register_signals(self) -> None:
        self._signal_log.connect(self._on_log)
        self._signal_start.connect(self._on_os_start)
        self._signal_stop.connect(self._on_os_stop)
        self._signal_module.connect(self._on_module_event)
        self._signal_lifecycle.connect(self._on_lifecycle_event)
        self._signal_trigger.connect(self._on_trigger_event)
        reg = self.event_engine.register
        reg(EVENT_SYSTEM_LOG,        self._signal_log.emit)
        reg(EVENT_OS_START,          self._signal_start.emit)
        reg(EVENT_OS_STOP,           self._signal_stop.emit)
        reg(EVENT_MODULE_REGISTERED, self._signal_module.emit)
        reg(EVENT_LIFECYCLE_CHANGE,  self._signal_lifecycle.emit)
        reg(EVENT_STRATEGY_TRIGGER,  self._signal_trigger.emit)

    def closeEvent(self, event) -> None:
        unreg = self.event_engine.unregister
        unreg(EVENT_SYSTEM_LOG,        self._signal_log.emit)
        unreg(EVENT_OS_START,          self._signal_start.emit)
        unreg(EVENT_OS_STOP,           self._signal_stop.emit)
        unreg(EVENT_MODULE_REGISTERED, self._signal_module.emit)
        unreg(EVENT_LIFECYCLE_CHANGE,  self._signal_lifecycle.emit)
        unreg(EVENT_STRATEGY_TRIGGER,  self._signal_trigger.emit)
        super().closeEvent(event)

    def _on_log(self, event) -> None:
        data = event.data or {}
        msg  = data.get("message", str(data))
        if self._log_tab:
            self._log_tab.append_event(EVENT_SYSTEM_LOG, data)
        if self._dashboard_tab:
            self._dashboard_tab.append_log(msg)
        self._refresh_left_panel()

    def _on_os_start(self, event) -> None:
        self._lbl_os_state.setText("RUNNING")
        self._lbl_os_state.setStyleSheet(
            f"color: {_GRN}; font-size: 12px; font-weight: bold;")
        self._refresh_all_tabs()

    def _on_os_stop(self, event) -> None:
        self._lbl_os_state.setText("STOPPED")
        self._lbl_os_state.setStyleSheet(
            f"color: {_RED}; font-size: 12px; font-weight: bold;")
        self._refresh_all_tabs()

    def _on_module_event(self, event) -> None:
        if self._module_tab:    self._module_tab.refresh()
        if self._dashboard_tab: self._dashboard_tab.refresh()
        self._refresh_left_panel()

    def _on_lifecycle_event(self, event) -> None:
        if self._lifecycle_tab: self._lifecycle_tab.refresh()
        if self._dashboard_tab: self._dashboard_tab.refresh()
        self._refresh_left_panel()

    def _on_trigger_event(self, event) -> None:
        if self._strategy_tab:  self._strategy_tab.refresh()
        if self._dashboard_tab: self._dashboard_tab.refresh()
        self._refresh_left_panel()

    def _on_btn_start(self) -> None:
        if not self.os_engine:
            return
        self.os_engine.init()
        self.os_engine.start()
        self._wire_tabs()
        self._refresh_all_tabs()

    def _on_btn_pause(self) -> None:
        if self.os_engine and self.os_engine.os_engine:
            self.os_engine.os_engine.pause()
            self.os_engine.pause_system()
            self._refresh_left_panel()

    def _on_btn_resume(self) -> None:
        if self.os_engine and self.os_engine.os_engine:
            self.os_engine.os_engine.resume()
            self.os_engine.resume_system()
            self._refresh_left_panel()

    def _on_btn_stop(self) -> None:
        if self.os_engine:
            self.os_engine.stop_system()
            self.os_engine.stop()
            self._refresh_all_tabs()

    def _wire_tabs(self) -> None:
        inner = getattr(self.os_engine, "_os_engine", None)
        if inner is None:
            return
        for tab in (self._dashboard_tab, self._lifecycle_tab,
                    self._strategy_tab,  self._module_tab,
                    self._control_tab,   self._log_tab):
            if tab is not None:
                tab.set_os_engine(inner)

    def _refresh_all_tabs(self) -> None:
        for tab in (self._dashboard_tab, self._lifecycle_tab,
                    self._strategy_tab,  self._module_tab,
                    self._control_tab):
            if tab is not None:
                try:
                    tab.refresh()
                except Exception:
                    pass
        self._refresh_left_panel()

    def _refresh_left_panel(self) -> None:
        if not (self.os_engine and self.os_engine.os_engine):
            return
        ose  = self.os_engine.os_engine
        summ = ose.get_summary()
        health = summ.get("system_health", "stopped")
        h_col  = _HEALTH_COLOR.get(health, _MUT)
        self._lbl_health.setText(health.upper())
        self._lbl_health.setStyleSheet(
            f"color: {h_col}; font-size: 12px; font-weight: bold;")
        mods = summ.get("modules", {})
        if isinstance(mods, dict):
            self._lbl_modules.setText(str(mods.get("total", 0)))
            running = mods.get("running", 0)
            errors  = mods.get("errors",  0)
        else:
            running = errors = 0
        self._lbl_running.setText(str(running))
        self._lbl_running.setStyleSheet(
            f"color: {_GRN if running > 0 else _MUT};"
            f" font-size: 12px; font-weight: bold;")
        self._lbl_errors.setText(str(errors))
        self._lbl_errors.setStyleSheet(
            f"color: {_RED if errors > 0 else _MUT};"
            f" font-size: 12px; font-weight: bold;")
        lc = summ.get("lifecycle", {})
        self._lbl_alpha_live.setText(
            str(lc.get("alpha", {}).get("by_state", {}).get("live", 0)))
        self._lbl_strat_live.setText(
            str(lc.get("strategy", {}).get("by_state", {}).get("live_trading", 0)))
        orch = summ.get("orchestrator", {})
        self._lbl_triggers.setText(
            str(orch.get("triggers", {}).get("total", 0)))
        self._lbl_uptime.setText(f"{summ.get('uptime', 0):.0f}s")

    def _status_row(self, layout, label: str, value: str, color: str):
        row = QtWidgets.QWidget()
        row.setStyleSheet("border: none;")
        h = QtWidgets.QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        ln = QtWidgets.QLabel(label)
        ln.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        lv = QtWidgets.QLabel(value)
        lv.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        h.addWidget(ln)
        h.addStretch()
        h.addWidget(lv)
        layout.addWidget(row)
        return lv

    @staticmethod
    def _btn_style(color: str) -> str:
        return (
            f"QPushButton {{ background: transparent; color: {color};"
            f" border: 1px solid {color}; border-radius: 4px;"
            f" padding: 6px 0px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {color}22; }}"
        )
