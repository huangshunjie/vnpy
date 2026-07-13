"""
capital_allocation_ai/ui/widget.py

CapitalAllocationWidget — 资本分配系统主窗口（Phase 1 骨架）。

布局：
  左侧（240px）：Alpha 排名预览面板（占位）
  右侧：6 Tab（Dashboard / Alpha Ranking / Allocation /
               Risk Budget / Rebalance / Logs）
"""

from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets

from .dashboard_tab   import DashboardTab
from .alpha_rank_tab  import AlphaRankTab
from .allocation_tab  import AllocationTab
from .risk_budget_tab import RiskBudgetTab
from .rebalance_tab   import RebalanceTab
from .log_tab         import LogTab

_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_MAV      = "#cba6f7"
_GRN      = "#a6e3a1"

APP_TITLE = "Capital Allocation Intelligence System  v1.0"


class CapitalAllocationWidget(QtWidgets.QMainWindow):
    """
    Capital Allocation Intelligence System 主窗口（Phase 1）。

    Phase 1: 骨架，全部 Tab 为占位内容。
    Phase 2+: 逐 Tab 接入真实数据。
    """

    def __init__(self, main_engine, event_engine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = None   # CapitalAllocationEngine（Phase 1: 初始化后赋值）
        self._init_engine()
        self._init_ui()

    # ------------------------------------------------------------------ #
    #  Engine 初始化
    # ------------------------------------------------------------------ #

    def _init_engine(self) -> None:
        """从 MainEngine 获取 CapitalAllocationEngine 实例。"""
        from ..constant import APP_NAME
        engine = self._main_engine.get_engine(APP_NAME)
        if engine is not None:
            self._engine = engine
            self._engine.init()
            self._engine.start()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        self.setWindowTitle(APP_TITLE)
        self.resize(1400, 820)
        self.setStyleSheet(f"background: #1e1e2e; color: {_FG};")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        root.addWidget(self._build_left_panel(), stretch=0)
        root.addWidget(self._build_tab_area(),   stretch=1)

        self._build_status_bar()

    def _build_left_panel(self) -> QtWidgets.QWidget:
        """左侧 Alpha 排名预览面板（Phase 1 占位）。"""
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(240)
        panel.setStyleSheet(
            f"background: {_PANEL_BG}; border-radius: 6px;"
            f" border: 1px solid {_BORDER};"
        )
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        # 标题
        t = QtWidgets.QLabel("Alpha Rankings")
        t.setStyleSheet(
            f"color: {_MAV}; font-size: 12px; font-weight: bold; border: none;")
        v.addWidget(t)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(f"border: none; border-top: 1px solid {_BORDER};")
        v.addWidget(sep)

        # 占位说明
        ph = QtWidgets.QLabel(
            "Phase 2 将显示：\n\n"
            "• Alpha 评分排行\n"
            "• 资金分配比例\n"
            "• 流动方向指示器\n"
            "• 风险预算状态"
        )
        ph.setStyleSheet(f"color: {_MUT}; font-size: 11px; border: none;")
        ph.setWordWrap(True)
        v.addWidget(ph)
        v.addStretch()

        # 刷新按钮
        btn = QtWidgets.QPushButton("刷新  Refresh")
        btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {_MUT};"
            f" border: 1px solid {_BORDER}; border-radius: 3px;"
            f" padding: 4px 0px; font-size: 11px; }}"
            f"QPushButton:hover {{ color: {_MAV}; border-color: {_MAV}; }}"
        )
        btn.clicked.connect(self._on_refresh)
        v.addWidget(btn)
        return panel

    def _build_tab_area(self) -> QtWidgets.QTabWidget:
        """右侧 6 Tab 区域。"""
        self._tabs = QtWidgets.QTabWidget()
        self._tabs.setStyleSheet(
            f"QTabBar::tab {{ background: {_PANEL_BG}; color: {_MUT};"
            f" padding: 6px 16px; border: 1px solid {_BORDER}; "
            f" border-bottom: none; border-radius: 4px 4px 0 0; }}"
            f"QTabBar::tab:selected {{ color: {_MAV}; "
            f" border-color: {_MAV}; background: #1e1e2e; }}"
            f"QTabWidget::pane {{ border: 1px solid {_BORDER}; "
            f" border-radius: 0 4px 4px 4px; background: #1e1e2e; }}"
        )

        self._tab_dashboard  = DashboardTab(self._engine)
        self._tab_alpha_rank = AlphaRankTab(self._engine)
        self._tab_allocation = AllocationTab(self._engine)
        self._tab_risk       = RiskBudgetTab(self._engine)
        self._tab_rebalance  = RebalanceTab(self._engine)
        self._tab_log        = LogTab(self._engine)

        self._tabs.addTab(self._tab_dashboard,  "Dashboard")
        self._tabs.addTab(self._tab_alpha_rank, "Alpha Ranking")
        self._tabs.addTab(self._tab_allocation, "Allocation")
        self._tabs.addTab(self._tab_risk,       "Risk Budget")
        self._tabs.addTab(self._tab_rebalance,  "Rebalance")
        self._tabs.addTab(self._tab_log,        "Logs")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        return self._tabs

    def _build_status_bar(self) -> None:
        """底部状态栏。"""
        sb = self.statusBar()
        sb.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        self._status_lbl = QtWidgets.QLabel(
            f"Capital Allocation AI  |  Phase 1  |  Engine: "
            + ("Running" if self._engine else "Not Found")
        )
        sb.addWidget(self._status_lbl)

    # ------------------------------------------------------------------ #
    #  回调
    # ------------------------------------------------------------------ #

    def _on_refresh(self) -> None:
        current = self._tabs.currentWidget()
        if hasattr(current, 'refresh'):
            current.refresh()

    def _on_tab_changed(self, index: int) -> None:
        tab = self._tabs.widget(index)
        if hasattr(tab, 'refresh'):
            tab.refresh()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._engine:
            self._engine.stop()
        super().closeEvent(event)
