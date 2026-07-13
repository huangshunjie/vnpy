"""
execution_intelligence_ai/ui/widget.py  (Phase 1)

ExecutionIntelligenceWidget — 主窗口（Phase 1 骨架）。

布局：
  左侧（220px）：执行状态面板（Phase 1 显示引擎摘要）
  右侧：TabWidget（6 个 Tab，Phase 1 全部空占位）
"""

from __future__ import annotations
from datetime import datetime

from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.event import Event

from ..constant import APP_NAME
from ..event import (
    EVENT_EXECUTION_START, EVENT_ORDER_SLICED, EVENT_IMPACT_ESTIMATED,
    EVENT_ROUTE_SELECTED, EVENT_EXECUTION_COMPLETED, EVENT_FEEDBACK_UPDATED,
    EVENT_EXECUTION_ABORTED,
)
from .dashboard_tab import DashboardTab
from .slicing_tab   import SlicingTab
from .impact_tab    import ImpactTab
from .routing_tab   import RoutingTab
from .feedback_tab  import FeedbackTab
from .log_tab       import LogTab

_PANEL  = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_MAV    = "#cba6f7"
_GRN    = "#a6e3a1"


class ExecutionIntelligenceWidget(QtWidgets.QMainWindow):
    """
    Execution Intelligence 2.0 主窗口。

    Phase 1：骨架 + 事件订阅 + 引擎摘要显示。
    Phase 2+：各 Tab 逐步实现真实内容。
    """

    # Qt Signals（在主线程安全更新 UI）
    signal_log    = QtCore.Signal(str)
    signal_update = QtCore.Signal(dict)

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()

        self.main_engine  = main_engine
        self.event_engine = event_engine
        self.engine       = main_engine.get_engine(APP_NAME)

        self._init_ui()
        self._register_events()

        # 传引擎给所有 Tab
        for tab in [self._tab_dashboard, self._tab_slicing,
                    self._tab_impact, self._tab_routing,
                    self._tab_feedback, self._tab_log]:
            tab.set_engine(self.engine)

        # 定时刷新摘要（每 2 秒）
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start(2000)

        self._refresh_status()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        self.setWindowTitle(
            f"Execution Intelligence AI  执行智能系统  |  Phase 1")
        self.setMinimumSize(1100, 680)

        # 中心 widget
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        main_hbox = QtWidgets.QHBoxLayout(central)
        main_hbox.setContentsMargins(8, 8, 8, 8)
        main_hbox.setSpacing(8)

        # 左侧状态面板
        main_hbox.addWidget(self._build_status_panel(), stretch=0)

        # 右侧 TabWidget
        main_hbox.addWidget(self._build_tab_widget(), stretch=1)

    def _build_status_panel(self) -> QtWidgets.QWidget:
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(220)
        panel.setStyleSheet(
            f"background:{_PANEL}; border-radius:8px; "
            f"border:1px solid {_BORDER};")

        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(10)

        # 标题
        title = QtWidgets.QLabel("Execution\nIntelligence")
        title.setStyleSheet(
            f"color:{_MAV}; font-size:14px; font-weight:bold; border:none;")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # 分隔线
        layout.addWidget(self._sep())

        # 状态指示器
        self._status_dot  = QtWidgets.QLabel("● IDLE")
        self._status_dot.setStyleSheet(
            f"color:{_MUT}; font-size:11px; border:none;")
        self._status_dot.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_dot)

        layout.addWidget(self._sep())

        # 摘要 KPI
        self._kpi_phase   = self._kpi_row("Phase",       "1")
        self._kpi_uptime  = self._kpi_row("Uptime",      "--")
        self._kpi_active  = self._kpi_row("Active Tasks","0")
        self._kpi_done    = self._kpi_row("Completed",   "0")
        for w in [self._kpi_phase, self._kpi_uptime,
                  self._kpi_active, self._kpi_done]:
            layout.addWidget(w)

        layout.addWidget(self._sep())

        # 刷新按钮
        btn_refresh = QtWidgets.QPushButton("Refresh  刷新")
        btn_refresh.setStyleSheet(
            f"QPushButton {{background:transparent; color:{_MUT}; "
            f"border:1px solid {_BORDER}; border-radius:4px; "
            f"padding:5px; font-size:11px;}}"
            f"QPushButton:hover {{background:#313244;}}")
        btn_refresh.clicked.connect(self._refresh_all)
        layout.addWidget(btn_refresh)

        layout.addStretch()

        # 版本标签
        ver = QtWidgets.QLabel("v2.0  Phase 1")
        ver.setStyleSheet(f"color:{_MUT}; font-size:9px; border:none;")
        ver.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver)

        return panel

    def _build_tab_widget(self) -> QtWidgets.QTabWidget:
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane {{border:1px solid {_BORDER}; "
            f"background:{_PANEL}; border-radius:4px;}}"
            f"QTabBar::tab {{background:#313244; color:{_MUT}; "
            f"padding:6px 16px; border:none; border-radius:3px 3px 0 0; "
            f"margin-right:2px;}}"
            f"QTabBar::tab:selected {{background:{_PANEL}; color:{_FG};}}"
            f"QTabBar::tab:hover {{background:#45475a;}}"
        )

        self._tab_dashboard = DashboardTab()
        self._tab_slicing   = SlicingTab()
        self._tab_impact    = ImpactTab()
        self._tab_routing   = RoutingTab()
        self._tab_feedback  = FeedbackTab()
        self._tab_log       = LogTab()

        tabs.addTab(self._tab_dashboard, "Dashboard  总览")
        tabs.addTab(self._tab_slicing,   "Slicing  拆单")
        tabs.addTab(self._tab_impact,    "Impact  冲击")
        tabs.addTab(self._tab_routing,   "Routing  路由")
        tabs.addTab(self._tab_feedback,  "Feedback  反馈")
        tabs.addTab(self._tab_log,       "Logs  日志")

        return tabs

    def _kpi_row(self, label: str, value: str) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        w.setStyleSheet("border:none; background:transparent;")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet(f"color:{_MUT}; font-size:10px; border:none;")
        val = QtWidgets.QLabel(value)
        val.setStyleSheet(
            f"color:{_FG}; font-size:11px; font-weight:bold; border:none;")
        val.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        h.addWidget(lbl)
        h.addWidget(val)
        w._val = val
        return w

    def _sep(self) -> QtWidgets.QFrame:
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border:none; border-top:1px solid {_BORDER};")
        return s

    # ------------------------------------------------------------------ #
    #  事件订阅
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        for evt in [EVENT_EXECUTION_START, EVENT_ORDER_SLICED,
                    EVENT_IMPACT_ESTIMATED, EVENT_ROUTE_SELECTED,
                    EVENT_EXECUTION_COMPLETED, EVENT_FEEDBACK_UPDATED,
                    EVENT_EXECUTION_ABORTED]:
            self.event_engine.register(evt, self._on_execution_event)

        self.signal_log.connect(self._tab_log.append)
        self.signal_update.connect(self._on_update)

    def _on_execution_event(self, event: Event) -> None:
        """事件回调（跨线程，通过 Signal 转发到主线程）。"""
        msg = f"[{event.type}]  {event.data}"
        self.signal_log.emit(msg)
        self.signal_update.emit({"type": event.type, "data": event.data})

    def _on_update(self, payload: dict) -> None:
        """主线程 UI 更新。"""
        self._status_dot.setText(f"● {payload.get('type', 'EVENT')}")
        self._status_dot.setStyleSheet(f"color:{_GRN}; font-size:11px; border:none;")

    # ------------------------------------------------------------------ #
    #  刷新
    # ------------------------------------------------------------------ #

    def _refresh_status(self) -> None:
        if self.engine is None:
            return
        try:
            summ = self.engine.get_summary()
            phase  = summ.get("phase", 1)
            uptime = summ.get("uptime", 0.0)
            mins   = int(uptime // 60)
            secs   = int(uptime % 60)
            self._kpi_phase._val.setText(str(phase))
            self._kpi_uptime._val.setText(f"{mins}m {secs}s")
        except Exception:
            pass

    def _refresh_all(self) -> None:
        self._refresh_status()
        for tab in [self._tab_dashboard, self._tab_slicing,
                    self._tab_impact, self._tab_routing,
                    self._tab_feedback, self._tab_log]:
            try:
                tab.refresh()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    #  窗口关闭
    # ------------------------------------------------------------------ #

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._timer.stop()
        event.accept()
