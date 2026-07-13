"""
global_portfolio_intelligence/ui/widget.py

GlobalPortfolioWidget — 全局组合智能系统主窗口（Phase 1 骨架）。

布局：
  左侧（固定宽度）— 全局状态面板（占位）
  右侧            — TabWidget（6个空 Tab）

Phase 1：全部为空占位，无任何功能逻辑。
"""
from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets, QtGui
from vnpy.trader.engine import MainEngine, EventEngine

from ..event import APP_NAME

_BG     = "#1e1e2e"
_DARK   = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_BLUE   = "#89b4fa"
_GRN    = "#a6e3a1"
_MAV    = "#cba6f7"
_HEAD   = "#313244"


class GlobalPortfolioWidget(QtWidgets.QMainWindow):
    """
    全局组合智能系统主窗口（Phase 1）。

    左侧：全局状态面板（系统状态 / 运行时间 / 关键指标）
    右侧：6-Tab 布局
      0. Dashboard  — 全局总览
      1. Objective  — 目标函数监控
      2. Allocation — 资金分配可视化
      3. Performance— 系统绩效热力图
      4. Rebalance  — 再平衡时间轴
      5. Logs       — 系统日志流
    """

    widget_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = main_engine.get_engine(APP_NAME)
        self._init_ui()
        self._init_menu()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        self.setWindowTitle("Global Portfolio Intelligence 全局组合智能系统")
        self.resize(1400, 800)
        self.setStyleSheet(f"background:{_BG}; color:{_FG};")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        layout = QtWidgets.QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 左侧状态面板
        layout.addWidget(self._build_status_panel(), stretch=0)

        # 右侧 Tab 区域
        layout.addWidget(self._build_tab_widget(), stretch=1)

    def _build_status_panel(self) -> QtWidgets.QWidget:
        """左侧全局状态面板（Phase 1 占位）。"""
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(220)
        panel.setStyleSheet(
            f"background:{_DARK}; border-radius:6px;"
            f" border:1px solid {_BORDER};")

        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(12, 14, 12, 14)
        vb.setSpacing(12)

        # 标题
        title = QtWidgets.QLabel("全局状态")
        title.setStyleSheet(
            f"color:{_MAV}; font-weight:bold; font-size:13px; border:none;")
        vb.addWidget(title)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(
            f"border:none; border-top:1px solid {_BORDER}; background:transparent;")
        vb.addWidget(sep)

        # 状态指标占位
        self._status_labels: dict[str, QtWidgets.QLabel] = {}
        for key, label in [
            ("status",    "系统状态"),
            ("phase",     "当前阶段"),
            ("uptime",    "运行时间"),
            ("objective", "目标函数"),
            ("allocation","资金分配"),
            ("regime",    "市场状态"),
        ]:
            row = QtWidgets.QWidget()
            row.setStyleSheet("background:transparent; border:none;")
            rh = QtWidgets.QHBoxLayout(row)
            rh.setContentsMargins(0, 0, 0, 0)

            lk = QtWidgets.QLabel(label)
            lk.setStyleSheet(
                f"color:{_MUT}; font-size:10px; border:none;"
                f" background:transparent;")
            lk.setFixedWidth(70)

            lv = QtWidgets.QLabel("--")
            lv.setStyleSheet(
                f"color:{_FG}; font-size:11px; font-weight:bold;"
                f" border:none; background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

            rh.addWidget(lk)
            rh.addStretch()
            rh.addWidget(lv)
            self._status_labels[key] = lv
            vb.addWidget(row)

        vb.addStretch()

        # 操作按钮
        btn_start = QtWidgets.QPushButton("▶  启动引擎")
        btn_start.setStyleSheet(
            f"QPushButton {{background:{_BLUE}; color:#1e1e2e;"
            f" font-weight:bold; border:none; border-radius:4px;"
            f" padding:8px; font-size:11px;}}"
            f"QPushButton:hover {{background:#74c7ec;}}")
        btn_start.clicked.connect(self._on_start)
        vb.addWidget(btn_start)

        btn_refresh = QtWidgets.QPushButton("刷新状态")
        btn_refresh.setStyleSheet(
            f"QPushButton {{background:transparent; color:{_MUT};"
            f" border:1px solid {_BORDER}; border-radius:4px;"
            f" padding:6px; font-size:11px;}}"
            f"QPushButton:hover {{background:{_HEAD};}}")
        btn_refresh.clicked.connect(self._on_refresh)
        vb.addWidget(btn_refresh)

        return panel

    def _build_tab_widget(self) -> QtWidgets.QTabWidget:
        """右侧 6-Tab 布局（Phase 1 全部为空占位）。"""
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane {{background:{_DARK}; border:1px solid {_BORDER};"
            f" border-radius:4px;}}"
            f"QTabBar::tab {{background:{_HEAD}; color:{_MUT};"
            f" padding:8px 16px; font-size:11px; border:none;"
            f" border-bottom:2px solid transparent; margin-right:2px;}}"
            f"QTabBar::tab:selected {{color:{_FG};"
            f" border-bottom:2px solid {_BLUE};}}"
            f"QTabBar::tab:hover {{color:{_FG}; background:{_BORDER};}}")

        tab_defs = [
            ("Dashboard",    "全局总览",     _BLUE),
            ("Objective",    "目标函数",     _MAV),
            ("Allocation",   "资金分配",     _GRN),
            ("Performance",  "系统绩效",     "#f9e2af"),
            ("Rebalance",    "再平衡",       "#f38ba8"),
            ("Logs",         "系统日志",     _MUT),
        ]

        for eng_name, cn_name, color in tab_defs:
            placeholder = self._build_placeholder(eng_name, cn_name, color)
            tabs.addTab(placeholder, f"{eng_name}  {cn_name}")

        self._tabs = tabs
        return tabs

    def _build_placeholder(
        self, name: str, cn: str, color: str
    ) -> QtWidgets.QWidget:
        """Phase 1 Tab 占位页面。"""
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_DARK};")

        vb = QtWidgets.QVBoxLayout(w)
        vb.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QtWidgets.QLabel("◈")
        icon_lbl.setStyleSheet(
            f"color:{color}; font-size:48px; border:none; background:transparent;")
        icon_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        name_lbl = QtWidgets.QLabel(f"{name}")
        name_lbl.setStyleSheet(
            f"color:{color}; font-size:20px; font-weight:bold;"
            f" border:none; background:transparent;")
        name_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        cn_lbl = QtWidgets.QLabel(cn)
        cn_lbl.setStyleSheet(
            f"color:{_MUT}; font-size:13px; border:none; background:transparent;")
        cn_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        phase_lbl = QtWidgets.QLabel("Phase 1  —  占位中，待后续阶段实现")
        phase_lbl.setStyleSheet(
            f"color:{_MUT}; font-size:10px; border:1px solid {_BORDER};"
            f" border-radius:3px; padding:6px 16px; background:{_HEAD};")
        phase_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        vb.addStretch()
        vb.addWidget(icon_lbl)
        vb.addWidget(name_lbl)
        vb.addWidget(cn_lbl)
        vb.addSpacing(20)
        vb.addWidget(phase_lbl)
        vb.addStretch()

        return w

    # ------------------------------------------------------------------ #
    #  菜单
    # ------------------------------------------------------------------ #

    def _init_menu(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet(
            f"QMenuBar {{background:{_DARK}; color:{_FG}; border:none;}}"
            f"QMenuBar::item:selected {{background:{_HEAD};}}"
            f"QMenu {{background:{_DARK}; color:{_FG};"
            f" border:1px solid {_BORDER};}}"
            f"QMenu::item:selected {{background:{_HEAD};}}")

        sys_menu = menu_bar.addMenu("系统")
        act_start = sys_menu.addAction("启动引擎")
        act_start.triggered.connect(self._on_start)
        act_stop = sys_menu.addAction("停止引擎")
        act_stop.triggered.connect(self._on_stop)
        sys_menu.addSeparator()
        act_close = sys_menu.addAction("关闭窗口")
        act_close.triggered.connect(self.close)

    # ------------------------------------------------------------------ #
    #  Slots
    # ------------------------------------------------------------------ #

    def _on_start(self) -> None:
        if self._engine:
            self._engine.init()
            self._engine.start()
            self._on_refresh()

    def _on_stop(self) -> None:
        if self._engine:
            self._engine.stop()
            self._on_refresh()

    def _on_refresh(self) -> None:
        if self._engine is None:
            return
        state = self._engine.compute_global_state()
        self._status_labels["status"].setText(
            state.get("status", "--"))
        self._status_labels["phase"].setText(
            f"Phase {state.get('phase', 1)}")
        uptime = state.get("uptime", 0.0)
        self._status_labels["uptime"].setText(
            f"{uptime:.0f}s")
        self._status_labels["objective"].setText("--")
        self._status_labels["allocation"].setText("--")
        self._status_labels["regime"].setText("--")
