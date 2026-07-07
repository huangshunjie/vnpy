"""patch_exp_stats.py — 扩展 ExperimentEngine.stats()"""
import pathlib

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\research_ops\engine\experiment_engine.py"
)
src = P.read_text(encoding="utf-8")

OLD = "    def stats(self) -> dict:\n        return {\n            \"experiments\": self._exp_repo.count(),\n            \"runs\":        self._run_repo.count(),\n        }"

NEW = """    def stats(self) -> dict:
        from ..constant import RunStatus, ExperimentStatus
        runs = self._run_repo.list()
        exps = self._exp_repo.list()
        return {
            "experiments":    len(exps),
            "runs":           len(runs),
            "running":        sum(1 for r in runs if r.status == RunStatus.RUNNING),
            "completed":      sum(1 for r in runs if r.status == RunStatus.COMPLETED),
            "failed":         sum(1 for r in runs if r.status == RunStatus.FAILED),
            "pending":        sum(1 for r in runs if r.status == RunStatus.PENDING),
            "exp_running":    sum(1 for e in exps if e.status == ExperimentStatus.RUNNING),
            "exp_completed":  sum(1 for e in exps if e.status == ExperimentStatus.COMPLETED),
        }"""

assert OLD in src, "pattern not found"
src = src.replace(OLD, NEW)
P.write_text(src, encoding="utf-8")
print("stats() patched OK")

# verify
import importlib, sys
for mod in list(sys.modules.keys()):
    if "research_ops" in mod:
        del sys.modules[mod]

from vnpy.research_ops.engine.experiment_engine import ExperimentEngine
from vnpy.research_ops.constant import RunStatus
ee = ExperimentEngine()
exp = ee.create_experiment("t", primary_metric="sharpe")
run = ee.start_run(exp.experiment_id, params={})
ee.complete_run(run.run_id, metrics={"sharpe": 1.5})
s = ee.stats()
assert s["completed"] == 1
assert s["running"] == 0
assert s["failed"] == 0
print("stats() verify:", s)
