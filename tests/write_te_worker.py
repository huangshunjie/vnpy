"""write_te_worker.py — append Worker + TaskEngine to task_engine.py"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\engine\task_engine.py"
)

WORKER = '''

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
'''

ast.parse(WORKER)
with open(P, "a", encoding="utf-8") as f:
    f.write(WORKER)
full = P.read_text(encoding="utf-8")
ast.parse(full)
print("Worker appended OK, lines:", len(full.splitlines()))
