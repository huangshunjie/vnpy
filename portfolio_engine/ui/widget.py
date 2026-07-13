"""
portfolio_engine/ui/widget.py

PortfolioEngineWidget — Portfolio Engine 主窗口。

布局：
┌──────────────────────────────────────────────────────────────┐
│  LeftPanel (300px)  │  TabWidget (stretch)                   │
│                     │  Overview / Allocation / Risk /        │
│                     │  Performance / Rebalance /             │
│                     │  Attribution / Report                  │
└──────────────────────────────────────────────────────────────┘

事件监听（Phase 2 接入）：
  EVENT_PORTFOLIO_UPDATE   → 刷新 Overview / Allocation / Performance
  EVENT_PORTFOLIO_RISK     → 刷新 Risk / Attribution
  EVENT_PORTFOLIO_REBALANCE → 刷新 Rebalance
  EVENT_PORTFOLIO_LOG      → 日志输出

Phase 1：UI 骨架完整可显示，Tab 均为占位页面，
         事件监听注册到位但回调为 pass。
"""

from __future__ import annotations

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import APP_NAME
from ..event import (
    EVENT_PORTFOLIO_LOG,
    EVENT_PORTFOLIO_REBALANCE,
    EVENT_PORTFOLIO_RISK,
    EVENT_PORTFOLIO_UPDATE,
)
from .left_panel import LeftPanel
from .overview_tab import OverviewTab
from .allocation_tab import AllocationTab
from .risk_tab import RiskTab
from .performance_tab import PerformanceTab
from .rebalance_tab import RebalanceTab
from .attribution_tab import AttributionTab
from .report_tab import ReportTab


class PortfolioEngineWidget(QtWidgets.QWidget):
    """Portfolio Engine 主窗口。"""

    # Qt Signal: receive VeighNa events on the UI thread
    _signal_update    = QtCore.Signal(Event)
    _signal_risk      = QtCore.Signal(Event)
    _signal_rebalance = QtCore.Signal(Event)
    _signal_log       = QtCore.Signal(Event)

    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__()
        self.main_engine  = main_engine
        self.event_engine = event_engine

        self.setWindowTitle("组合管理引擎")
        self.resize(1280, 800)

        self._init_ui()
        self._register_events()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # 左侧面板
        self.left_panel = LeftPanel(self)
        self.left_panel.run_requested.connect(self._on_run_requested)
        self.left_panel.stop_requested.connect(self._on_stop_requested)
        root.addWidget(self.left_panel)

        # 右侧 Tab 容器
        right = QtWidgets.QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(4)

        self.tab_widget = self._build_tab_widget()
        right.addWidget(self.tab_widget)

        # 底部日志栏
        self.txt_log = QtWidgets.QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(80)
        self.txt_log.setStyleSheet(
            "background: #181825; color: #cdd6f4; font-size: 11px; font-family: monospace;"
        )
        right.addWidget(self.txt_log)

        root.addLayout(right, stretch=1)

    def _build_tab_widget(self) -> QtWidgets.QTabWidget:
        tw = QtWidgets.QTabWidget()

        self.overview_tab    = OverviewTab(self)
        self.allocation_tab  = AllocationTab(self)
        self.risk_tab        = RiskTab(self)
        self.performance_tab = PerformanceTab(self)
        self.rebalance_tab   = RebalanceTab(self)
        self.attribution_tab = AttributionTab(self)
        self.report_tab      = ReportTab(self)

        tw.addTab(self.overview_tab,    "概览")
        tw.addTab(self.allocation_tab,  "权重分配")
        tw.addTab(self.risk_tab,        "风险暴露")
        tw.addTab(self.performance_tab, "组合绩效")
        tw.addTab(self.rebalance_tab,   "调仓历史")
        tw.addTab(self.attribution_tab, "回撤归因")
        tw.addTab(self.report_tab,      "报告导出")
        return tw

    # ------------------------------------------------------------------ #
    #  事件注册 / 注销
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        """注册 VeighNa 事件 → Qt Signal（跨线程安全）。"""
        reg = self.event_engine.register

        # 将 VeighNa 事件桥接到 Qt Signal，避免跨线程直接操作 UI
        self._signal_update.connect(self._on_portfolio_update)
        self._signal_risk.connect(self._on_portfolio_risk)
        self._signal_rebalance.connect(self._on_portfolio_rebalance)
        self._signal_log.connect(self._on_portfolio_log)

        reg(EVENT_PORTFOLIO_UPDATE,    self._signal_update.emit)
        reg(EVENT_PORTFOLIO_RISK,      self._signal_risk.emit)
        reg(EVENT_PORTFOLIO_REBALANCE, self._signal_rebalance.emit)
        reg(EVENT_PORTFOLIO_LOG,       self._signal_log.emit)

    def _unregister_events(self) -> None:
        unreg = self.event_engine.unregister
        unreg(EVENT_PORTFOLIO_UPDATE,    self._signal_update.emit)
        unreg(EVENT_PORTFOLIO_RISK,      self._signal_risk.emit)
        unreg(EVENT_PORTFOLIO_REBALANCE, self._signal_rebalance.emit)
        unreg(EVENT_PORTFOLIO_LOG,       self._signal_log.emit)

    # ------------------------------------------------------------------ #
    #  事件回调（Phase 2 填充实现）
    # ------------------------------------------------------------------ #

    def _on_portfolio_update(self, event: Event) -> None:
        """接收 EVENT_PORTFOLIO_UPDATE，刷新 Overview / Allocation / Performance / Rebalance Tab。"""
        data = event.data
        if not isinstance(data, dict):
            return
        allocation  = data.get("allocation")
        performance = data.get("performance")
        rebalance   = data.get("rebalance_history", [])
        if allocation is not None:
            self.allocation_tab.update_allocation(allocation)
        if performance is not None:
            self.overview_tab.update_performance(performance)
            self.performance_tab.update_performance(performance)
        if rebalance:
            self.rebalance_tab.update_rebalance(rebalance)
        self.tab_widget.setCurrentWidget(self.overview_tab)
        # Phase 4: 刷新 report_tab
        self.report_tab.update_all(
            performance=performance,
            allocation=allocation,
            rebalance_history=rebalance,
        )

    def _on_portfolio_risk(self, event: Event) -> None:
        """接收 EVENT_PORTFOLIO_RISK，刷新 RiskTab 和 AttributionTab。"""
        data = event.data
        if not isinstance(data, dict):
            return
        risk        = data.get("risk")
        attribution = data.get("attribution")
        nav_series  = None

        # 从已缓存的 performance 取净值序列
        engine = self.main_engine.get_engine("PortfolioEngine")
        if engine is not None:
            perf = engine.portfolio_state.get_performance()
            if perf is not None and perf.nav_series is not None:
                nav_series = perf.nav_series

        if risk is not None:
            self.risk_tab.update_risk(risk)

        if attribution is not None:
            self.attribution_tab.update_attribution(
                attribution, nav_series=nav_series
            )

        # Phase 4: 同步 risk 到 report_tab
        self.report_tab.update_all(risk=risk, attribution=attribution)

    def _on_portfolio_rebalance(self, event: Event) -> None:
        """接收 EVENT_PORTFOLIO_REBALANCE（Phase 2 已内嵌在 UPDATE 事件中）。"""
        pass

    def _on_portfolio_log(self, event: Event) -> None:
        """接收日志消息；__IDLE__ 恢复按钮状态。"""
        msg = event.data if isinstance(event.data, str) else str(event.data)
        if msg == "__IDLE__":
            self.left_panel.set_idle()
            return
        self.txt_log.append(msg)
        sb = self.txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_run_requested(self, params: dict) -> None:
        """用户点击运行，调用后台引擎。"""
        self._clear_tabs()
        method_val = params.get("weight_method")
        self._write_log(
            f"[运行] portfolio={params.get('portfolio_name')}  "
            f"method={method_val.value if method_val else '?'}  "
            f"slots={len(params.get('slots', []))}  "
            f"{params.get('start')} ~ {params.get('end')}"
        )
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is None:
            self._write_log("错误：PortfolioEngine 未加载，请检查 run.py 中的 add_app 注册。")
            self.left_panel.set_idle()
            return
        engine.run(params)

    def _on_stop_requested(self) -> None:
        """用户点击停止，通知引擎。"""
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is not None:
            engine.stop()
        else:
            self._write_log("停止：引擎未加载。")
            self.left_panel.set_idle()


    # ------------------------------------------------------------------ #
    #  工具
    # ------------------------------------------------------------------ #

    def _clear_tabs(self) -> None:
        """每次新运行前重置所有 Tab。"""
        for tab in (
            self.overview_tab, self.allocation_tab, self.risk_tab,
            self.performance_tab, self.rebalance_tab,
            self.attribution_tab, self.report_tab,
        ):
            tab.clear()
        self.txt_log.clear()

    def _write_log(self, msg: str) -> None:
        self.txt_log.append(msg)

    # ------------------------------------------------------------------ #
    #  生命周期
    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:
        self._unregister_events()
        super().closeEvent(event)
