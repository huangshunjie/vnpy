"""
BatchResearchEngine

VeighNa BaseEngine 包装器，将 BatchBacktestingEngine 接入 MainEngine
的 EventEngine 总线，实现：

  - 在后台线程执行批量回测（不阻塞 Qt 主线程）
  - 每完成一只股票发出 EVENT_BATCH_RESULT + EVENT_BATCH_PROGRESS
  - 全部完成后发出 EVENT_BATCH_FINISHED
  - 支持中途停止（stop_backtesting）
  - 日志统一通过 EVENT_BATCH_LOG 广播
  - 提供同步 API（get_results、get_summary）供 Widget 使用
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import TYPE_CHECKING

from vnpy.event import Event, EventEngine
from vnpy.trader.engine import BaseEngine, MainEngine

from .base import (
    APP_NAME,
    EVENT_BATCH_FINISHED,
    EVENT_BATCH_LOG,
    EVENT_BATCH_PROGRESS,
    EVENT_BATCH_RESULT,
    EVENT_BATCH_STOPPED,
    ProgressData,
)
from .batch_engine import BatchBacktestingEngine
from .batch_result import BatchBacktestResult
from .statistics.enricher import ResultEnricher, TushareNameProvider
from .task import BacktestResult, TaskStatus

if TYPE_CHECKING:
    from .scheduler import RunSummary


class BatchResearchEngine(BaseEngine):
    """
    Adapter between VeighNa MainEngine and BatchBacktestingEngine.

    All heavy work runs in a daemon thread so the Qt event loop
    stays responsive.  Results are forwarded to the event bus so
    any number of widgets can subscribe without tight coupling.
    """

    def __init__(
        self,
        main_engine: MainEngine,
        event_engine: EventEngine,
    ) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)

        self.batch_engine: BatchBacktestingEngine = BatchBacktestingEngine()

        self._thread: threading.Thread | None = None
        self._stop_flag: bool = False
        self._results: list[BatchBacktestResult] = []
        # 自动加载 TushareNameProvider（如果配置了 token）
        _name_provider = TushareNameProvider.from_settings()
        self._enricher: ResultEnricher = ResultEnricher(
            name_provider=_name_provider
        )
        if _name_provider is not None:
            self.write_log("已加载 TushareNameProvider，股票名称和行业将自动填充")

    # ------------------------------------------------------------------ #
    #  Public configuration API (called from Widget)
    # ------------------------------------------------------------------ #

    def set_parameters(self, **kwargs) -> None:
        """
        Configure the inner BatchBacktestingEngine.
        Accepts the same kwargs as BatchBacktestingEngine.set_parameters().
        """
        self.batch_engine.set_parameters(**kwargs)
        name = getattr(kwargs.get("strategy_class"), "__name__", "?")
        self.write_log(f"参数已设置：策略={name}")

    def set_stock_pool(self, symbols: list[str]) -> None:
        """Set the list of vt_symbols to backtest."""
        self.batch_engine.set_stock_pool(symbols)
        self.write_log(f"股票池已设置：{len(symbols)} 只")

    def set_bars(self, vt_symbol: str, bars: list) -> None:
        """Pre-load BarData for CSV mode."""
        self.batch_engine.set_bars(vt_symbol, bars)

    # ------------------------------------------------------------------ #
    #  Run control
    # ------------------------------------------------------------------ #

    def run_backtesting(
        self,
        use_multiprocess: bool = False,
        max_workers: int | None = None,
    ) -> None:
        """
        Start batch backtesting in a background daemon thread.
        No-op if a run is already in progress.
        """
        if self._thread and self._thread.is_alive():
            self.write_log("回测正在运行中，请等待完成")
            return

        self._stop_flag = False
        self._results.clear()

        # 每次回测前重新读 token，保证配置对话框填完后立即生效
        _provider = TushareNameProvider.from_settings()
        self._enricher = ResultEnricher(name_provider=_provider)
        if _provider is not None:
            self.write_log("已加载 TushareNameProvider，将自动填充股票名称和行业")

        self._thread = threading.Thread(
            target=self._run_in_thread,
            args=(use_multiprocess, max_workers),
            daemon=True,
        )
        self._thread.start()
        self.write_log("批量回测已启动（后台线程）")

    def stop_backtesting(self) -> None:
        """
        Request graceful stop. The current task finishes first;
        the loop then checks _stop_flag before starting the next one.
        """
        if self._thread and self._thread.is_alive():
            self._stop_flag = True
            self.write_log("停止信号已发出，等待当前任务完成…")

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ------------------------------------------------------------------ #
    #  Result access (thread-safe snapshots)
    # ------------------------------------------------------------------ #

    def get_results(self) -> list[BatchBacktestResult]:
        return list(self._results)

    def get_summary(self) -> "RunSummary | None":
        return self.batch_engine.summary

    # ------------------------------------------------------------------ #
    #  Export delegates
    # ------------------------------------------------------------------ #

    def export_to_csv(
        self,
        filepath: str,
        column_manager=None,
        scope=None,
    ) -> None:
        if not self._results:
            self.write_log("\u65e0\u7ed3\u679c\u53ef\u5bfc\u51fa")
            return
        from .output.csv_exporter import CSVExporter
        from .output.exporter import ExportScope as _Scope
        from .column_manager import ColumnManager as _CM
        from pathlib import Path
        cm = column_manager or _CM()
        sc = scope or _Scope.ALL
        result = CSVExporter().export(
            self._results, Path(filepath), column_manager=cm, scope=sc
        )
        self.write_log(str(result))

    def export_to_excel(
        self,
        filepath: str,
        column_manager=None,
        scope=None,
        top_n: int = 20,
    ) -> None:
        if not self._results:
            self.write_log("\u65e0\u7ed3\u679c\u53ef\u5bfc\u51fa")
            return
        from .output.excel_exporter import ExcelExporter
        from .output.exporter import ExportScope as _Scope
        from .column_manager import ColumnManager as _CM
        from pathlib import Path
        cm = column_manager or _CM()
        sc = scope or _Scope.ALL
        result = ExcelExporter().export(
            self._results, Path(filepath),
            column_manager=cm, scope=sc, top_n=top_n
        )
        self.write_log(str(result))


    # ------------------------------------------------------------------ #
    #  BaseEngine overrides
    # ------------------------------------------------------------------ #

    def write_log(self, msg: str) -> None:
        """Emit log string to EVENT_BATCH_LOG."""
        self.event_engine.put(Event(EVENT_BATCH_LOG, msg))

    def close(self) -> None:
        self._stop_flag = True

    # ------------------------------------------------------------------ #
    #  Background thread
    # ------------------------------------------------------------------ #

    def _run_in_thread(
        self,
        use_multiprocess: bool,
        max_workers: int | None,
    ) -> None:
        """Execute batch backtest in background; emit events on completion."""
        from .scheduler import SerialScheduler, ProcessPoolScheduler  # noqa

        # Swap scheduler on inner engine for this run
        if use_multiprocess:
            scheduler = ProcessPoolScheduler(max_workers=max_workers)
        else:
            scheduler = SerialScheduler()

        orig_scheduler = self.batch_engine._scheduler
        self.batch_engine._scheduler = scheduler

        completed = 0
        success = skipped = failed = 0
        run_start = datetime.now()

        def on_task_done(result: BacktestResult) -> None:
            nonlocal completed, success, skipped, failed

            bbr = self._enricher.enrich(result)
            self._results.append(bbr)
            completed += 1

            if result.status == TaskStatus.SUCCESS:
                success += 1
            elif result.status == TaskStatus.SKIPPED:
                skipped += 1
            else:
                failed += 1

            # Single-result event (BatchBacktestResult)
            self.event_engine.put(Event(EVENT_BATCH_RESULT, bbr))

            # Progress event
            elapsed = (datetime.now() - run_start).total_seconds()
            pool = self.batch_engine._stock_pool
            total_count = pool.size() if pool else completed
            prog = ProgressData(
                completed=completed,
                total=total_count,
                success=success,
                skipped=skipped,
                failed=failed,
                current_symbol=result.vt_symbol,
                elapsed_seconds=elapsed,
            )
            self.event_engine.put(Event(EVENT_BATCH_PROGRESS, prog))

            # Cooperative stop: clear pending jobs after current task
            if self._stop_flag:
                scheduler.clear()

        run_summary = None
        try:
            self.batch_engine.run_backtesting(
                show_progress=False,
                on_task_done=on_task_done,
            )
            # Capture summary before restoring the original scheduler
            run_summary = getattr(scheduler, "summary", None)
        except Exception as e:
            self.write_log(f"批量回测异常：{e}")
        finally:
            # Copy summary onto the original scheduler so get_summary() works
            if run_summary is not None:
                orig_scheduler.summary = run_summary
            self.batch_engine._scheduler = orig_scheduler

        if self._stop_flag:
            self.write_log("批量回测已被用户中止")
            self.event_engine.put(Event(EVENT_BATCH_STOPPED, None))
        else:
            summary = run_summary or self.get_summary()
            self.write_log(f"批量回测完成：{summary}")
            self.event_engine.put(Event(EVENT_BATCH_FINISHED, summary))
