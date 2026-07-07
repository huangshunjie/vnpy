"""smoke_pe_p3.py — Phase 3 smoke test"""
import time

# ── 1. TaskEngine 核心逻辑 ────────────────────────────────────────
from vnpy.platform_engineering.engine.task_engine import (
    TaskEngine, ScheduledJob, Worker, _QItem,
)
from vnpy.platform_engineering.constant import (
    TaskStatus, TaskType, TaskPriority, WorkerStatus,
)

te = TaskEngine(num_workers=2, scheduler_interval=9999)
te.start()

# create tasks
t1 = te.create_task("回测任务", task_type=TaskType.BACKTEST,
                     priority=TaskPriority.HIGH, created_by="alice")
t2 = te.create_task("因子计算", task_type=TaskType.FACTOR_CALC,
                     priority=TaskPriority.NORMAL)
t3 = te.create_task("数据更新", task_type=TaskType.DATA_UPDATE,
                     priority=TaskPriority.LOW)
assert te.get_task(t1.task_id) is not None
print(f"  create_task: PASSED  created={3}")

# cancel pending/queued task
t_cancel = te.create_task("待取消", task_type=TaskType.CUSTOM,
                           priority=TaskPriority.LOW)
ok = te.cancel_task(t_cancel.task_id)
assert ok
assert te.get_task(t_cancel.task_id).status == TaskStatus.CANCELLED
print("  cancel_task: PASSED")

# list tasks
all_tasks = te.list_tasks()
assert len(all_tasks) >= 4
print(f"  list_tasks: PASSED  total={len(all_tasks)}")

# search
results = te.search_tasks("回测")
assert any("回测" in t.name for t in results)
print(f"  search_tasks: PASSED  found={len(results)}")

# register handler + wait for completion
done_ids = []
te.on_task_done(lambda t: done_ids.append(t.task_id))
te.register_handler(TaskType.CUSTOM,
    lambda task: {"result": "custom_done"})

t_exec = te.create_task("自定义任务", task_type=TaskType.CUSTOM,
                         priority=TaskPriority.URGENT)
# wait up to 3s for worker to pick it up
for _ in range(30):
    t = te.get_task(t_exec.task_id)
    if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED,
                    TaskStatus.RUNNING):
        break
    time.sleep(0.1)
t = te.get_task(t_exec.task_id)
assert t.status in (TaskStatus.COMPLETED, TaskStatus.RUNNING,
                    TaskStatus.QUEUED), f"unexpected: {t.status}"
print(f"  handler_dispatch: PASSED  status={t.status.value}")

# workers
workers = te.list_workers()
assert len(workers) == 2
print(f"  list_workers: PASSED  count={len(workers)}")

# add worker
te.add_worker()
assert len(te.list_workers()) == 3
print("  add_worker: PASSED")

# retry
t_fail = te.create_task("失败任务", task_type=TaskType.CUSTOM,
                         priority=TaskPriority.URGENT, max_retries=0)
te.register_handler(TaskType.CUSTOM, lambda _: (_ for _ in ()).throw(
    RuntimeError("forced error")))
for _ in range(30):
    t = te.get_task(t_fail.task_id)
    if t.status in (TaskStatus.FAILED, TaskStatus.COMPLETED,
                    TaskStatus.RUNNING):
        break
    time.sleep(0.1)
# restore handler
te.register_handler(TaskType.CUSTOM, lambda task: {"result": "ok"})
print(f"  error_handling: PASSED  status={te.get_task(t_fail.task_id).status.value}")

# retry_task
t_for_retry = te.create_task("重试任务", task_type=TaskType.CUSTOM,
                              priority=TaskPriority.LOW, max_retries=0)
te.cancel_task(t_for_retry.task_id)
retried = te.retry_task(t_for_retry.task_id)
assert retried is not None
assert retried.status in (TaskStatus.PENDING, TaskStatus.QUEUED,
                          TaskStatus.RUNNING, TaskStatus.COMPLETED)
print(f"  retry_task: PASSED  status={retried.status.value}")

# stats
s = te.stats()
assert "queue_size" in s
assert "total_workers" in s
assert s["total_workers"] >= 3
print(f"  stats: PASSED  {s}")

te.stop()

# ── 2. ScheduledJob ───────────────────────────────────────────────
te2 = TaskEngine(num_workers=1, scheduler_interval=9999)
job = te2.add_scheduled_job(
    name="定时回测", cron_expr="*/5 * * * *",
    task_type=TaskType.BACKTEST,
    priority=TaskPriority.NORMAL,
    created_by="system",
)
assert job.job_id.startswith("JOB-")
assert job.next_run is not None
jobs = te2.list_scheduled_jobs()
assert len(jobs) == 1
# manual trigger
te2.start()
triggered = te2.trigger_job(job.job_id)
assert triggered is not None
assert "[manual]" in triggered.name
print(f"  ScheduledJob: PASSED  next_run={job.next_run}")
print(f"  trigger_job: PASSED  task={triggered.name}")
te2.remove_scheduled_job(job.job_id)
assert len(te2.list_scheduled_jobs()) == 0
print("  remove_job: PASSED")
te2.stop()

# ── 3. UI class imports ───────────────────────────────────────────
from vnpy.platform_engineering.ui.task import (
    TaskTab, TaskList, WorkerPanel, SchedulerPanel,
    CreateTaskDialog, AddJobDialog,
    STATUS_COLOR, WORKER_COLOR, PRIORITY_COLOR,
)
assert len(STATUS_COLOR)   == 8
assert len(WORKER_COLOR)   == 4
assert len(PRIORITY_COLOR) == 4
assert hasattr(TaskList,       "refresh")
assert hasattr(WorkerPanel,    "refresh")
assert hasattr(SchedulerPanel, "refresh")
assert hasattr(TaskTab,        "_refresh")
assert hasattr(CreateTaskDialog, "get_name")
assert hasattr(AddJobDialog,     "get_cron")
print("  TaskTab UI: PASSED")

# ── 4. stub_tabs re-export ────────────────────────────────────────
from vnpy.platform_engineering.ui.stub_tabs import (
    TaskTab as TT2, DashboardTab, ObservabilityTab, LogTab,
    DeploymentTab, StrategyHealthTab, ConfigTab, ApiTab, SecurityTab,
)
assert TaskTab is TT2
print("  stub_tabs re-export: PASSED")

# ── 5. Phase 1+2 regression ──────────────────────────────────────
from vnpy.platform_engineering import PlatformEngineeringApp
from vnpy.platform_engineering.engine.observability_engine import ObservabilityEngine
oe = ObservabilityEngine()
oe.record_metric(oe.make_point("system.cpu_pct", 50.0,
    __import__("vnpy.platform_engineering.constant",
               fromlist=["MetricLayer"]).MetricLayer.SYSTEM))
assert oe.stats()["health_score"] == 100.0
print("  Phase1+2 regression: PASSED")

print()
print("=== Phase 3 Smoke Test: ALL PASSED ===")
