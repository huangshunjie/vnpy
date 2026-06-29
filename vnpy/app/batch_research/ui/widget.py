"""
ui/widget.py

BatchResearchWidget — 批量回测研究主窗口

布局：
┌─────────────────────────────────────────────────────────┐
│  工具栏：[配置参数] [开始回测] [停止] [导出CSV] [导出Excel]
│          [列设置] [因子分析] [清空结果]
├─────────────────────────────────────────────────────────┤
│  进度条 + 状态文字                                         │
├─────────────────────────────────────────────────────────┤
│  结果表格（ResultTableWidget，实时追加，动态列）             │
├─────────────────────────────────────────────────────────┤
│  日志面板（滚动文本）                                       │
└─────────────────────────────────────────────────────────┘
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
from ..column_manager import ColumnManager
from ..engine import BatchResearchEngine
from .result_table import ResultTableWidget
from .setting_dialog import SettingDialog
from .factor_dialog import FactorAnalysisDialog
from .column_setting_dialog import ColumnSettingDialog
from .stock_pool_dialog import StockPoolDialog
from ..manager import StockPoolManager


class BatchResearchWidget(QtWidgets.QWidget):

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

        self._last_config: dict = {}
        self._column_manager: ColumnManager = ColumnManager()
        self._pool_manager: StockPoolManager = StockPoolManager()

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
        self._btn_pool    = QtWidgets.QPushButton("股票池")
        self._btn_columns = QtWidgets.QPushButton("列设置")
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
        self._btn_pool.clicked.connect(self._on_pool)
        self._btn_columns.clicked.connect(self._on_column_settings)
        self._btn_factor.clicked.connect(self._on_factor_analysis)
        self._btn_clear.clicked.connect(self._on_clear)

        toolbar = QtWidgets.QHBoxLayout()
        for btn in (
            self._btn_config, self._btn_pool, self._btn_run, self._btn_stop,
            None,
            self._btn_csv, self._btn_excel,
            None,
            self._btn_columns, self._btn_factor, self._btn_clear,
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

        # ---- Result table（接入 ColumnManager）----
        self._result_table = ResultTableWidget(
            self.main_engine,
            self.event_engine,
            self._column_manager,
        )

        # ---- Log panel ----
        self._log_text = QtWidgets.QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumHeight(160)

        # ---- Splitter ----
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
        dlg._pool_manager = self._pool_manager
        dlg._load_config()        # restore saved config using the shared manager
        dlg._update_pool_display()
        if self._last_config:
            dlg.set_config(self._last_config)

        if dlg.exec_() != dlg.DialogCode.Accepted:
            return

        cfg = dlg.get_config()
        self._last_config = cfg

        if cfg["parameters"].get("strategy_class") is None:
            QtWidgets.QMessageBox.warning(self, "警告", "未选择策略类，无法运行回测")
            return

        self.batch_engine.set_parameters(**cfg["parameters"])
        self.batch_engine.set_stock_pool(cfg["symbols"])
        pool_name = self._pool_manager.current_name
        pool_n    = len(cfg["symbols"])
        self._append_log(
            f"配置完成：策略={cfg['parameters']['strategy_class'].__name__}  "
            f"股票池={pool_name!r}（{pool_n} 只）"
        )
        self._btn_run.setEnabled(True)

    def _on_pool(self) -> None:
        """Open StockPoolDialog from the main toolbar."""
        dlg = StockPoolDialog(
            manager=self._pool_manager,
            initial_name=self._pool_manager.current_name,
            parent=self,
        )
        dlg.exec_()

    def _on_run(self) -> None:
        if self.batch_engine.is_running():
            return

        cfg = self._last_config
        use_mp  = cfg.get("use_multiprocess", False)
        workers = cfg.get("max_workers", 4)

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
            from ..output.exporter import ExportScope
            self.batch_engine.export_to_csv(
                path,
                column_manager=self._column_manager,
                scope=ExportScope.ALL,
            )

    def _on_export_excel(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出结果 Excel", "", "Excel 文件 (*.xlsx)"
        )
        if path:
            from ..output.exporter import ExportScope
            self.batch_engine.export_to_excel(
                path,
                column_manager=self._column_manager,
                scope=ExportScope.ALL,
            )

    def _on_column_settings(self) -> None:
        """打开列设置对话框。"""
        dlg = ColumnSettingDialog(self._column_manager, parent=self)
        dlg.exec_()

    def _on_factor_analysis(self) -> None:
        results = self.batch_engine.get_results()
        if not results:
            QtWidgets.QMessageBox.information(self, "提示", "暂无回测结果，请先运行回测")
            return
        dlg = FactorAnalysisDialog(
            results=results,
            bars_map=self.batch_engine.batch_engine._bars_map,
            parent=self,
        )
        dlg.exec_()
        # 因子分析写回了 LF 字段（composite_score / factor_rank 等），刷新表格
        self._result_table.refresh_all_rows()

    def _on_clear(self) -> None:
        self._result_table.clear_results()
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("就绪")
        self._status_label.setText("结果已清空")
        self._btn_csv.setEnabled(False)
        self._btn_excel.setEnabled(False)
        self._btn_factor.setEnabled(False)

    # ------------------------------------------------------------------ #
    #  Event handlers
    # ------------------------------------------------------------------ #

    def _on_log_event(self, event: Event) -> None:
        self._append_log(event.data)

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
        if self.batch_engine.get_results():
            self._btn_csv.setEnabled(True)
            self._btn_excel.setEnabled(True)
            self._btn_factor.setEnabled(True)

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #

    def _append_log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_text.append(f"[{ts}]  {msg}")
        sb = self._log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def show(self) -> None:
        self.showMaximized()
