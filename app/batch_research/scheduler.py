"""
Scheduler

Task scheduler for batch backtesting.

Phase 5: Serial (single-threaded) SerialScheduler.
Phase 8: ProcessPoolScheduler — multi-process, drop-in replacement.

Design:
  - SchedulerBase        abstract interface
  - SerialScheduler      Phase 5, single-threaded, always safe
  - ProcessPoolScheduler Phase 8, concurrent.futures.ProcessPoolExecutor
  - Scheduler            alias (default SerialScheduler)
  - ScheduleJob          bundles BacktestTask + optional pre-loaded bars
  - RunSummary           aggregate statistics after a completed run
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from .parameter import BacktestParameter
from .task import BacktestResult, BacktestTask, TaskStatus
from .worker import Worker
from .utils.logger import get_logger
from .utils.progress import ProgressBar
from .utils.timer import Timer

logger = get_logger()


# ------------------------------------------------------------------ #
#  ScheduleJob
# ------------------------------------------------------------------ #

@dataclass
class ScheduleJob:
    """
    Unit of work submitted to the Scheduler.

    bars=None  -> Worker calls BacktestingEngine.load_data() (DB mode)
    bars=[...] -> Worker injects directly, bypassing load_data() (CSV mode)
    """
    task: BacktestTask
    bars: list | None = None

    def __post_init__(self) -> None:
        if not self.task.task_id:
            self.task.task_id = str(uuid.uuid4())[:8]


# ------------------------------------------------------------------ #
#  SchedulerBase
# ------------------------------------------------------------------ #

class SchedulerBase(ABC):
    """Abstract interface shared by SerialScheduler and ProcessPoolScheduler."""

    @abstractmethod
    def submit(self, jobs: list[ScheduleJob]) -> None:
        """Append jobs to the internal queue. May be called multiple times."""

    @abstractmethod
    def run(
        self,
        parameter: BacktestParameter,
        *,
        on_task_start: Callable[[BacktestTask], None] | None = None,
        on_task_done: Callable[[BacktestResult], None] | None = None,
        show_progress: bool = True,
    ) -> list[BacktestResult]:
        """Execute all submitted jobs; return results in submission order."""

    @abstractmethod
    def clear(self) -> None:
        """Reset job queue so the scheduler can be reused."""


# ------------------------------------------------------------------ #
#  RunSummary
# ------------------------------------------------------------------ #

@dataclass
class RunSummary:
    """Aggregate statistics attached to a scheduler after run() completes."""
    total: int = 0
    success: int = 0
    skipped: int = 0
    failed: int = 0
    elapsed_seconds: float = 0.0
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def success_rate(self) -> float:
        return self.success / self.total * 100 if self.total else 0.0

    def __str__(self) -> str:
        return (
            f"RunSummary("
            f"total={self.total}, "
            f"success={self.success}, "
            f"skipped={self.skipped}, "
            f"failed={self.failed}, "
            f"success_rate={self.success_rate:.1f}%, "
            f"elapsed={self.elapsed_seconds:.2f}s)"
        )


# ------------------------------------------------------------------ #
#  SerialScheduler  (Phase 5)
# ------------------------------------------------------------------ #

class SerialScheduler(SchedulerBase):
    """
    Single-threaded serial scheduler. Processes jobs one at a time.
    Simple, predictable, always safe — the correct default.
    """

    def __init__(self) -> None:
        self._jobs: list[ScheduleJob] = []
        self._worker: Worker = Worker()
        self.summary: RunSummary = RunSummary()

    def submit(self, jobs: list[ScheduleJob]) -> None:
        self._jobs.extend(jobs)
        logger.debug("SerialScheduler: %d jobs queued (total %d)",
                     len(jobs), len(self._jobs))

    def run(
        self,
        parameter: BacktestParameter,
        *,
        on_task_start: Callable[[BacktestTask], None] | None = None,
        on_task_done: Callable[[BacktestResult], None] | None = None,
        show_progress: bool = True,
    ) -> list[BacktestResult]:
        if not self._jobs:
            logger.warning("Scheduler.run() called with empty job queue")
            return []

        total = len(self._jobs)
        results: list[BacktestResult] = []
        summary = RunSummary(total=total, start_time=datetime.now())
        wall_timer = Timer()
        wall_timer.start()

        bar = ProgressBar(total=total, label="Backtesting") if show_progress else None
        logger.info("SerialScheduler starting: %d jobs", total)

        for idx, job in enumerate(self._jobs):
            task = job.task
            task.status = TaskStatus.RUNNING

            if on_task_start:
                try:
                    on_task_start(task)
                except Exception:
                    pass

            result = self._worker.run(
                task=task, parameter=parameter,
                bars=job.bars, suppress_output=True,
            )

            task.status = result.status
            results.append(result)

            if result.status == TaskStatus.SUCCESS:
                summary.success += 1
            elif result.status == TaskStatus.SKIPPED:
                summary.skipped += 1
            else:
                summary.failed += 1

            if on_task_done:
                try:
                    on_task_done(result)
                except Exception:
                    pass

            if bar:
                bar.update(idx + 1,
                           suffix=f"{task.vt_symbol} [{result.status.value}]")

            logger.debug("[%d/%d] %s  status=%s  elapsed=%.3fs",
                         idx + 1, total, task.vt_symbol,
                         result.status.value, result.elapsed_seconds or 0)

        if bar:
            bar.finish()

        wall_timer.stop()
        summary.elapsed_seconds = wall_timer.elapsed
        summary.end_time = datetime.now()
        self.summary = summary
        logger.info("SerialScheduler done: %s", summary)
        return results

    def clear(self) -> None:
        self._jobs.clear()
        logger.debug("SerialScheduler: job queue cleared")

    @property
    def job_count(self) -> int:
        return len(self._jobs)

    def __repr__(self) -> str:
        return f"SerialScheduler(jobs={self.job_count})"



# ------------------------------------------------------------------ #
#  Module-level worker function — must be top-level for pickle/spawn
# ------------------------------------------------------------------ #

def _process_worker_fn(
    job_tuple: tuple,
    parameter: BacktestParameter,
) -> BacktestResult:
    """
    Executed in each worker process.

    Top-level so Python's 'spawn' start method (Windows) can pickle
    and re-import it in the child process.
    """
    task, bars = job_tuple
    return Worker().run(task=task, parameter=parameter,
                        bars=bars, suppress_output=True)


# ------------------------------------------------------------------ #
#  ProcessPoolScheduler  (Phase 8)
# ------------------------------------------------------------------ #

class ProcessPoolScheduler(SchedulerBase):
    """
    Multi-process scheduler using concurrent.futures.ProcessPoolExecutor.

    Drop-in replacement for SerialScheduler — same interface, results
    returned in submission order regardless of completion order.

    Best for large stock pools (300+ symbols) where CPU is the bottleneck.
    Each symbol runs in an isolated subprocess; a crash in one worker
    does not affect the others.

    Windows constraints:
      - Uses 'spawn' multiprocessing; all objects sent to workers must
        be picklable at module level (standard vnpy classes satisfy this).
      - Script entry points MUST be guarded with:
            if __name__ == '__main__':
                engine.run_backtesting()

    Performance guidelines:
      - max_workers=4 is safe on most developer machines
      - max_workers=cpu_count()-1 keeps one core for the UI/OS
      - For very short backtests (<0.1s each), SerialScheduler is faster
        due to process-spawn overhead (~0.5s/worker on Windows)

    Usage::

        engine = BatchBacktestingEngine(
            scheduler=ProcessPoolScheduler(max_workers=4)
        )
        engine.set_parameters(...)
        engine.set_stock_pool([...])

        if __name__ == '__main__':
            engine.run_backtesting()
    """

    def __init__(self, max_workers: int | None = None) -> None:
        """
        :param max_workers: Worker process count.
                            None (default) -> os.cpu_count().
        """
        import os
        self._max_workers: int = max_workers or max(1, (os.cpu_count() or 1))
        self._jobs: list[ScheduleJob] = []
        self.summary: RunSummary = RunSummary()

    def submit(self, jobs: list[ScheduleJob]) -> None:
        self._jobs.extend(jobs)
        logger.debug("ProcessPoolScheduler: %d jobs queued (total %d)",
                     len(jobs), len(self._jobs))

    def run(
        self,
        parameter: BacktestParameter,
        *,
        on_task_start: Callable[[BacktestTask], None] | None = None,
        on_task_done: Callable[[BacktestResult], None] | None = None,
        show_progress: bool = True,
    ) -> list[BacktestResult]:
        """
        Execute all queued jobs in a process pool.

        Results are in submission order. Both callbacks run in the main
        process — never sent to worker processes.

        on_task_start fires at submission time (before the worker starts).
        on_task_done  fires when the future resolves (completion order).
        """
        from concurrent.futures import ProcessPoolExecutor, as_completed  # noqa

        if not self._jobs:
            logger.warning("ProcessPoolScheduler.run() called with empty queue")
            return []

        total = len(self._jobs)
        summary = RunSummary(total=total, start_time=datetime.now())
        wall_timer = Timer()
        wall_timer.start()

        bar = ProgressBar(total=total, label="Backtesting") if show_progress else None
        logger.info("ProcessPoolScheduler starting: %d jobs, %d workers",
                    total, self._max_workers)

        # Fire on_task_start in main process before dispatching
        for job in self._jobs:
            job.task.status = TaskStatus.RUNNING
            if on_task_start:
                try:
                    on_task_start(job.task)
                except Exception:
                    pass

        # (task, bars) tuples — plain data, no closures, pickle-safe
        job_tuples = [(job.task, job.bars) for job in self._jobs]

        # Submission-order result slots; futures complete in any order
        results: list[BacktestResult | None] = [None] * total
        future_to_idx: dict = {}

        with ProcessPoolExecutor(max_workers=self._max_workers) as executor:
            for idx, jt in enumerate(job_tuples):
                f = executor.submit(_process_worker_fn, jt, parameter)
                future_to_idx[f] = idx

            completed = 0
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                task = self._jobs[idx].task

                try:
                    result: BacktestResult = future.result()
                except Exception as exc:
                    result = BacktestResult(
                        vt_symbol=task.vt_symbol,
                        task_id=task.task_id,
                        strategy_name=task.strategy_class.__name__,
                        status=TaskStatus.FAILED,
                        error_msg=f"ProcessPool executor error: {exc}",
                    )

                results[idx] = result
                task.status = result.status

                if result.status == TaskStatus.SUCCESS:
                    summary.success += 1
                elif result.status == TaskStatus.SKIPPED:
                    summary.skipped += 1
                else:
                    summary.failed += 1

                if on_task_done:
                    try:
                        on_task_done(result)
                    except Exception:
                        pass

                completed += 1
                if bar:
                    bar.update(completed,
                               suffix=f"{task.vt_symbol} [{result.status.value}]")

                logger.debug("[%d/%d] %s  status=%s  elapsed=%.3fs",
                             completed, total, task.vt_symbol,
                             result.status.value, result.elapsed_seconds or 0)

        if bar:
            bar.finish()

        wall_timer.stop()
        summary.elapsed_seconds = wall_timer.elapsed
        summary.end_time = datetime.now()
        self.summary = summary
        logger.info("ProcessPoolScheduler done: %s", summary)

        return [r for r in results if r is not None]

    def clear(self) -> None:
        self._jobs.clear()
        logger.debug("ProcessPoolScheduler: job queue cleared")

    @property
    def job_count(self) -> int:
        return len(self._jobs)

    def __repr__(self) -> str:
        return (f"ProcessPoolScheduler("
                f"jobs={self.job_count}, "
                f"max_workers={self._max_workers})")


# ------------------------------------------------------------------ #
#  Default alias  (swap to ProcessPoolScheduler for parallel runs)
# ------------------------------------------------------------------ #

Scheduler = SerialScheduler

