"""
Worker

Single-stock backtest execution unit.

Responsibilities:
  - Accept BacktestTask + BacktestParameter
  - Create and configure BacktestingEngine (call only, never modify)
  - Support two data sources:
      1. Database mode (default): BacktestingEngine.load_data() reads from configured DB
      2. CSV inject mode: inject external BarData list directly into history_data,
         bypassing load_data()
  - Execute full backtest pipeline:
      set_parameters -> add_strategy -> load_data/inject -> run_backtesting
      -> calculate_result -> calculate_statistics
  - Capture all exceptions, return TaskStatus.FAILED, never re-raise
  - Return BacktestResult (full stats + timing)

Design constraints:
  - Never modify BacktestingEngine
  - Never change vt_symbol (one engine = one symbol)
  - Stateless: run() creates a fresh BacktestingEngine each call, safe for threading
"""

import traceback
from datetime import datetime

from vnpy_ctastrategy.backtesting import BacktestingEngine

from .parameter import BacktestParameter
from .task import BacktestResult, BacktestTask, TaskStatus
from .utils.logger import get_logger
from .utils.timer import Timer

logger = get_logger()


class Worker:
    """
    Single-stock backtest worker.

    Worker is stateless. Each run() call creates a brand-new BacktestingEngine
    instance, so concurrent calls for different symbols are fully isolated.

    Usage::

        worker = Worker()
        result = worker.run(task, parameter, bars=bar_list)
    """

    def run(
        self,
        task: BacktestTask,
        parameter: BacktestParameter,
        bars: list | None = None,
        suppress_output: bool = True,
    ) -> BacktestResult:
        """
        Execute one complete single-stock backtest.

        :param task:            Backtest task (vt_symbol, strategy class, settings).
        :param parameter:       Global backtest parameters (dates, capital, costs).
        :param bars:            Optional BarData list. When provided, injected directly
                                into history_data, bypassing load_data().
        :param suppress_output: Silence BacktestingEngine's built-in print output.
        :return:                BacktestResult. Never raises.
        """
        result = BacktestResult(
            vt_symbol=task.vt_symbol,
            task_id=task.task_id,
            strategy_name=task.strategy_class.__name__,
        )

        timer = Timer()
        timer.start()
        result.run_start_time = datetime.now()

        try:
            stats = self._run_engine(task, parameter, bars, suppress_output)
            result.statistics = stats
            result.status = TaskStatus.SUCCESS if stats else TaskStatus.SKIPPED
            logger.debug(
                "[%s] %s  total_return=%.2f%%  sharpe=%.2f",
                task.task_id or task.vt_symbol,
                result.status.value,
                result.total_return,
                result.sharpe_ratio,
            )

        except Exception:
            result.status = TaskStatus.FAILED
            result.error_msg = traceback.format_exc()
            logger.warning(
                "[%s] %s backtest failed:\n%s",
                task.task_id or task.vt_symbol,
                task.vt_symbol,
                result.error_msg,
            )

        finally:
            result.run_end_time = datetime.now()
            elapsed = timer.stop()
            logger.debug("[%s] elapsed %.3fs", task.task_id or task.vt_symbol, elapsed)

        return result

    @staticmethod
    def _run_engine(
        task: BacktestTask,
        parameter: BacktestParameter,
        bars: list | None,
        suppress_output: bool,
    ) -> dict:
        """
        Create BacktestingEngine and run full pipeline, returning statistics dict.

        Call order matches official BacktestingEngine usage:
          1. set_parameters()
          2. add_strategy()
          3. inject bars / load_data()
          4. run_backtesting()
          5. calculate_result()
          6. calculate_statistics()
        """
        engine = BacktestingEngine()

        if suppress_output:
            engine.output = lambda msg: None  # type: ignore[method-assign]

        # Task-level start/end override global parameter (e.g. newly-listed stocks)
        effective_start = task.start or parameter.start
        effective_end   = task.end   or parameter.end

        kwargs = parameter.to_engine_kwargs(task.vt_symbol)
        kwargs["start"] = effective_start
        kwargs["end"]   = effective_end
        engine.set_parameters(**kwargs)

        # Task strategy_setting wins over parameter strategy_setting
        effective_setting = {**parameter.strategy_setting, **task.strategy_setting}
        engine.add_strategy(task.strategy_class, effective_setting)

        if bars is not None:
            # CSV inject mode.
            # BacktestingEngine.run_backtesting() does NOT filter history_data by
            # the configured start/end range — it replays everything in the list.
            # We must slice to [effective_start, effective_end] here so that
            # task-level date overrides actually take effect.
            end_inclusive = effective_end.replace(hour=23, minute=59, second=59)
            engine.history_data = [
                b for b in bars
                if effective_start
                <= b.datetime.replace(tzinfo=None)
                <= end_inclusive
            ]
        else:
            engine.load_data()

        if not engine.history_data:
            return {}

        engine.run_backtesting()
        engine.calculate_result()
        stats: dict = engine.calculate_statistics(output=False)
        return stats
