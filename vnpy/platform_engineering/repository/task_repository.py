"""
platform_engineering/repository/task_repository.py
任务与 Worker 内存存储。
"""
from __future__ import annotations
from typing import Dict, List, Optional
from ..model.task import TaskRecord, WorkerRecord
from ..constant import TaskStatus


class TaskRepository:
    def __init__(self) -> None:
        self._tasks:   Dict[str, TaskRecord]   = {}
        self._workers: Dict[str, WorkerRecord] = {}

    # ── tasks ─────────────────────────────────────────────────────
    def save(self, task: TaskRecord) -> None:
        self._tasks[task.task_id] = task

    def get(self, task_id: str) -> Optional[TaskRecord]:
        return self._tasks.get(task_id)

    def list(self, status: Optional[TaskStatus] = None) -> List[TaskRecord]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def delete(self, task_id: str) -> None:
        self._tasks.pop(task_id, None)

    def search(self, keyword: str) -> List[TaskRecord]:
        kw = keyword.lower()
        return [t for t in self._tasks.values()
                if kw in t.name.lower()
                or kw in t.task_type.value
                or any(kw in tag for tag in t.tags)]

    # ── workers ───────────────────────────────────────────────────
    def save_worker(self, worker: WorkerRecord) -> None:
        self._workers[worker.worker_id] = worker

    def get_worker(self, worker_id: str) -> Optional[WorkerRecord]:
        return self._workers.get(worker_id)

    def list_workers(self) -> List[WorkerRecord]:
        return list(self._workers.values())

    def delete_worker(self, worker_id: str) -> None:
        self._workers.pop(worker_id, None)

    def stats(self) -> dict:
        tasks   = list(self._tasks.values())
        workers = list(self._workers.values())
        from ..constant import WorkerStatus
        return {
            "total":     len(tasks),
            "pending":   sum(1 for t in tasks if t.status == TaskStatus.PENDING),
            "running":   sum(1 for t in tasks if t.status == TaskStatus.RUNNING),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "failed":    sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            "workers":   len(workers),
            "idle_workers": sum(1 for w in workers
                               if w.status == WorkerStatus.IDLE),
        }
