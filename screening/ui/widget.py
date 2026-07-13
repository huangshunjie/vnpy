"""
screening/ui/widget.py
ScreeningWidget - Quant Screening Platform main window (Phase 1)
"""
from __future__ import annotations
from vnpy.trader.ui import QtCore, QtWidgets
from vnpy.trader.engine import MainEngine
from vnpy.event import EventEngine
from ..constant import APP_NAME
from ..event import (
    EVENT_SCREENING_STARTED, EVENT_SCREENING_DONE,
    EVENT_SCREENING_ERROR, EVENT_SCREENING_LOG,
    EVENT_UNIVERSE_UPDATED, EVENT_SCORE_UPDATED,
    EVENT_BACKTEST_DONE, EVENT_PORTFOLIO_GENERATED,
)
from .universe_widget import UniverseWidget
from .condition_widget import ConditionWidget
from .factor_rank_widget import FactorRankWidget
from .risk_filter_widget import RiskFilterWidget
from .portfolio_widget import PortfolioWidget
from .result_widget import ResultWidget
from .backtest_widget import BacktestWidget

_BG="#1e1e2e"; _PANEL="#181825"; _BORDER="#45475a"; _FG="#cdd6f4"
_MUT="#6c7086"; _BLU="#89b4fa"; _GRN="#a6e3a1"; _YLW="#f9e2af"
_MAV="#cba6f7"; _RED="#f38ba8"; _ORG="#fab387"

def _btn(label, bg, hv, pr):
    b = QtWidgets.QPushButton(label)
    b.setStyleSheet(
        f"QPushButton{{background:{bg};color:#1e1e2e;border:1px solid {bg};"
        f"border-radius:4px;padding:6px 14px;font-size:12px;font-weight:bold;}}"
        f"QPushButton:hover{{background:{hv};}}"
        f"QPushButton:pressed{{background:{pr};}}"
        f"QPushButton:disabled{{background:#313244;color:#6c7086;}}")
    b.setMinimumWidth(110)
    return b

class ScreeningWidget(QtWidgets.QMainWindow):
    """Quant Screening Platform main window (Phase 1 framework)."""
    widget_name = f"{APP_NAME}Widget"

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__()
        self.main_engine = main_engine
        self.event_engine = event_engine
        self.engine = main_engine.get_engine(APP_NAME)
        self._init_ui()
        self._register_events()
        if self.engine:
            self.engine.init()
            self.engine.start()

    def _sep(self):
        s = QtWidgets.QFrame()
        s.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        s.setStyleSheet(f"border:none;border-top:1px solid {_BORDER};")
        return s

    def _init_ui(self) -> None:
        self.setWindowTitle("Quant Screening Platform  机构级量化条件选股系统")
        self.setMinimumSize(1400, 860)
        self.setStyleSheet(f"QMainWindow{{background:{_BG};}}")
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)
        root.addWidget(self._build_header(), stretch=0)
        root.addWidget(self._build_top_panels(), stretch=3)
        root.addWidget(self._build_bottom_tabs(), stretch=2)
        root.addWidget(self._build_button_bar(), stretch=0)
        root.addWidget(self._build_status_bar(), stretch=0)

    def _build_header(self):
        w = QtWidgets.QWidget()
        w.setFixedHeight(38)
        w.setStyleSheet(f"background:{_PANEL};border-radius:6px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(16, 4, 16, 4)
        title = QtWidgets.QLabel("Quant Screening Platform  |  机构级 Alpha Universe 生产系统")
        title.setStyleSheet(f"color:{_MAV};font-size:13px;font-weight:bold;border:none;")
        h.addWidget(title)
        h.addStretch()
        self._status_badge = QtWidgets.QLabel("● IDLE")
        self._status_badge.setStyleSheet(f"color:{_MUT};font-size:11px;border:none;")
        h.addWidget(self._status_badge)
        phase_lbl = QtWidgets.QLabel("Phase 8  Portfolio + Templates")
        phase_lbl.setStyleSheet(f"color:{_MUT};font-size:10px;border:none;")
        h.addWidget(phase_lbl)
        return w

    def _build_top_panels(self):
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle{background:#313244;width:2px;}")
        self.universe_widget = UniverseWidget(self.engine)
        self.condition_widget = ConditionWidget(self.engine)
        self.factor_rank_widget = FactorRankWidget(self.engine)
        for w in [self.universe_widget, self.condition_widget, self.factor_rank_widget]:
            w.setStyleSheet(f"background:{_PANEL};border-radius:6px;border:1px solid {_BORDER};")
            splitter.addWidget(w)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        splitter.setStretchFactor(2, 2)
        return splitter

    def _build_bottom_tabs(self):
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setStyleSheet(
            f"QTabWidget::pane{{background:{_PANEL};border:1px solid {_BORDER};border-radius:4px;}}"
            f"QTabBar::tab{{background:#11111b;color:{_MUT};padding:5px 16px;"
            f"border:1px solid {_BORDER};border-bottom:none;border-radius:4px 4px 0 0;font-size:11px;}}"
            f"QTabBar::tab:selected{{background:{_PANEL};color:{_BLU};border-bottom:2px solid {_BLU};}}"
            f"QTabBar::tab:hover{{color:{_FG};}}")
        self.result_widget = ResultWidget(self.engine)
        self.backtest_widget = BacktestWidget(self.engine)
        self.tab_widget.addTab(self.result_widget, "Stock Result  选股结果")
        self.portfolio_widget = PortfolioWidget(self.engine)
        self.tab_widget.addTab(self.backtest_widget, "Backtest  回测")
        self.tab_widget.addTab(self.portfolio_widget, "Portfolio  组合权重")
        return self.tab_widget

    def _build_button_bar(self):
        w = QtWidgets.QWidget()
        w.setFixedHeight(46)
        w.setStyleSheet(f"background:{_PANEL};border-radius:6px;border:1px solid {_BORDER};")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(12, 6, 12, 6)
        h.setSpacing(10)
        self._btn_run       = _btn("▶  运行筛选",  _GRN, "#b4eda1", "#7ecb6e")
        self._btn_backtest  = _btn("⏱  回测",      _BLU, "#a0c4ff", "#6d9fe0")
        self._btn_portfolio = _btn("⊕  生成组合",  _MAV, "#d9c0ff", "#b090e0")
        self._btn_save      = _btn("💾  保存模板",  _YLW, "#fff0a0", "#e0d060")
        self._btn_export    = _btn("↑  导出",      _ORG, "#ffc880", "#e09040")
        self._btn_run.clicked.connect(self._on_run_screening)
        self._btn_backtest.clicked.connect(self._on_run_backtest)
        self._btn_portfolio.clicked.connect(self._on_generate_portfolio)
        self._btn_save.clicked.connect(self._on_save_template)
        self._btn_export.clicked.connect(self._on_export)
        for b in [self._btn_run, self._btn_backtest,
                  self._btn_portfolio, self._btn_save, self._btn_export]:
            h.addWidget(b)
        h.addStretch()
        return w

    def _build_status_bar(self):
        w = QtWidgets.QWidget()
        w.setFixedHeight(24)
        w.setStyleSheet("background:#11111b;")
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(12, 2, 12, 2)
        self._log_label = QtWidgets.QLabel("就绪")
        self._log_label.setStyleSheet(f"color:{_MUT};font-size:10px;")
        h.addWidget(self._log_label)
        h.addStretch()
        return w

    def _on_run_screening(self) -> None:
        if self.engine:
            self.engine.run_screening()
        self._set_log("运行筛选…")

    def _on_run_backtest(self) -> None:
        if self.engine:
            self.engine.run_backtest()
        self._set_log("回测…")
        self.tab_widget.setCurrentWidget(self.backtest_widget)

    def _on_generate_portfolio(self) -> None:
        if self.engine:
            self.engine.generate_portfolio()
        self._set_log("生成组合权重…")

    def _on_save_template(self) -> None:
        if hasattr(self, "portfolio_widget"):
            self.portfolio_widget._on_save_template()
        self._set_log("保存模板…")

    def _on_export(self) -> None:
        if hasattr(self, "result_widget"):
            self.result_widget._on_export()
        self._set_log("导出…")

    def _register_events(self) -> None:
        self._handlers = {
            EVENT_SCREENING_STARTED:   self._on_screening_started,
            EVENT_SCREENING_DONE:      self._on_screening_done,
            EVENT_SCREENING_ERROR:     self._on_screening_error,
            EVENT_SCREENING_LOG:       self._on_screening_log,
            EVENT_UNIVERSE_UPDATED:    self._on_universe_updated,
            EVENT_SCORE_UPDATED:       self._on_score_updated,
            EVENT_BACKTEST_DONE:       self._on_backtest_done,
            EVENT_PORTFOLIO_GENERATED: self._on_portfolio_generated,
        }
        for et, handler in self._handlers.items():
            self.event_engine.register(et, handler)

    def _unregister_events(self) -> None:
        for et, handler in self._handlers.items():
            try:
                self.event_engine.unregister(et, handler)
            except Exception:
                pass

    def _on_screening_started(self, event) -> None:
        self._status_badge.setText("● RUNNING")
        self._status_badge.setStyleSheet(f"color:{_GRN};font-size:11px;border:none;")
        self._set_log("选股运行中…")

    def _on_screening_done(self, event) -> None:
        self._status_badge.setText("● DONE")
        self._status_badge.setStyleSheet(f"color:{_BLU};font-size:11px;border:none;")
        self._set_log("选股完成")

    def _on_screening_error(self, event) -> None:
        data = event.data or {}
        self._status_badge.setText("● ERROR")
        self._status_badge.setStyleSheet(f"color:{_RED};font-size:11px;border:none;")
        self._set_log(f"错误：{data.get('msg', '')}")

    def _on_screening_log(self, event) -> None:
        data = event.data or {}
        self._set_log(data.get("msg", ""))

    def _on_universe_updated(self, event) -> None:
        if self.engine and hasattr(self, "universe_widget"):
            uni = self.engine.universe_engine.get_universe()
            self.universe_widget.update_preview(uni)

    def _on_score_updated(self, event) -> None:
        if self.engine:
            result = self.engine.scoring_engine.get_last_result()
            self.result_widget.update_result(result)
            self.tab_widget.setCurrentWidget(self.result_widget)

    def _on_backtest_done(self, event) -> None:
        if self.engine and hasattr(self, "backtest_widget"):
            result = self.engine.backtest_engine.get_last_result()
            if result:
                self.backtest_widget.update_result(result)
                self.tab_widget.setCurrentWidget(self.backtest_widget)

    def _on_portfolio_generated(self, event) -> None:
        if self.engine:
            result = self.engine.portfolio_bridge.get_last_result()
            sr = self.engine.scoring_engine.get_last_result()
            if result: self.portfolio_widget.update_result(result, sr)

    def _set_log(self, msg: str) -> None:
        try:
            self._log_label.setText(msg)
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        if self.engine:
            self.engine.stop()
        self._unregister_events()
        event.accept()
