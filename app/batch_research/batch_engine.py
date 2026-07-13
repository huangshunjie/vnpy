"""
BatchBacktestingEngine

The top-level entry point for the batch backtesting system.

Responsibilities:
  - Accept user configuration (strategy, parameters, stock pool, data)
  - Build BacktestTask list from the stock pool
  - Drive the Scheduler to execute all tasks
  - Collect and expose results
  - Delegate export to output layer (Phase 7)

This class contains NO backtesting logic.
All backtesting is handled by Worker -> BacktestingEngine (one per symbol).

Typical usage::

    engine = BatchBacktestingEngine()
    engine.set_parameters(
        strategy_class=AtrRsiStrategy,
        start=datetime(2020, 1, 1),
        end=datetime(2022, 12, 31),
        capital=1_000_000,
        rate=1e-4,
        slippage=0.02,
        size=1.0,
        pricetick=0.01,
        strategy_setting={"atr_length": 22, "atr_ma_length": 10},
    )
    engine.set_stock_pool(["000001.SZSE", "600519.SSE"])
    engine.load_bars_from_directory(Path("data/"))
    engine.run_backtesting()
    df = engine.get_result_dataframe()
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from vnpy.trader.constant import Exchange, Interval
from vnpy_ctastrategy.backtesting import BacktestingMode
from vnpy_ctastrategy.template import CtaTemplate

from .parameter import BacktestParameter
from .task import BacktestResult, BacktestTask, TaskStatus
from .scheduler import Scheduler, SchedulerBase, ScheduleJob, RunSummary
from .datasource.stock_pool import StockPool
from .datasource.csv_loader import CSVLoader, CSVLoadConfig
from .utils.logger import get_logger

logger = get_logger()


class BatchBacktestingEngine:
    """
    Batch backtesting engine - system entry point.

    Orchestrates: StockPool -> tasks -> Scheduler -> results.
    Does not implement any backtesting logic itself.
    """

    def __init__(self, scheduler: SchedulerBase | None = None) -> None:
        self._strategy_class: type[CtaTemplate] | None = None
        self._parameter: BacktestParameter | None = None
        self._stock_pool: StockPool | None = None
        self._scheduler: SchedulerBase = scheduler or Scheduler()
        self._bars_map: dict[str, list] = {}
        self._results: list[BacktestResult] = []
        self._run_id: str = ""

    # ------------------------------------------------------------------ #
    #  Configuration
    # ------------------------------------------------------------------ #

    def set_parameters(
        self,
        strategy_class: type[CtaTemplate],
        start: datetime,
        end: datetime,
        capital: int = 1_000_000,
        rate: float = 1e-4,
        slippage: float = 0.0,
        size: float = 1.0,
        pricetick: float = 0.01,
        interval: Interval = Interval.DAILY,
        mode: BacktestingMode = BacktestingMode.BAR,
        risk_free: float = 0.03,
        annual_days: int = 240,
        half_life: int = 120,
        strategy_setting: dict[str, Any] | None = None,
    ) -> None:
        """Set global backtest parameters and strategy class."""
        self._strategy_class = strategy_class
        self._parameter = BacktestParameter(
            start=start,
            end=end,
            interval=interval,
            capital=capital,
            rate=rate,
            slippage=slippage,
            size=size,
            pricetick=pricetick,
            risk_free=risk_free,
            annual_days=annual_days,
            half_life=half_life,
            mode=mode,
            strategy_setting=strategy_setting or {},
        )
        logger.info(
            "Parameters set: strategy=%s  %s~%s  capital=%d",
            strategy_class.__name__, start.date(), end.date(), capital,
        )

    def set_stock_pool(
        self,
        symbols: list[str] | StockPool,
        as_of: Any = None,
    ) -> None:
        """
        Set the stock pool.

        :param symbols: List of vt_symbols/codes, or a StockPool instance.
        :param as_of:   Reference date for StockPool filters.
        """
        if isinstance(symbols, StockPool):
            self._stock_pool = symbols
        else:
            self._stock_pool = StockPool.from_symbols(symbols)
        logger.info("Stock pool set: %d symbols", self._stock_pool.size(as_of))

    # ------------------------------------------------------------------ #
    #  Data loading
    # ------------------------------------------------------------------ #

    def load_bars_from_directory(
        self,
        directory: Path,
        exchange: Exchange = Exchange.SZSE,
        interval: Interval = Interval.DAILY,
        encoding: str = "utf-8-sig",
        column_map: dict[str, str] | None = None,
    ) -> None:
        """
        Load bar data from a CSV directory and cache by vt_symbol.

        File convention: {symbol}.csv or {symbol}.{EXCHANGE}.csv
        When bars are pre-loaded here, Worker injects them directly
        instead of calling BacktestingEngine.load_data().
        """
        loader = CSVLoader()
        results = loader.load_directory(
            directory=Path(directory),
            exchange=exchange,
            interval=interval,
            encoding=encoding,
            column_map=column_map or {},
        )
        loaded = 0
        for r in results:
            vt_symbol = f"{r.symbol}.{r.exchange.value}"
            self._bars_map[vt_symbol] = r.bars
            loaded += r.loaded_count
            logger.debug("Loaded %s: %d bars", vt_symbol, r.loaded_count)
        logger.info(
            "CSV directory loaded: %d files, %d bars total",
            len(results), loaded,
        )

    def load_bars_from_file(
        self,
        filepath: Path,
        vt_symbol: str,
        interval: Interval = Interval.DAILY,
        encoding: str = "utf-8-sig",
        column_map: dict[str, str] | None = None,
    ) -> None:
        """Load bar data from a single CSV file for one symbol."""
        symbol, exchange_str = vt_symbol.split(".", 1)
        exchange = Exchange(exchange_str)
        loader = CSVLoader()
        config = CSVLoadConfig(
            filepath=Path(filepath),
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            encoding=encoding,
            column_map=column_map or {},
        )
        result = loader.load(config)
        self._bars_map[vt_symbol] = result.bars
        logger.info(
            "Loaded %s: %d bars (skipped=%d, errors=%d)",
            vt_symbol, result.loaded_count,
            result.skipped_rows, result.error_rows,
        )

    def set_bars(self, vt_symbol: str, bars: list) -> None:
        """Directly inject a pre-built BarData list for one symbol."""
        self._bars_map[vt_symbol] = bars
        logger.debug("set_bars: %s  %d bars", vt_symbol, len(bars))

    # ------------------------------------------------------------------ #
    #  Core: run backtesting
    # ------------------------------------------------------------------ #

    def run_backtesting(
        self,
        as_of: Any = None,
        show_progress: bool = True,
        on_task_start: Callable[[BacktestTask], None] | None = None,
        on_task_done: Callable[[BacktestResult], None] | None = None,
    ) -> list[BacktestResult]:
        """
        Execute batch backtesting for all symbols in the stock pool.

        Steps:
          1. Validate configuration
          2. Resolve stock pool to vt_symbol list
          3. Build ScheduleJob list (one per symbol)
          4. Delegate to Scheduler
          5. Store and return results

        :raises RuntimeError: If set_parameters() or set_stock_pool() not called.
        """
        self._validate_config()

        self._run_id = str(uuid.uuid4())[:8]
        logger.info("BatchBacktestingEngine run_id=%s starting", self._run_id)

        vt_symbols = self._stock_pool.get_symbols(as_of)  # type: ignore[union-attr]
        if not vt_symbols:
            logger.warning("Stock pool is empty, nothing to run")
            self._results = []
            return []

        jobs = self._build_jobs(vt_symbols)
        self._scheduler.clear()
        self._scheduler.submit(jobs)

        self._results = self._scheduler.run(
            self._parameter,  # type: ignore[arg-type]
            on_task_start=on_task_start,
            on_task_done=on_task_done,
            show_progress=show_progress,
        )

        if (s := getattr(self._scheduler, "summary", None)):
            logger.info("Batch run complete: %s", s)

        return self._results

    # ------------------------------------------------------------------ #
    #  Results access
    # ------------------------------------------------------------------ #

    @property
    def results(self) -> list[BacktestResult]:
        """All results from the last run_backtesting() call."""
        return self._results

    @property
    def summary(self) -> RunSummary | None:
        """RunSummary from the last run, or None if not run yet."""
        return getattr(self._scheduler, "summary", None)

    def get_result_dataframe(self):
        """
        Return results as a pandas DataFrame sorted by sharpe_ratio descending.

        Each row is one symbol; columns are BacktestResult.to_flat_dict() fields.
        """
        import pandas as pd  # noqa: PLC0415
        if not self._results:
            return pd.DataFrame()
        rows = [r.to_flat_dict() for r in self._results]
        df = pd.DataFrame(rows)
        if "sharpe_ratio" in df.columns:
            df = df.sort_values("sharpe_ratio", ascending=False).reset_index(drop=True)
        return df

    def get_results_by_status(self, status: TaskStatus) -> list[BacktestResult]:
        """Filter results by TaskStatus."""
        return [r for r in self._results if r.status == status]

    @property
    def successful_results(self) -> list[BacktestResult]:
        return self.get_results_by_status(TaskStatus.SUCCESS)

    @property
    def failed_results(self) -> list[BacktestResult]:
        return self.get_results_by_status(TaskStatus.FAILED)

    @property
    def skipped_results(self) -> list[BacktestResult]:
        return self.get_results_by_status(TaskStatus.SKIPPED)

    # ------------------------------------------------------------------ #
    #  Export (delegates to Phase 7 output layer)
    # ------------------------------------------------------------------ #

    def export_to_csv(self, filepath: Path | str) -> None:
        """Export all results to CSV (Phase 7 CSVWriter)."""
        from .output.csv_writer import CSVWriter  # noqa: PLC0415
        CSVWriter().write(self._results, Path(filepath))
        logger.info("Results exported to CSV: %s", filepath)

    def export_to_excel(self, filepath: Path | str) -> None:
        """Export all results to Excel (Phase 7 ExcelWriter)."""
        from .output.excel_writer import ExcelWriter  # noqa: PLC0415
        ExcelWriter().write(self._results, Path(filepath))
        logger.info("Results exported to Excel: %s", filepath)

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #

    def _validate_config(self) -> None:
        if self._strategy_class is None or self._parameter is None:
            raise RuntimeError("Call set_parameters() before run_backtesting()")
        if self._stock_pool is None:
            raise RuntimeError("Call set_stock_pool() before run_backtesting()")

    def _build_jobs(self, vt_symbols: list[str]) -> list[ScheduleJob]:
        """Build one ScheduleJob per symbol; attach pre-loaded bars if available."""
        assert self._strategy_class is not None
        assert self._parameter is not None

        jobs: list[ScheduleJob] = []
        for vt_symbol in vt_symbols:
            task = BacktestTask(
                vt_symbol=vt_symbol,
                strategy_class=self._strategy_class,
                strategy_setting=self._parameter.strategy_setting.copy(),
                task_id=f"{self._run_id}_{vt_symbol}",
            )
            bars = self._bars_map.get(vt_symbol)
            jobs.append(ScheduleJob(task=task, bars=bars))

        logger.debug("Built %d jobs for run_id=%s", len(jobs), self._run_id)
        return jobs

    def __repr__(self) -> str:
        pool_size = self._stock_pool.size() if self._stock_pool else 0
        strategy = self._strategy_class.__name__ if self._strategy_class else "None"
        return (
            f"BatchBacktestingEngine("
            f"strategy={strategy}, "
            f"pool_size={pool_size}, "
            f"results={len(self._results)})"
        )
