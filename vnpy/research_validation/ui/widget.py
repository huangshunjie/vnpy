"""
research_validation/ui/widget.py

ValidationWidget — Research Validation System 主窗口（Phase 1 骨架）。

布局：
  左侧（240px）：参数配置面板（占位）
  右侧：TabWidget（7 个 Tab，全部为空占位）
"""

from __future__ import annotations

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtCore, QtWidgets

from ..constant import APP_NAME
from ..event import (
    EVENT_VALIDATION_START,
    EVENT_VALIDATION_PROGRESS,
    EVENT_VALIDATION_RESULT,
    EVENT_VALIDATION_ERROR,
    EVENT_VALIDATION_LOG,
)
from .overview_tab    import OverviewTab
from .walkforward_tab import WalkForwardTab
from .oos_tab         import OOSTab
from .regime_tab      import RegimeTab
from .stability_tab   import StabilityTab
from .bias_tab        import BiasTab
from .report_tab      import ReportTab

_DARK_BG  = "#1e1e2e"
_PANEL_BG = "#181825"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_MUT      = "#6c7086"
_GRN      = "#a6e3a1"
_YLW      = "#f9e2af"
_RED      = "#f38ba8"
_BLU      = "#89b4fa"


class ValidationWidget(QtWidgets.QMainWindow):
    """Research Validation System 主窗口（Phase 1 骨架）。"""

    _signal_log      = QtCore.Signal(Event)
    _signal_progress = QtCore.Signal(Event)
    _signal_result   = QtCore.Signal(Event)
    _signal_error    = QtCore.Signal(Event)

    def __init__(
        self,
        main_engine:  MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__()
        self.main_engine  = main_engine
        self.event_engine = event_engine
        self._init_ui()
        self._register_events()

    # ------------------------------------------------------------------ #
    #  UI 构建
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        self.setWindowTitle("研究验证体系 2.0  —  Alpha 真实性过滤器")
        self.setMinimumSize(1200, 720)
        self.setStyleSheet(f"background: {_DARK_BG}; color: {_FG};")
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QHBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(self._build_left_panel(), stretch=0)
        root.addWidget(self._build_right_panel(), stretch=1)

    def _build_left_panel(self):
        panel = QtWidgets.QWidget()
        panel.setFixedWidth(240)
        panel.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 6px;")
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(8)

        title = QtWidgets.QLabel("验证参数配置")
        title.setStyleSheet(f"color: {_FG}; font-size: 13px; font-weight: bold;")
        v.addWidget(title)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {_BORDER};")
        v.addWidget(sep)

        v.addWidget(self._lbl("因子名称："))
        self._cmb_factor = QtWidgets.QComboBox()
        self._cmb_factor.addItem("—（Phase 2 对接 Factor Engine）")
        self._cmb_factor.setStyleSheet(self._combo_style())
        v.addWidget(self._cmb_factor)

        v.addWidget(self._lbl("开始日期："))
        self._dte_start = QtWidgets.QDateEdit()
        self._dte_start.setCalendarPopup(True)
        self._dte_start.setStyleSheet(self._input_style())
        v.addWidget(self._dte_start)

        v.addWidget(self._lbl("结束日期："))
        self._dte_end = QtWidgets.QDateEdit()
        self._dte_end.setCalendarPopup(True)
        self._dte_end.setStyleSheet(self._input_style())
        v.addWidget(self._dte_end)

        sep2 = QtWidgets.QFrame()
        sep2.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {_BORDER};")
        v.addWidget(sep2)

        v.addWidget(self._lbl("Walk Forward 参数："))
        self._spn_train = QtWidgets.QSpinBox()
        self._spn_train.setRange(20, 2000)
        self._spn_train.setValue(252)
        self._spn_train.setSuffix(" 期（训练）")
        self._spn_train.setStyleSheet(self._spin_style())
        v.addWidget(self._spn_train)

        self._spn_test = QtWidgets.QSpinBox()
        self._spn_test.setRange(5, 500)
        self._spn_test.setValue(63)
        self._spn_test.setSuffix(" 期（测试）")
        self._spn_test.setStyleSheet(self._spin_style())
        v.addWidget(self._spn_test)

        self._spn_step = QtWidgets.QSpinBox()
        self._spn_step.setRange(1, 252)
        self._spn_step.setValue(21)
        self._spn_step.setSuffix(" 期（步长）")
        self._spn_step.setStyleSheet(self._spin_style())
        v.addWidget(self._spn_step)

        v.addWidget(self._lbl("OOS 样本外比例："))
        self._spn_oos = QtWidgets.QDoubleSpinBox()
        self._spn_oos.setRange(0.1, 0.5)
        self._spn_oos.setValue(0.3)
        self._spn_oos.setDecimals(2)
        self._spn_oos.setSingleStep(0.05)
        self._spn_oos.setStyleSheet(self._spin_style())
        v.addWidget(self._spn_oos)

        sep3 = QtWidgets.QFrame()
        sep3.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        sep3.setStyleSheet(f"color: {_BORDER};")
        v.addWidget(sep3)

        v.addWidget(self._lbl("启用验证模块："))
        self._chk_wf  = self._checkbox("Walk Forward")
        self._chk_oos = self._checkbox("OOS Testing")
        self._chk_reg = self._checkbox("Regime Detection")
        self._chk_sta = self._checkbox("Stability Test")
        self._chk_bia = self._checkbox("Bias Detection")
        for chk in (self._chk_wf, self._chk_oos,
                    self._chk_reg, self._chk_sta, self._chk_bia):
            v.addWidget(chk)

        v.addStretch()

        self._btn_run = QtWidgets.QPushButton("▶  开始验证")
        self._btn_run.setStyleSheet(
            f"QPushButton {{ background: {_BLU}; color: #1e1e2e;"
            f" border-radius: 4px; padding: 7px; font-size: 12px;"
            f" font-weight: bold; }}"
            f"QPushButton:hover {{ background: #b4befe; }}"
            f"QPushButton:disabled {{ background: {_MUT}; }}"
        )
        self._btn_run.clicked.connect(self._on_run_clicked)
        v.addWidget(self._btn_run)

        self._btn_stop = QtWidgets.QPushButton("■  停止")
        self._btn_stop.setEnabled(False)
        self._btn_stop.setStyleSheet(
            f"QPushButton {{ background: {_RED}; color: #1e1e2e;"
            f" border-radius: 4px; padding: 7px; font-size: 12px;"
            f" font-weight: bold; }}"
            f"QPushButton:hover {{ background: #eba0ac; }}"
            f"QPushButton:disabled {{ background: {_MUT}; }}"
        )
        self._btn_stop.clicked.connect(self._on_stop_clicked)
        v.addWidget(self._btn_stop)

        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        self._progress.setStyleSheet(
            f"QProgressBar {{ background: #313244; border-radius: 3px;"
            f" color: {_FG}; font-size: 11px; }}"
            f"QProgressBar::chunk {{ background: {_BLU}; border-radius: 3px; }}"
        )
        v.addWidget(self._progress)

        self._lbl_status_val = QtWidgets.QLabel("● 待机")
        self._lbl_status_val.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        v.addWidget(self._lbl_status_val)
        return panel

    def _build_right_panel(self):
        panel = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        v.addWidget(self._build_tabs(), stretch=1)
        v.addWidget(self._build_log_bar())
        return panel

    def _build_tabs(self):
        tabs = QtWidgets.QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: 1px solid {_BORDER}; border-radius: 4px; }}"
            f"QTabBar::tab {{ background: {_PANEL_BG}; color: {_MUT};"
            f" padding: 6px 16px; border-radius: 3px; margin-right: 2px; }}"
            f"QTabBar::tab:selected {{ background: #313244; color: {_FG}; }}"
        )
        self.overview_tab    = OverviewTab(self)
        self.walkforward_tab = WalkForwardTab(self)
        self.oos_tab         = OOSTab(self)
        self.regime_tab      = RegimeTab(self)
        self.stability_tab   = StabilityTab(self)
        self.bias_tab        = BiasTab(self)
        self.report_tab      = ReportTab(self)

        tabs.addTab(self.overview_tab,    "Overview（总览）")
        tabs.addTab(self.walkforward_tab, "Walk Forward")
        tabs.addTab(self.oos_tab,         "OOS Testing")
        tabs.addTab(self.regime_tab,      "Regime Detection")
        tabs.addTab(self.stability_tab,   "Stability Test")
        tabs.addTab(self.bias_tab,        "Bias Detection")
        tabs.addTab(self.report_tab,      "Report")
        return tabs

    def _build_log_bar(self):
        w = QtWidgets.QWidget()
        w.setFixedHeight(120)
        w.setStyleSheet(f"background: {_PANEL_BG}; border-radius: 4px;")
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(8, 4, 8, 4)
        v.setSpacing(2)
        lbl = QtWidgets.QLabel("验证日志")
        lbl.setStyleSheet(f"color: {_MUT}; font-size: 10px;")
        v.addWidget(lbl)
        self._txt_log = QtWidgets.QTextEdit()
        self._txt_log.setReadOnly(True)
        self._txt_log.setStyleSheet(
            f"QTextEdit {{ background: #11111b; color: {_FG};"
            f" font-size: 11px; font-family: monospace;"
            f" border: 1px solid {_BORDER}; border-radius: 3px; }}"
        )
        v.addWidget(self._txt_log)
        return w

    # ------------------------------------------------------------------ #
    #  事件注册 / 注销
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        self._signal_log.connect(self._on_log)
        self._signal_progress.connect(self._on_progress)
        self._signal_result.connect(self._on_result)
        self._signal_error.connect(self._on_error)
        reg = self.event_engine.register
        reg(EVENT_VALIDATION_LOG,      self._signal_log.emit)
        reg(EVENT_VALIDATION_PROGRESS, self._signal_progress.emit)
        reg(EVENT_VALIDATION_RESULT,   self._signal_result.emit)
        reg(EVENT_VALIDATION_ERROR,    self._signal_error.emit)

    def _unregister_events(self) -> None:
        unreg = self.event_engine.unregister
        unreg(EVENT_VALIDATION_LOG,      self._signal_log.emit)
        unreg(EVENT_VALIDATION_PROGRESS, self._signal_progress.emit)
        unreg(EVENT_VALIDATION_RESULT,   self._signal_result.emit)
        unreg(EVENT_VALIDATION_ERROR,    self._signal_error.emit)

    # ------------------------------------------------------------------ #
    #  事件回调
    # ------------------------------------------------------------------ #

    def _on_log(self, event: Event) -> None:
        msg = event.data if isinstance(event.data, str) else str(event.data)
        self._txt_log.append(msg)
        sb = self._txt_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_progress(self, event: Event) -> None:
        data = event.data
        if isinstance(data, dict):
            pct = int(float(data.get("progress", 0.0)) * 100)
            self._progress.setValue(pct)
            msg = data.get("message", "")
            if msg:
                self._txt_log.append(f"  {msg}")

    def _on_result(self, event: Event) -> None:
        self._progress.setValue(100)
        self._set_running(False)
        self._lbl_status_val.setText("● 完成")
        self._lbl_status_val.setStyleSheet(f"color: {_GRN}; font-size: 11px;")
        self._txt_log.append("[完成] 验证任务结束。")
        result = event.data
        if result is None:
            return
        # Walk Forward 结果 → WalkForwardTab
        wf_results = getattr(result, 'walkforward_results', [])
        wf_summary = getattr(result, 'wf_summary', None)
        if wf_results:
            self.walkforward_tab.update_results(wf_results, wf_summary)
        # OOS 结果 → OOSTab
        oos_result = getattr(result, 'oos_result', None)
        if oos_result is not None:
            self.oos_tab.update_result(oos_result)
        # Regime 结果 -> RegimeTab
        regime_summary = getattr(result, 'regime_summary', None)
        if regime_summary is not None:
            self.regime_tab.update_summary(regime_summary)
        # Stability 结果 -> StabilityTab
        stability_summary = getattr(result, 'stability_summary', None)
        if stability_summary is not None:
            self.stability_tab.update_summary(stability_summary)
        # Bias 结果 -> BiasTab
        bias_summary = getattr(result, 'bias_summary', None)
        if bias_summary is not None:
            self.bias_tab.update_summary(bias_summary)
        # Overview -> OverviewTab
        self.overview_tab.update_result(result)
        # 综合评分日志
        score = getattr(result, 'overall_score', None)
        is_real = getattr(result, 'is_real_alpha', False)
        if score is not None:
            alpha_str = '真实' if is_real else '可疑'
            self._txt_log.append(
                f"<span style='color:#89b4fa'>[综合] "
                f"评分={score:.1f}  Alpha={alpha_str}</span>"
            )

    def _on_error(self, event: Event) -> None:
        data = event.data or {}
        error = data.get("error", "未知错误")
        self._set_running(False)
        self._lbl_status_val.setText("● 错误")
        self._lbl_status_val.setStyleSheet(f"color: {_RED}; font-size: 11px;")
        self._txt_log.append(
            f"<span style='color:{_RED}'>[ERROR] {error}</span>"
        )

    # ------------------------------------------------------------------ #
    #  按钮回调
    # ------------------------------------------------------------------ #

    def _on_run_clicked(self) -> None:
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is None:
            self._txt_log.append("[WARN] ResearchValidation 引擎未加载。")
            return
        params = self._collect_params()
        self._set_running(True)
        self._progress.setValue(0)
        self._lbl_status_val.setText("● 运行中")
        self._lbl_status_val.setStyleSheet(f"color: {_YLW}; font-size: 11px;")
        engine.run_validation(params)

    def _on_stop_clicked(self) -> None:
        engine = self.main_engine.get_engine(APP_NAME)
        if engine is not None:
            engine.stop()
        self._set_running(False)
        self._lbl_status_val.setText("● 已取消")
        self._lbl_status_val.setStyleSheet(f"color: {_MUT}; font-size: 11px;")

    # ------------------------------------------------------------------ #
    #  工具方法
    # ------------------------------------------------------------------ #

    def _collect_params(self) -> dict:
        return {
            "factor_name":     self._cmb_factor.currentText(),
            "start_date":      self._dte_start.date().toPython(),
            "end_date":        self._dte_end.date().toPython(),
            "train_window":    self._spn_train.value(),
            "test_window":     self._spn_test.value(),
            "step_size":       self._spn_step.value(),
            "oos_ratio":       self._spn_oos.value(),
            "run_walkforward": self._chk_wf.isChecked(),
            "run_oos":         self._chk_oos.isChecked(),
            "run_regime":      self._chk_reg.isChecked(),
            "run_stability":   self._chk_sta.isChecked(),
            "run_bias":        self._chk_bia.isChecked(),
        }

    def _set_running(self, running: bool) -> None:
        self._btn_run.setEnabled(not running)
        self._btn_stop.setEnabled(running)

    @staticmethod
    def _lbl(text: str):
        l = QtWidgets.QLabel(text)
        l.setStyleSheet(f"color: {_MUT}; font-size: 11px;")
        return l

    @staticmethod
    def _checkbox(text: str):
        cb = QtWidgets.QCheckBox(text)
        cb.setChecked(True)
        cb.setStyleSheet(f"color: {_FG}; font-size: 12px;")
        return cb

    @staticmethod
    def _combo_style() -> str:
        return (
            "QComboBox { background: #313244; color: #cdd6f4;"
            " border: 1px solid #45475a; border-radius: 3px;"
            " padding: 3px 6px; font-size: 12px; }"
        )

    @staticmethod
    def _input_style() -> str:
        return (
            "QDateEdit { background: #313244; color: #cdd6f4;"
            " border: 1px solid #45475a; border-radius: 3px;"
            " padding: 3px 6px; font-size: 12px; }"
        )

    @staticmethod
    def _spin_style() -> str:
        return (
            "QSpinBox, QDoubleSpinBox {"
            " background: #313244; color: #cdd6f4;"
            " border: 1px solid #45475a; border-radius: 3px;"
            " padding: 2px 4px; font-size: 11px; }"
        )

    def closeEvent(self, event) -> None:
        self._unregister_events()
        super().closeEvent(event)
