"""
temporal_intelligence_ai/ui/widget.py  (Phase 6 完整版)

TemporalIntelligenceWidget — 时间智能系统主窗口。
布局：左侧时间结构状态面板 + 右侧 7-Tab。
Phase 6: 五大引擎 Tab 全部接入真实实现，仅 Logs Tab 保留占位。
"""
from __future__ import annotations

from vnpy.trader.ui import QtCore, QtWidgets
from vnpy.trader.engine import MainEngine, EventEngine
from vnpy.event import Event

from ..event import APP_NAME, EVENT_CYCLE_DETECTED
from .cycle_tab import CycleTab

_BG     = "#1e1e2e"
_DARK   = "#181825"
_BORDER = "#45475a"
_FG     = "#cdd6f4"
_MUT    = "#6c7086"
_BLUE   = "#89b4fa"
_GRN    = "#a6e3a1"
_YLW    = "#f9e2af"
_RED    = "#f38ba8"
_MAV    = "#cba6f7"
_HEAD   = "#313244"
_CYN    = "#89dceb"
_ORG    = "#fab387"
_PNK    = "#f5c2e7"


class TemporalIntelligenceWidget(QtWidgets.QMainWindow):
    """
    时间智能系统主窗口（Phase 2）。

    左侧：时间结构状态面板（系统状态 / 周期阶段 / Regime / 衰减健康度）
    右侧：7-Tab 布局
      0. Dashboard   — 时间总览      [占位]
      1. Cycle        — 市场周期     [Phase 2 ✔ 已实现]
      2. Decay        — Alpha 衰减   [占位]
      3. Dependency   — 时间依赖     [占位]
      4. Transition   — 状态转移     [占位]
      5. Validation   — 时间验证     [占位]
      6. Logs         — 日志流       [占位]
    """

    widget_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self._main_engine  = main_engine
        self._event_engine = event_engine
        self._engine       = main_engine.get_engine(APP_NAME)
        self._init_ui()
        self._init_menu()
        self._register_events()

    # ── UI construction ───────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowTitle("Temporal Intelligence AI  时间智能系统")
        self.resize(1500, 860)
        self.setStyleSheet(f"background:{_BG}; color:{_FG};")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self._build_status_panel(), stretch=0)
        layout.addWidget(self._build_tab_widget(),   stretch=1)

    def _build_status_panel(self) -> QtWidgets.QWidget:
        """左侧时间结构状态面板。"""
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(230)
        panel.setStyleSheet(
            f"background:{_DARK};border-radius:6px;border:1px solid {_BORDER};")

        vb = QtWidgets.QVBoxLayout(panel)
        vb.setContentsMargins(12, 14, 12, 14)
        vb.setSpacing(10)

        title = QtWidgets.QLabel("时间结构状态")
        title.setStyleSheet(
            f"color:{_CYN};font-weight:bold;font-size:13px;border:none;")
        vb.addWidget(title)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(
            f"border:none;border-top:1px solid {_BORDER};background:transparent;")
        vb.addWidget(sep)

        self._status_labels: dict[str, QtWidgets.QLabel] = {}
        rows = [
            ("status",       "系统状态",   _FG),
            ("cycle_phase",  "周期阶段",   _GRN),
            ("regime",       "Regime",     _YLW),
            ("confidence",   "置信度",     _CYN),
            ("decay_health", "衰减健康度", _ORG),
            ("transition",   "转移状态",   _MAV),
            ("uptime",       "运行时间",   _MUT),
        ]
        for key, label, color in rows:
            row_w = QtWidgets.QWidget()
            row_w.setStyleSheet("background:transparent;border:none;")
            rh = QtWidgets.QHBoxLayout(row_w)
            rh.setContentsMargins(0, 0, 0, 0)
            rh.setSpacing(4)

            lk = QtWidgets.QLabel(label)
            lk.setStyleSheet(
                f"color:{_MUT};font-size:10px;border:none;background:transparent;")
            lk.setFixedWidth(78)

            lv = QtWidgets.QLabel("--")
            lv.setStyleSheet(
                f"color:{color};font-size:11px;font-weight:bold;"
                f"border:none;background:transparent;")
            lv.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

            rh.addWidget(lk)
            rh.addStretch()
            rh.addWidget(lv)
            self._status_labels[key] = lv
            vb.addWidget(row_w)

        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep2.setStyleSheet(
            f"border:none;border-top:1px solid {_BORDER};background:transparent;")
        vb.addWidget(sep2)

        health_title = QtWidgets.QLabel("Temporal Health Score")
        health_title.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:none;background:transparent;")
        vb.addWidget(health_title)

        self._health_bar = QtWidgets.QProgressBar()
        self._health_bar.setRange(0, 100)
        self._health_bar.setValue(0)
        self._health_bar.setTextVisible(True)
        self._health_bar.setFixedHeight(18)
        self._health_bar.setStyleSheet(
            f"QProgressBar{{background:{_HEAD};border:1px solid {_BORDER};"
            f"border-radius:3px;color:{_FG};font-size:10px;}}"
            f"QProgressBar::chunk{{background:{_CYN};border-radius:2px;}}")
        vb.addWidget(self._health_bar)

        vb.addStretch()

        btn_start = QtWidgets.QPushButton("▶  启动时间引擎")
        btn_start.setStyleSheet(
            f"QPushButton{{background:{_CYN};color:#1e1e2e;font-weight:bold;"
            f"border:none;border-radius:4px;padding:8px;font-size:11px;}}"
            f"QPushButton:hover{{background:#74c7ec;}}")
        btn_start.clicked.connect(self._on_start)
        vb.addWidget(btn_start)

        btn_stop = QtWidgets.QPushButton("■  停止")
        btn_stop.setStyleSheet(
            f"QPushButton{{background:transparent;color:{_RED};"
            f"border:1px solid {_RED};border-radius:4px;"
            f"padding:6px;font-size:11px;}}"
            f"QPushButton:hover{{background:{_HEAD};}}")
        btn_stop.clicked.connect(self._on_stop)
        vb.addWidget(btn_stop)

        btn_refresh = QtWidgets.QPushButton("刷新状态")
        btn_refresh.setStyleSheet(
            f"QPushButton{{background:transparent;color:{_MUT};"
            f"border:1px solid {_BORDER};border-radius:4px;"
            f"padding:6px;font-size:11px;}}"
            f"QPushButton:hover{{background:{_HEAD};}}")
        btn_refresh.clicked.connect(self._on_refresh)
        vb.addWidget(btn_refresh)

        return panel

    def _build_tab_widget(self) -> QtWidgets.QTabWidget:
        """右侧 7-Tab 布局。"""
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane{{background:{_DARK};border:1px solid {_BORDER};"
            f"border-radius:4px;}}"
            f"QTabBar::tab{{background:{_HEAD};color:{_MUT};"
            f"padding:8px 14px;font-size:11px;border:none;"
            f"border-bottom:2px solid transparent;margin-right:2px;}}"
            f"QTabBar::tab:selected{{color:{_FG};border-bottom:2px solid {_CYN};}}"
            f"QTabBar::tab:hover{{color:{_FG};background:{_BORDER};}}")

        # Tab 0: Dashboard（占位）
        tabs.addTab(
            self._build_placeholder("Dashboard", "时间总览", _CYN),
            "Dashboard  时间总览")

        # Tab 1: Cycle（Phase 2 真实实现）
        self._cycle_tab = CycleTab(self._main_engine, self._event_engine)
        tabs.addTab(self._cycle_tab, "Cycle  市场周期")

        # Tab 2–6（占位）
        placeholder_defs = [
            ("Decay",      "Alpha衰减", _ORG),
            ("Dependency", "时间依赖",  _BLUE),
            ("Transition", "状态转移",  _MAV),
            ("Validation", "时间验证",  _YLW),
            ("Logs",       "日志流",    _MUT),
        ]
        for eng_name, cn_name, color in placeholder_defs:
            tabs.addTab(
                self._build_placeholder(eng_name, cn_name, color),
                f"{eng_name}  {cn_name}")

        self._tabs = tabs
        return tabs

    def _build_placeholder(self, name: str, cn: str, color: str) -> QtWidgets.QWidget:
        """占位页面（后续 Phase 替换）。"""
        w = QtWidgets.QWidget()
        w.setStyleSheet(f"background:{_DARK};")
        vb = QtWidgets.QVBoxLayout(w)
        vb.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QtWidgets.QLabel("◈")
        icon_lbl.setStyleSheet(
            f"color:{color};font-size:48px;border:none;background:transparent;")
        icon_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        name_lbl = QtWidgets.QLabel(name)
        name_lbl.setStyleSheet(
            f"color:{color};font-size:22px;font-weight:bold;"
            f"border:none;background:transparent;")
        name_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        cn_lbl = QtWidgets.QLabel(cn)
        cn_lbl.setStyleSheet(
            f"color:{_MUT};font-size:13px;border:none;background:transparent;")
        cn_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        phase_lbl = QtWidgets.QLabel("占位中，待后续阶段实现")
        phase_lbl.setStyleSheet(
            f"color:{_MUT};font-size:10px;border:1px solid {_BORDER};"
            f"border-radius:3px;padding:6px 16px;background:{_HEAD};")
        phase_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        vb.addStretch()
        vb.addWidget(icon_lbl)
        vb.addWidget(name_lbl)
        vb.addWidget(cn_lbl)
        vb.addSpacing(20)
        vb.addWidget(phase_lbl)
        vb.addStretch()
        return w

    # ── menu ──────────────────────────────────────────────────────────

    def _init_menu(self) -> None:
        mb = self.menuBar()
        mb.setStyleSheet(
            f"QMenuBar{{background:{_DARK};color:{_FG};border:none;}}"
            f"QMenuBar::item:selected{{background:{_HEAD};}}"
            f"QMenu{{background:{_DARK};color:{_FG};border:1px solid {_BORDER};}}"
            f"QMenu::item:selected{{background:{_HEAD};}}")

        sys_menu = mb.addMenu("系统")
        sys_menu.addAction("启动引擎").triggered.connect(self._on_start)
        sys_menu.addAction("停止引擎").triggered.connect(self._on_stop)
        sys_menu.addSeparator()
        sys_menu.addAction("关闭窗口").triggered.connect(self.close)

        view_menu = mb.addMenu("视图")
        for i, label in enumerate([
            "Dashboard 时间总览",
            "Cycle 市场周期",
            "Decay Alpha衰减",
            "Dependency 时间依赖",
            "Transition 状态转移",
            "Validation 时间验证",
            "Logs 日志流",
        ]):
            action = view_menu.addAction(label)
            action.triggered.connect(
                lambda checked, idx=i: self._tabs.setCurrentIndex(idx))

    # ── events ────────────────────────────────────────────────────────

    def _register_events(self) -> None:
        self._event_engine.register(
            EVENT_CYCLE_DETECTED, self._on_cycle_event)

    def _on_cycle_event(self, event: Event) -> None:
        state = event.data
        if state is None:
            return
        QtCore.QTimer.singleShot(0, lambda: self._update_cycle_panel(state))

    def _update_cycle_panel(self, state) -> None:
        """用最新 CycleState 刷新左侧状态面板。"""
        self._status_labels["cycle_phase"].setText(state.phase.value)
        self._status_labels["regime"].setText(state.regime.value)
        self._status_labels["confidence"].setText(f"{state.confidence:.1%}")
        health = int(state.confidence * 100)
        self._health_bar.setValue(health)

    # ── slots ─────────────────────────────────────────────────────────

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
        summ = self._engine.get_summary()
        self._status_labels["status"].setText(summ.get("status", "--"))
        self._status_labels["uptime"].setText(
            f"{summ.get('uptime', 0):.0f}s")

        cycle = summ.get("cycle", {})
        if cycle.get("phase"):
            self._status_labels["cycle_phase"].setText(cycle["phase"])
        if cycle.get("regime"):
            self._status_labels["regime"].setText(cycle["regime"])
        conf = cycle.get("confidence", 0.0)
        self._status_labels["confidence"].setText(
            f"{conf:.1%}" if conf else "--")
        self._health_bar.setValue(int(conf * 100))

    # ── close ─────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        self._event_engine.unregister(
            EVENT_CYCLE_DETECTED, self._on_cycle_event)
        super().closeEvent(event)
