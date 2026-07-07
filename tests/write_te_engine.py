"""write_te_engine.py — append TaskEngine main class to task_engine.py"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\engine\task_engine.py"
)

ENGINE = '''

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
'''

ast.parse(ENGINE)
with open(P, "a", encoding="utf-8") as f:
    f.write(ENGINE)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("TaskEngine OK, total lines:", len(full.splitlines()), "size:", P.stat().st_size)
