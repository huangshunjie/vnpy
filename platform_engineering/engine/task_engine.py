"""
platform_engineering/engine/task_engine.py
TaskEngine 完整版 — Phase 3
优先级队列 + WorkerPool + TaskScheduler + 重试 + 超时
"""
from __future__ import annotations

import queue
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from ..model.task import TaskRecord, WorkerRecord
from ..repository.task_repository import TaskRepository
from ..constant import TaskStatus, TaskType, TaskPriority, WorkerStatus
from ..utils.scheduler_utils import next_run_from_cron


class _QItem:
    """Priority-queue wrapper: higher priority.value → lower sort key."""
    __slots__ = ("priority_val", "created_ts", "task_id")

    def __init__(self, task: TaskRecord) -> None:
        self.priority_val = -task.priority.value
        self.created_ts   = task.created_at.timestamp()
        self.task_id      = task.task_id

    def __lt__(self, other: "_QItem") -> bool:
        if self.priority_val != other.priority_val:
            return self.priority_val < other.priority_val
        return self.created_ts < other.created_ts


class ScheduledJob:
    def __init__(
        self,
        job_id:       str,
        name:         str,
        cron_expr:    str,
        task_type:    TaskType,
        params:       dict,
        priority:     TaskPriority = TaskPriority.NORMAL,
        max_retries:  int = 3,
        timeout_secs: int = 3600,
        created_by:   str = "",
        enabled:      bool = True,
    ) -> None:
        self.job_id       = job_id
        self.name         = name
        self.cron_expr    = cron_expr
        self.task_type    = task_type
        self.params       = params
        self.priority     = priority
        self.max_retries  = max_retries
        self.timeout_secs = timeout_secs
        self.created_by   = created_by
        self.enabled      = enabled
        self.next_run:    Optional[datetime] = None
        self.last_run:    Optional[datetime] = None
        self.run_count:   int = 0
        self._calc_next()

    def _calc_next(self, after: Optional[datetime] = None) -> None:
        self.next_run = next_run_from_cron(self.cron_expr, after)

    def is_due(self) -> bool:
        return (self.enabled and self.next_run is not None
                and datetime.now() >= self.next_run)

    def mark_fired(self) -> None:
        self.last_run   = datetime.now()
        self.run_count += 1
        self._calc_next(after=self.last_run)


class Worker:
    def __init__(
        self,
        worker_id:  str,
        name:       str,
        task_queue: "queue.PriorityQueue[_QItem]",
        handler:    Callable[[TaskRecord], Any],
        repo:       TaskRepository,
        on_done:    Callable[[TaskRecord], None],
    ) -> None:
        self.record = WorkerRecord(
            worker_id=worker_id, name=name,
            status=WorkerStatus.IDLE,
            registered_at=datetime.now(),
            last_heartbeat=datetime.now(),
        )
        self._queue   = task_queue
        self._handler = handler
        self._repo    = repo
        self._on_done = on_done
        self._stop    = threading.Event()
        self._thread  = threading.Thread(
            target=self._loop, name=name, daemon=True)

    def start(self)    -> None: self._thread.start()
    def stop(self)     -> None: self._stop.set()
    def is_alive(self) -> bool: return self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=1.0)
            except queue.Empty:
                self.record.last_heartbeat = datetime.now()
                continue
            task = self._repo.get(item.task_id)
            if task is None or task.status == TaskStatus.CANCELLED:
                self._queue.task_done()
                continue
            self._run_task(task)
            self._queue.task_done()
        self.record.status = WorkerStatus.OFFLINE

    def _run_task(self, task: TaskRecord) -> None:
        self.record.status       = WorkerStatus.BUSY
        self.record.current_task = task.task_id
        self.record.task_count  += 1
        self.record.last_heartbeat = datetime.now()

        task.status     = TaskStatus.RUNNING
        task.worker_id  = self.record.worker_id
        task.started_at = datetime.now()
        task.updated_at = datetime.now()
        self._repo.save(task)

        deadline = task.started_at + timedelta(seconds=task.timeout_secs)
        try:
            result = self._handler(task)
            if datetime.now() > deadline:
                raise TimeoutError(f"exceeded {task.timeout_secs}s")
            task.result   = result
            task.status   = TaskStatus.COMPLETED
            task.progress = 1.0
        except TimeoutError as e:
            task.status    = TaskStatus.TIMEOUT
            task.error_msg = str(e)
            self.record.error_count += 1
        except Exception as e:
            task.error_msg = str(e)
            if task.retries < task.max_retries:
                task.retries += 1
                task.status   = TaskStatus.RETRYING
            else:
                task.status = TaskStatus.FAILED
                self.record.error_count += 1

        task.finished_at = datetime.now()
        task.updated_at  = datetime.now()
        self._repo.save(task)
        self.record.status       = WorkerStatus.IDLE
        self.record.current_task = ""
        self.record.last_heartbeat = datetime.now()
        self._on_done(task)


class TaskEngine:
    """
    完整任务执行引擎。
    优先级队列(URGENT>HIGH>NORMAL>LOW) + WorkerPool + Cron Scheduler
    支持可插拔任务处理函数、自动重试、超时检测、任务完成回调。
    """

    def __init__(
        self,
        num_workers:        int = 4,
        scheduler_interval: int = 30,
    ) -> None:
        self._repo        = TaskRepository()
        self._queue: queue.PriorityQueue[_QItem] = queue.PriorityQueue()
        self._workers:  Dict[str, Worker]         = {}
        self._handlers: Dict[TaskType, Callable]  = {}
        self._jobs:     Dict[str, ScheduledJob]   = {}
        self._num_workers       = num_workers
        self._sched_interval    = scheduler_interval
        self._sched_thread:     Optional[threading.Thread] = None
        self._stop_sched        = threading.Event()
        self._callbacks:        List[Callable[[TaskRecord], None]] = []
        self._started           = False

    # ── lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        if self._started:
            return
        for i in range(self._num_workers):
            self._add_worker(f"Worker-{i+1:02d}")
        self._stop_sched.clear()
        self._sched_thread = threading.Thread(
            target=self._scheduler_loop, name="TaskScheduler", daemon=True)
        self._sched_thread.start()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self._stop_sched.set()
        for w in self._workers.values():
            w.stop()
        self._started = False

    # ── handler & callback ────────────────────────────────────────

    def register_handler(
        self, task_type: TaskType, handler: Callable[[TaskRecord], Any]
    ) -> None:
        self._handlers[task_type] = handler

    def on_task_done(self, cb: Callable[[TaskRecord], None]) -> None:
        self._callbacks.append(cb)

    # ── task CRUD ─────────────────────────────────────────────────

    def create_task(
        self,
        name:         str,
        task_type:    TaskType     = TaskType.CUSTOM,
        priority:     TaskPriority = TaskPriority.NORMAL,
        params:       dict         = None,
        max_retries:  int          = 3,
        timeout_secs: int          = 3600,
        tags:         List[str]    = None,
        created_by:   str          = "",
        scheduled_at: Optional[datetime] = None,
    ) -> TaskRecord:
        task = TaskRecord(
            task_id      = "TSK-" + uuid.uuid4().hex[:8].upper(),
            name         = name,
            task_type    = task_type,
            priority     = priority,
            status       = TaskStatus.PENDING,
            params       = params or {},
            max_retries  = max_retries,
            timeout_secs = timeout_secs,
            tags         = tags or [],
            created_by   = created_by,
            scheduled_at = scheduled_at,
            created_at   = datetime.now(),
            updated_at   = datetime.now(),
        )
        self._repo.save(task)
        if scheduled_at is None or scheduled_at <= datetime.now():
            self._enqueue(task)
        return task

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self._repo.get(task_id)

    def list_tasks(
        self,
        status:    Optional[TaskStatus] = None,
        task_type: Optional[TaskType]   = None,
    ) -> List[TaskRecord]:
        tasks = self._repo.list(status=status)
        if task_type:
            tasks = [t for t in tasks if t.task_type == task_type]
        return tasks

    def search_tasks(self, keyword: str) -> List[TaskRecord]:
        return self._repo.search(keyword)

    def cancel_task(self, task_id: str) -> bool:
        task = self._repo.get(task_id)
        if not task:
            return False
        if task.status in (TaskStatus.PENDING, TaskStatus.QUEUED,
                           TaskStatus.RETRYING):
            task.status      = TaskStatus.CANCELLED
            task.finished_at = datetime.now()
            task.updated_at  = datetime.now()
            self._repo.save(task)
            return True
        return False

    def retry_task(self, task_id: str) -> Optional[TaskRecord]:
        task = self._repo.get(task_id)
        if not task:
            return None
        if task.status in (TaskStatus.FAILED, TaskStatus.TIMEOUT,
                           TaskStatus.CANCELLED):
            task.status      = TaskStatus.PENDING
            task.error_msg   = ""
            task.retries     = 0
            task.started_at  = None
            task.finished_at = None
            task.updated_at  = datetime.now()
            self._repo.save(task)
            self._enqueue(task)
        return task

    # ── workers ───────────────────────────────────────────────────

    def list_workers(self) -> List[WorkerRecord]:
        return [w.record for w in self._workers.values()]

    def add_worker(self) -> str:
        idx = len(self._workers) + 1
        return self._add_worker(f"Worker-{idx:02d}")

    def _add_worker(self, name: str) -> str:
        wid = "WRK-" + uuid.uuid4().hex[:6].upper()
        w   = Worker(
            worker_id  = wid,
            name       = name,
            task_queue = self._queue,
            handler    = self._dispatch,
            repo       = self._repo,
            on_done    = self._on_task_done,
        )
        self._workers[wid] = w
        self._repo.save_worker(w.record)
        w.start()
        return wid

    def _dispatch(self, task: TaskRecord) -> Any:
        handler = self._handlers.get(task.task_type)
        if handler:
            return handler(task)
        return {"status": "no_handler", "task_id": task.task_id}

    def _on_task_done(self, task: TaskRecord) -> None:
        if task.status == TaskStatus.RETRYING:
            task.status     = TaskStatus.PENDING
            task.updated_at = datetime.now()
            self._repo.save(task)
            self._enqueue(task)
        for cb in self._callbacks:
            try:
                cb(task)
            except Exception:
                pass

    # ── queue ─────────────────────────────────────────────────────

    def _enqueue(self, task: TaskRecord) -> None:
        task.status     = TaskStatus.QUEUED
        task.updated_at = datetime.now()
        self._repo.save(task)
        self._queue.put(_QItem(task))

    # ── scheduler ─────────────────────────────────────────────────

    def add_scheduled_job(
        self,
        name:         str,
        cron_expr:    str,
        task_type:    TaskType,
        params:       dict         = None,
        priority:     TaskPriority = TaskPriority.NORMAL,
        max_retries:  int          = 3,
        timeout_secs: int          = 3600,
        created_by:   str          = "",
    ) -> ScheduledJob:
        job = ScheduledJob(
            job_id       = "JOB-" + uuid.uuid4().hex[:8].upper(),
            name         = name,
            cron_expr    = cron_expr,
            task_type    = task_type,
            params       = params or {},
            priority     = priority,
            max_retries  = max_retries,
            timeout_secs = timeout_secs,
            created_by   = created_by,
        )
        self._jobs[job.job_id] = job
        return job

    def remove_scheduled_job(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)

    def list_scheduled_jobs(self) -> List[ScheduledJob]:
        return list(self._jobs.values())

    def trigger_job(self, job_id: str) -> Optional[TaskRecord]:
        job = self._jobs.get(job_id)
        if not job:
            return None
        return self.create_task(
            name         = job.name + " [manual]",
            task_type    = job.task_type,
            priority     = job.priority,
            params       = job.params,
            max_retries  = job.max_retries,
            timeout_secs = job.timeout_secs,
            created_by   = job.created_by,
        )

    def _scheduler_loop(self) -> None:
        while not self._stop_sched.is_set():
            for job in list(self._jobs.values()):
                if job.is_due():
                    self.create_task(
                        name         = job.name,
                        task_type    = job.task_type,
                        priority     = job.priority,
                        params       = job.params,
                        max_retries  = job.max_retries,
                        timeout_secs = job.timeout_secs,
                        created_by   = job.created_by,
                    )
                    job.mark_fired()
            self._stop_sched.wait(self._sched_interval)

    # ── stats ─────────────────────────────────────────────────────

    def stats(self) -> dict:
        base = self._repo.stats()
        base["queue_size"]     = self._queue.qsize()
        base["scheduled_jobs"] = len(self._jobs)
        base["busy_workers"]   = sum(
            1 for w in self._workers.values()
            if w.record.status == WorkerStatus.BUSY)
        base["total_workers"]  = len(self._workers)
        return base
