"""
ui/widget.py

BatchResearchWidget — 批量回测研究主窗口

布局（垂直三分）：
┌─────────────────────────────────────────────────────────┐
│  工具栏：[配置参数] [开始回测] [停止] [导出CSV] [导出Excel] [因子分析]
├─────────────────────────────────────────────────────────┤
│  进度条 + 状态文字                                         │
├─────────────────────────────────────────────────────────┤
│  结果表格（ResultTableWidget，实时追加）                    │
├─────────────────────────────────────────────────────────┤
│  日志面板（滚动文本）                                       │
└─────────────────────────────────────────────────────────┘

事件订阅：
  EVENT_BATCH_LOG      → 日志面板追加
  EVENT_BATCH_PROGRESS → 进度条 + 状态更新
  EVENT_BATCH_RESULT   → 结果表格（由 ResultTableWidget 自行订阅）
  EVENT_BATCH_FINISHED → 进度条满 + 按钮恢复
  EVENT_BATCH_STOPPED  → 进度条状态 + 按钮恢复
"""

from __future__ import annotations

from datetime import datetime

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.trader.ui import QtCore, QtWidgets

from ..base import (
    APP_NAME,
    EVENT_BATCH_FINISHED,
    EVENT_BATCH_LOG,
    EVENT_BATCH_PROGRESS,
    EVENT_BATCH_STOPPED,
    ProgressData,
)
from ..engine import BatchResearchEngine
from .result_table import ResultTableWidget
from .setting_dialog import SettingDialog
from .factor_dialog import FactorAnalysisDialog


class BatchResearchWidget(QtWidgets.QWidget):
    """
    Main window for BatchResearch app.

    Registered in BatchResearchApp.widget_name so VeighNa
    instantiates it when the user opens the app from the menu.
    """

    signal_log:      QtCore.Signal = QtCore.Signal(Event)
    signal_progress: QtCore.Signal = QtCore.Signal(Event)
    signal_finished: QtCore.Signal = QtCore.Signal(Event)
    signal_stopped:  QtCore.Signal = QtCore.Signal(Event)

    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__()

        self.main_engine:   MainEngine          = main_engine
        self.event_engine:  EventEngine         = event_engine
        self.batch_engine:  BatchResearchEngine = (
            main_engine.get_engine(APP_NAME)  # type: ignore[assignment]
        )

        self._last_config: dict = {}   # remember last dialog settings

        self._init_ui()
        self._register_events()

    # ------------------------------------------------------------------ #
    #  UI construction
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        self.setWindowTitle("批量回测研究")
        self.resize(1200, 800)

        # ---- Toolbar ----
        self._btn_config  = QtWidgets.QPushButton("⚙ 配置参数")
        self._btn_run     = QtWidgets.QPushButton("▶ 开始回测")
        self._btn_stop    = QtWidgets.QPushButton("■ 停止")
        self._btn_csv     = QtWidgets.QPushButton("导出 CSV")
        self._btn_excel   = QtWidgets.QPushButton("导出 Excel")
        self._btn_factor  = QtWidgets.QPushButton("因子分析")
        self._btn_clear   = QtWidgets.QPushButton("清空结果")

        self._btn_stop.setEnabled(False)
        self._btn_csv.setEnabled(False)
        self._btn_excel.setEnabled(False)
        self._btn_factor.setEnabled(False)

        self._btn_config.clicked.connect(self._on_config)
        self._btn_run.clicked.connect(self._on_run)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_csv.clicked.connect(self._on_export_csv)
        self._btn_excel.clicked.connect(self._on_export_excel)
        self._btn_factor.clicked.connect(self._on_factor_analysis)
        self._btn_clear.clicked.connect(self._on_clear)

        toolbar = QtWidgets.QHBoxLayout()
        for btn in (
            self._btn_config, self._btn_run, self._btn_stop,
            None,
            self._btn_csv, self._btn_excel,
            None,
            self._btn_factor, self._btn_clear,
        ):
            if btn is None:
                toolbar.addStretch()
            else:
                toolbar.addWidget(btn)

        # ---- Progress bar ----
        self._progress_bar = QtWidgets.QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("就绪")
        self._progress_bar.setFixedHeight(22)

        self._status_label = QtWidgets.QLabel("尚未运行回测")
        self._status_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )

        prog_row = QtWidgets.QHBoxLayout()
        prog_row.addWidget(self._progress_bar, 3)
        prog_row.addWidget(self._status_label, 1)

        # ---- Result table ----
        self._result_table = ResultTableWidget(
            self.main_engine, self.event_engine
        )

        # ---- Log panel ----
        self._log_text = QtWidgets.QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(160)
        self._log_text.setFont(
            QtWidgets.QApplication.font()
        )

        # ---- Splitter (result / log) ----
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        splitter.addWidget(self._result_table)
        splitter.addWidget(self._log_text)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        # ---- Master layout ----
        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(toolbar)
        vbox.addLayout(prog_row)
        vbox.addWidget(splitter, 1)
        self.setLayout(vbox)

    # ------------------------------------------------------------------ #
    #  Event registration
    # ------------------------------------------------------------------ #

    def _register_events(self) -> None:
        self.signal_log.connect(self._on_log_event)
        self.signal_progress.connect(self._on_progress_event)
        self.signal_finished.connect(self._on_finished_event)
        self.signal_stopped.connect(self._on_stopped_event)

        self.event_engine.register(EVENT_BATCH_LOG,      self.signal_log.emit)
        self.event_engine.register(EVENT_BATCH_PROGRESS, self.signal_progress.emit)
        self.event_engine.register(EVENT_BATCH_FINISHED, self.signal_finished.emit)
        self.event_engine.register(EVENT_BATCH_STOPPED,  self.signal_stopped.emit)

    # ------------------------------------------------------------------ #
    #  Button handlers
    # ------------------------------------------------------------------ #

    def _on_config(self) -> None:
        dlg = SettingDialog(parent=self)
        if self._last_config:
            dlg.set_config(self._last_config)

        if dlg.exec_() != dlg.DialogCode.Accepted:
            return

        cfg = dlg.get_config()
        self._last_config = cfg

        # Apply to engine
        if cfg["parameters"].get("strategy_class") is None:
            QtWidgets.QMessageBox.warning(
                self, "警告", "未选择策略类，无法运行回测"
            )
            return

        self.batch_engine.set_parameters(**cfg["parameters"])
        self.batch_engine.set_stock_pool(cfg["symbols"])
        self._append_log(
            f"配置完成：策略={cfg['parameters']['strategy_class'].__name__}  "
            f"股票池={len(cfg['symbols'])} 只"
        )
        self._btn_run.setEnabled(True)

    def _on_run(self) -> None:
        if self.batch_engine.is_running():
            return

        cfg = self._last_config
        use_mp = cfg.get("use_multiprocess", False)
        workers = cfg.get("max_workers", 4)

        # Reset UI state for new run
        self._result_table.clear_results()
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("0%")
        self._status_label.setText("运行中…")
        self._btn_run.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_csv.setEnabled(False)
        self._btn_excel.setEnabled(False)
        self._btn_factor.setEnabled(False)

        self.batch_engine.run_backtesting(
            use_multiprocess=use_mp,
            max_workers=workers,
        )

    def _on_stop(self) -> None:
        self.batch_engine.stop_backtesting()
        self._btn_stop.setEnabled(False)

    def _on_export_csv(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出结果 CSV", "", "CSV 文件 (*.csv)"
        )
        if path:
            self.batch_engine.export_to_csv(path)

    def _on_export_excel(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出结果 Excel", "", "Excel 文件 (*.xlsx)"
        )
        if path:
            self.batch_engine.export_to_excel(path)

    def _on_factor_analysis(self) -> None:
        results = self.batch_engine.get_results()
        if not results:
            QtWidgets.QMessageBox.information(
                self, "提示", "暂无回测结果，请先运行回测"
            )
            return
        dlg = FactorAnalysisDialog(
            results=results,
            bars_map=self.batch_engine.batch_engine._bars_map,
            parent=self,
        )
        dlg.exec_()

    def _on_clear(self) -> None:
        self._result_table.clear_results()
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("就绪")
        self._status_label.setText("结果已清空")
        self._btn_csv.setEnabled(False)
        self._btn_excel.setEnabled(False)
        self._btn_factor.setEnabled(False)

    # ------------------------------------------------------------------ #
    #  Event handlers (always invoked on main thread via Signal)
    # ------------------------------------------------------------------ #

    def _on_log_event(self, event: Event) -> None:
        msg: str = event.data
        self._append_log(msg)

    def _on_progress_event(self, event: Event) -> None:
        prog: ProgressData = event.data
        pct = int(prog.percent)
        self._progress_bar.setValue(pct)
        self._progress_bar.setFormat(f"{pct}%")

        elapsed = prog.elapsed_seconds
        self._status_label.setText(
            f"{prog.completed}/{prog.total}  "
            f"✓{prog.success} ✗{prog.failed} -{prog.skipped}  "
            f"{elapsed:.1f}s  [{prog.current_symbol}]"
        )

    def _on_finished_event(self, event: Event) -> None:
        self._progress_bar.setValue(100)
        self._progress_bar.setFormat("完成 100%")

        summary = event.data
        if summary:
            self._status_label.setText(
                f"完成：共{summary.total}只  "
                f"✓{summary.success} ✗{summary.failed} -{summary.skipped}  "
                f"{summary.elapsed_seconds:.1f}s"
            )

        self._result_table.enable_sorting()
        self._btn_run.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_csv.setEnabled(True)
        self._btn_excel.setEnabled(True)
        self._btn_factor.setEnabled(True)

    def _on_stopped_event(self, event: Event) -> None:
        self._progress_bar.setFormat("已中止")
        self._status_label.setText("用户已停止回测")
        self._result_table.enable_sorting()
        self._btn_run.setEnabled(True)
        self._btn_stop.setEnabled(False)
        results = self.batch_engine.get_results()
        if results:
            self._btn_csv.setEnabled(True)
            self._btn_excel.setEnabled(True)
            self._btn_factor.setEnabled(True)

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _append_log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_text.append(f"[{ts}]  {msg}")
        # Auto-scroll
        sb = self._log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def show(self) -> None:
        self.showMaximized()
