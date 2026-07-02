"""
alpha_factory_2/ui/widget.py

AlphaFactoryWidget — Alpha Factory 2.0 主窗口（Phase 1 骨架）。

布局：
  左侧（210px）：Alpha 生产控制面板（占位）
  右侧：TabWidget（5 个空 Tab）
    1. Generator（生成）
    2. Scoring（评分）
    3. Screening（筛选）
    4. Lifecycle（生命周期）
    5. Report（报告）
"""

from __future__ import annotations

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import APP_NAME, AlphaStatus
from ..event import (
    EVENT_ALPHA_GENERATED,
    EVENT_ALPHA_SCORED,
    EVENT_ALPHA_SCREENED,
    EVENT_ALPHA_REJECTED,
    EVENT_ALPHA_LIVE,
    EVENT_ALPHA_RETIRED,
)
from .generator_tab  import GeneratorTab
from .scoring_tab    import ScoringTab
from .screening_tab  import ScreeningTab
from .lifecycle_tab  import LifecycleTab
from .report_tab     import ReportTab

_DARK_BG  = "#1e1e2e"
_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"
_MAV      = "#cba6f7"   # mauve — Alpha Factory 主色调

_STATUS_COLOR = {
    AlphaStatus.GENERATED.value: _MUT,
    AlphaStatus.SCORED.value:    _BLU,
    AlphaStatus.SCREENED.value:  _YLW,
    AlphaStatus.LIVE.value:      _GRN,
    AlphaStatus.DEGRADED.value:  _YLW,
    AlphaStatus.RETIRED.value:   _RED,
    AlphaStatus.REJECTED.value:  _RED,
}


class AlphaFactoryWidget(QtWidgets.QMainWindow):
    """Alpha Factory 2.0 主窗口（Phase 1 骨架）。"""

    _signal_generated = QtCore.Signal(Event)
    _signal_scored    = QtCore.Signal(Event)
    _signal_screened  = QtCore.Signal(Event)
    _signal_rejected  = QtCore.Signal(Event)
    _signal_live      = QtCore.Signal(Event)
    _signal_retired   = QtCore.Signal(Event)

    def __init__(
        self,
        main_engine:  MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__()
        self.main_engine  = main_engine
        self.event_engine = event_engine
        self.af_engine    = main_engine.get_engine(APP_NAME)

        self._generator_tab:  GeneratorTab  | None = None
        self._scoring_tab:    ScoringTab    | None = None
        self._screening_tab:  ScreeningTab  | None = None
        self._lifecycle_tab:  LifecycleTab  | None = None
        self._report_tab:     ReportTab     | None = None

        self._af_engine_ref = self.af_engine
        self._init_ui()
        self._register_signals()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        self.setWindowTitle("Alpha Factory 2.0  工业化Alpha生产系统")
        self.setMinimumSize(1280, 760)
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
        panel.setFixedWidth(210)
        panel.setStyleSheet(
            f"background: {_PANEL_BG}; border-radius: 6px;"
            f" border: 1px solid {_BORDER};"
        )
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        title = QtWidgets.QLabel("Alpha Factory 2.0")
        title.setStyleSheet(
            f"color: {_MAV}; font-size: 13px; font-weight: bold; border: none;")
        v.addWidget(title)

        sub = QtWidgets.QLabel("工业化Alpha生产系统")
        sub.setStyleSheet(f"color: {_MUT}; font-size: 10px; border: none;")
        v.addWidget(sub)

        self._sep(v)

        # 状态指示行
        self._lbl_alphas    = self._row(v, "Alpha 总数  Total", "0",    _FG)
        self._lbl_live      = self._row(v, "存活  Live",        "0",    _GRN)
        self._lbl_retired   = self._row(v, "退役  Retired",     "0",    _RED)
        self._lbl_uptime    = self._row(v, "运行时长  Uptime",  "---",  _MUT)

        self._sep(v)

        # 最新事件
        lbl_ev = QtWidgets.QLabel("最近事件  Last Event")
        lbl_ev.setStyleSheet(f"color: {_MUT}; font-size: 10px; border: none;")
        v.addWidget(lbl_ev)
        self._lbl_last_event = QtWidgets.QLabel("---")
        self._lbl_last_event.setStyleSheet(
            f"color: {_MUT}; font-size: 11px; border: none;")
        self._lbl_last_event.setWordWrap(True)
        v.addWidget(self._lbl_last_event)

        v.addStretch()
        self._sep(v)

        # 控制按钮
        for label, color, slot in [
            ("▶ 启动  Start",  _GRN, self._on_start),
            ("■ 停止  Stop",   _RED, self._on_stop),
        ]:
            btn = QtWidgets.QPushButton(label)
            btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {color};"
                f" border: 1px solid {color}; border-radius: 4px;"
                f" padding: 6px 0px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            btn.clicked.connect(slot)
            v.addWidget(btn)

        return panel

    def _build_tab_widget(self) -> QtWidgets.QTabWidget:
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: 1px solid {_BORDER}; border-radius: 4px; }}"
            f"QTabBar::tab {{ background: {_PANEL_BG}; color: {_MUT};"
            f" padding: 6px 18px; border-radius: 3px; }}"
            f"QTabBar::tab:selected {{ background: {_DARK_BG}; color: {_FG}; }}"
        )

        eng = getattr(self.af_engine, "_engine", None)

        self._generator_tab  = GeneratorTab(engine=eng)
        self._scoring_tab    = ScoringTab(engine=eng)
        self._screening_tab  = ScreeningTab(engine=eng)
        self._lifecycle_tab  = LifecycleTab(engine=eng)
        self._report_tab     = ReportTab(engine=eng)

        tabs.addTab(self._generator_tab,  "生成  Generator")
        tabs.addTab(self._scoring_tab,    "评分  Scoring")
        tabs.addTab(self._screening_tab,  "筛选  Screening")
        tabs.addTab(self._lifecycle_tab,  "生命周期  Lifecycle")
        tabs.addTab(self._report_tab,     "报告  Report")

        return tabs

    # ------------------------------------------------------------------ #
    #  信号注册
    # ------------------------------------------------------------------ #

    def _register_signals(self) -> None:
        self._signal_generated.connect(self._on_event_generated)
        self._signal_scored.connect(self._on_event_scored)
        self._signal_screened.connect(self._on_event_screened)
        self._signal_rejected.connect(self._on_event_rejected)
        self._signal_live.connect(self._on_event_live)
        self._signal_retired.connect(self._on_event_retired)

        reg = self.event_engine.register
        reg(EVENT_ALPHA_GENERATED, self._signal_generated.emit)
        reg(EVENT_ALPHA_SCORED,    self._signal_scored.emit)
        reg(EVENT_ALPHA_SCREENED,  self._signal_screened.emit)
        reg(EVENT_ALPHA_REJECTED,  self._signal_rejected.emit)
        reg(EVENT_ALPHA_LIVE,      self._signal_live.emit)
        reg(EVENT_ALPHA_RETIRED,   self._signal_retired.emit)

    def closeEvent(self, event) -> None:
        unreg = self.event_engine.unregister
        unreg(EVENT_ALPHA_GENERATED, self._signal_generated.emit)
        unreg(EVENT_ALPHA_SCORED,    self._signal_scored.emit)
        unreg(EVENT_ALPHA_SCREENED,  self._signal_screened.emit)
        unreg(EVENT_ALPHA_REJECTED,  self._signal_rejected.emit)
        unreg(EVENT_ALPHA_LIVE,      self._signal_live.emit)
        unreg(EVENT_ALPHA_RETIRED,   self._signal_retired.emit)
        super().closeEvent(event)

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_start(self) -> None:
        if self.af_engine:
            self.af_engine.init()
            self.af_engine.start()
            self._wire_tabs()
            self._lbl_last_event.setText("系统已启动")
            self._lbl_last_event.setStyleSheet(
                f"color: {_GRN}; font-size: 11px; border: none;")

    def _on_stop(self) -> None:
        if self.af_engine:
            self.af_engine.stop()
            self._lbl_last_event.setText("系统已停止")
            self._lbl_last_event.setStyleSheet(
                f"color: {_RED}; font-size: 11px; border: none;")

    # ------------------------------------------------------------------ #
    #  事件回调
    # ------------------------------------------------------------------ #

    def _on_event_generated(self, event: Event) -> None:
        self._update_last_event("GENERATED", event.data, _MUT)
        self._refresh_counts()

    def _on_event_scored(self, event: Event) -> None:
        self._update_last_event("SCORED", event.data, _BLU)
        self._refresh_counts()

    def _on_event_screened(self, event: Event) -> None:
        self._update_last_event("SCREENED", event.data, _YLW)
        self._refresh_counts()

    def _on_event_rejected(self, event: Event) -> None:
        self._update_last_event("REJECTED", event.data, _RED)
        self._refresh_counts()

    def _on_event_live(self, event: Event) -> None:
        self._update_last_event("LIVE", event.data, _GRN)
        self._refresh_counts()

    def _on_event_retired(self, event: Event) -> None:
        self._update_last_event("RETIRED", event.data, _RED)
        self._refresh_counts()

    # ------------------------------------------------------------------ #
    #  内部工具
    # ------------------------------------------------------------------ #

    def _wire_tabs(self) -> None:
        eng = getattr(self.af_engine, "_engine", None)
        if eng is None:
            return
        for tab in (self._generator_tab, self._scoring_tab,
                    self._screening_tab, self._lifecycle_tab,
                    self._report_tab):
            if tab is not None:
                tab.set_engine(eng)

    def _refresh_counts(self) -> None:
        eng = getattr(self.af_engine, "_engine", None)
        if eng is None:
            return
        summ = eng.get_summary()
        self._lbl_alphas.setText(str(summ.get("alphas", 0)))
        lc = summ.get("lifecycle", {}).get("by_status", {})
        self._lbl_live.setText(str(lc.get(AlphaStatus.LIVE.value, 0)))
        self._lbl_retired.setText(str(lc.get(AlphaStatus.RETIRED.value, 0)))
        self._lbl_uptime.setText(f"{summ.get('uptime', 0):.0f}s")

    def _update_last_event(self, label: str, data: dict, color: str) -> None:
        alpha_id = data.get("alpha_id", "")
        text = f"[{label}] {alpha_id}" if alpha_id else f"[{label}]"
        self._lbl_last_event.setText(text)
        self._lbl_last_event.setStyleSheet(
            f"color: {color}; font-size: 11px; border: none;")

    def _sep(self, layout) -> None:
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(
            f"border: none; border-top: 1px solid {_BORDER};")
        layout.addWidget(sep)

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
