"""
platform_engineering/engine/metric_collector.py
MetricCollector — Phase 2
定时轮询系统资源 + 各子系统适配器，推送指标到 ObservabilityEngine。
"""
from __future__ import annotations
import threading
import time
from datetime import datetime
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

from ..constant import MetricLayer, MetricType
from ..model.metric import MetricPoint
from ..utils.monitor_utils import get_system_metrics

if TYPE_CHECKING:
    from .observability_engine import ObservabilityEngine


class CollectorAdapter:
    """单个采集适配器基类。"""

    name:  str = "base"
    layer: MetricLayer = MetricLayer.SYSTEM

    def collect(self) -> List[MetricPoint]:
        return []


class SystemAdapter(CollectorAdapter):
    """系统层：CPU / 内存 / 磁盘。"""

    name  = "system"
    layer = MetricLayer.SYSTEM

    def collect(self) -> List[MetricPoint]:
        raw = get_system_metrics()
        now = datetime.now()
        points = []
        for key, val in raw.items():
            metric_name = f"system.{key}"
            points.append(MetricPoint(
                metric_id   = metric_name + "." + str(int(now.timestamp())),
                name        = metric_name,
                layer       = self.layer,
                metric_type = MetricType.GAUGE,
                value       = val,
                unit        = "%",
                source      = "system",
                timestamp   = now,
            ))
        return points


class TaskMetricsAdapter(CollectorAdapter):
    """系统层：任务引擎运行状态。"""

    name  = "task_metrics"
    layer = MetricLayer.SYSTEM

    def __init__(self, task_engine) -> None:
        self._te = task_engine

    def collect(self) -> List[MetricPoint]:
        s   = self._te.stats()
        now = datetime.now()
        mapping = {
            "system.task_running":   ("running", ""),
            "system.task_pending":   ("pending", ""),
            "system.task_failed":    ("failed",  ""),
            "system.workers_idle":   ("idle_workers", ""),
        }
        points = []
        for metric_name, (key, unit) in mapping.items():
            points.append(MetricPoint(
                metric_id   = metric_name + "." + str(int(now.timestamp())),
                name        = metric_name,
                layer       = self.layer,
                metric_type = MetricType.GAUGE,
                value       = float(s.get(key, 0)),
                unit        = unit,
                source      = "task_engine",
                timestamp   = now,
            ))
        return points


class DeploymentMetricsAdapter(CollectorAdapter):
    """策略层：部署状态快照。"""

    name  = "deployment_metrics"
    layer = MetricLayer.STRATEGY

    def __init__(self, deployment_engine) -> None:
        self._de = deployment_engine

    def collect(self) -> List[MetricPoint]:
        s   = self._de.stats()
        now = datetime.now()
        by_stage = s.get("by_stage", {})
        points = []
        for stage_val, count in by_stage.items():
            points.append(MetricPoint(
                metric_id   = f"strategy.deploy_{stage_val}.{int(now.timestamp())}",
                name        = f"strategy.deploy_{stage_val}",
                layer       = self.layer,
                metric_type = MetricType.GAUGE,
                value       = float(count),
                unit        = "",
                source      = "deployment_engine",
                timestamp   = now,
            ))
        points.append(MetricPoint(
            metric_id   = f"strategy.deploy_total.{int(now.timestamp())}",
            name        = "strategy.deploy_total",
            layer       = self.layer,
            metric_type = MetricType.GAUGE,
            value       = float(s.get("total", 0)),
            unit        = "",
            source      = "deployment_engine",
            timestamp   = now,
        ))
        return points


class HealthMetricsAdapter(CollectorAdapter):
    """策略层：健康状态快照。"""

    name  = "health_metrics"
    layer = MetricLayer.STRATEGY

    def __init__(self, health_engine) -> None:
        self._he = health_engine

    def collect(self) -> List[MetricPoint]:
        s   = self._he.stats()
        now = datetime.now()
        points = []
        for status_key in ("healthy", "warning", "critical", "unknown"):
            points.append(MetricPoint(
                metric_id   = f"strategy.health_{status_key}.{int(now.timestamp())}",
                name        = f"strategy.health_{status_key}",
                layer       = self.layer,
                metric_type = MetricType.GAUGE,
                value       = float(s.get(status_key, 0)),
                unit        = "",
                source      = "health_engine",
                timestamp   = now,
            ))
        return points


class CustomMetricAdapter(CollectorAdapter):
    """通用自定义采集适配器。"""

    def __init__(
        self,
        name:      str,
        layer:     MetricLayer,
        collector: Callable[[], List[MetricPoint]],
    ) -> None:
        self.name      = name
        self.layer     = layer
        self._fn       = collector

    def collect(self) -> List[MetricPoint]:
        try:
            return self._fn()
        except Exception:
            return []


class MetricCollector:
    """
    定时轮询协调器。
    - 持有多个 CollectorAdapter
    - 每隔 interval_secs 轮询一次，批量推送到 ObservabilityEngine
    - 线程安全，支持热插拔 adapter
    """

    def __init__(
        self,
        obs_engine: "ObservabilityEngine",
        interval_secs: int = 10,
    ) -> None:
        self._obs       = obs_engine
        self._interval  = interval_secs
        self._adapters: Dict[str, CollectorAdapter] = {}
        self._thread:   Optional[threading.Thread]  = None
        self._stop_evt  = threading.Event()
        self._lock      = threading.Lock()

    # ── adapter management ────────────────────────────────────────

    def register(self, adapter: CollectorAdapter) -> None:
        with self._lock:
            self._adapters[adapter.name] = adapter

    def unregister(self, name: str) -> None:
        with self._lock:
            self._adapters.pop(name, None)

    def list_adapters(self) -> List[str]:
        with self._lock:
            return list(self._adapters.keys())

    # ── lifecycle ─────────────────────────────────────────────────

    def start(self) -> None:
        self._stop_evt.clear()
        self._thread = threading.Thread(
            target=self._loop, name="MetricCollector", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_evt.set()
        if self._thread:
            self._thread.join(timeout=5)

    # ── collection loop ───────────────────────────────────────────

    def _loop(self) -> None:
        while not self._stop_evt.is_set():
            self.collect_once()
            self._stop_evt.wait(self._interval)

    def collect_once(self) -> int:
        """立即执行一次采集，返回写入的点数量。"""
        points: List[MetricPoint] = []
        with self._lock:
            adapters = list(self._adapters.values())
        for adapter in adapters:
            try:
                pts = adapter.collect()
                points.extend(pts)
            except Exception:
                pass
        if points:
            self._obs.record_many(points)
        return len(points)

    def stats(self) -> dict:
        return {
            "adapters":     len(self._adapters),
            "interval_secs": self._interval,
            "running":      self._thread is not None and self._thread.is_alive(),
        }
