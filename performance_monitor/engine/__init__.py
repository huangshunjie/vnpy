"""
performance_monitor/engine/__init__.py

PerformanceMonitorEngine — VeighNa BaseEngine 子类。
统一监控所有 16 个模块的延迟、吞吐量、错误率，生成系统级 Dashboard。
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from ..constant import (
    APP_NAME, MONITORED_MODULES, AggWindow,
    AlertLevel, ModuleStatus, MetricType,
)
from ..event import (
    EVENT_MONITOR_STARTED, EVENT_MONITOR_STOPPED,
    EVENT_METRIC_UPDATED, EVENT_SNAPSHOT_UPDATED,
    EVENT_ALERT_INFO, EVENT_ALERT_WARNING,
    EVENT_ALERT_CRITICAL, EVENT_ALERT_FATAL,
    EVENT_MODULE_STATUS_CHANGED, EVENT_MODULE_OFFLINE,
    EVENT_MODULE_RECOVERED, EVENT_DASHBOARD_REFRESH,
)
from .collector    import MetricCollector
from .aggregator   import MetricAggregator
from .alert_engine import AlertEngine
from ..model.metric_model import (
    ModuleMetrics, SystemSnapshot, Alert, MetricPoint,
)

_ALERT_EVENTS = {
    AlertLevel.INFO:     EVENT_ALERT_INFO,
    AlertLevel.WARNING:  EVENT_ALERT_WARNING,
    AlertLevel.CRITICAL: EVENT_ALERT_CRITICAL,
    AlertLevel.FATAL:    EVENT_ALERT_FATAL,
}


class PerformanceMonitorEngine(BaseEngine):
    """全系统实时性能监控引擎（16 模块 / 121 事件）。"""

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine,
                 event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._started_at:  datetime | None = None
        self._log_records: list[str]       = []
        self._agg_interval_secs = 10.0   # aggregation update interval

        # ── sub-engines ───────────────────────────────────────────────
        self._collector = MetricCollector(
            event_engine,
            on_metric = self._on_metric_point,
            log_fn    = self._log,
        )
        self._aggregator = MetricAggregator(
            self._collector,
            window           = AggWindow.W1M,
            on_status_change = self._on_status_change,
            log_fn           = self._log,
        )
        self._alert_engine = AlertEngine(
            on_alert = self._on_alert,
            log_fn   = self._log,
        )

        self._snapshot_count = 0
        self._log(f"[{APP_NAME}] PerformanceMonitorEngine created")

    # ── lifecycle ─────────────────────────────────────────────────────
    def init(self) -> None:
        self._log(f"[{APP_NAME}] init()")

    def start(self) -> None:
        self._started_at = datetime.now()
        self._collector.start()
        self.dispatch_event(EVENT_MONITOR_STARTED,
                            {"modules": len(MONITORED_MODULES),
                             "event_types": self._collector.total_event_types})
        self._log(f"[{APP_NAME}] started — monitoring "
                  f"{self._collector.total_event_types} events "
                  f"across {len(MONITORED_MODULES)} modules")

    def stop(self) -> None:
        self._collector.stop()
        self.dispatch_event(EVENT_MONITOR_STOPPED, {"uptime": self._uptime()})
        self._log(f"[{APP_NAME}] stopped")

    def close(self) -> None:
        self.stop()

    # ── periodic update (call from UI timer or external scheduler) ────
    def update(self) -> SystemSnapshot:
        """
        触发一次聚合更新并评估告警规则。
        UI 定时器（如每 5 秒）调用此方法驱动 Dashboard 刷新。
        """
        snap = self._aggregator.update()
        self._snapshot_count += 1

        # evaluate alerts
        new_alerts = self._alert_engine.evaluate(snap)

        # dispatch snapshot event
        self.dispatch_event(EVENT_SNAPSHOT_UPDATED, {
            "snapshot_id":       snap.snapshot_id,
            "health_score":      snap.health_score,
            "system_throughput": snap.system_throughput,
            "avg_latency_ms":    snap.avg_latency_ms,
            "active_count":      snap.active_count,
            "offline_count":     snap.offline_count,
            "active_alerts":     self._alert_engine.active_count(),
        })
        self.dispatch_event(EVENT_DASHBOARD_REFRESH, snap.to_dict())
        return snap

    # ── callbacks ────────────────────────────────────────────────────
    def _on_metric_point(self, point: MetricPoint) -> None:
        self.dispatch_event(EVENT_METRIC_UPDATED, point.to_dict())

    def _on_status_change(self, module: str,
                           old: ModuleStatus, new: ModuleStatus) -> None:
        payload = {"module": module, "old": old.value, "new": new.value}
        self.dispatch_event(EVENT_MODULE_STATUS_CHANGED, payload)
        if new == ModuleStatus.OFFLINE:
            self.dispatch_event(EVENT_MODULE_OFFLINE, payload)
        elif old == ModuleStatus.OFFLINE and new != ModuleStatus.OFFLINE:
            self.dispatch_event(EVENT_MODULE_RECOVERED, payload)

    def _on_alert(self, alert: Alert) -> None:
        ev = _ALERT_EVENTS.get(alert.level, EVENT_ALERT_WARNING)
        self.dispatch_event(ev, alert.to_dict())

    # ── public query interface ────────────────────────────────────────
    def get_module_metrics(self, module: str) -> ModuleMetrics | None:
        return self._collector.get_metrics(module)

    def get_all_metrics(self) -> dict[str, ModuleMetrics]:
        return self._collector.get_all_metrics()

    def get_latest_snapshot(self) -> SystemSnapshot | None:
        return self._aggregator.get_latest_snapshot()

    def get_snapshot_history(self, n: int = 60) -> list[SystemSnapshot]:
        return self._aggregator.get_snapshot_history(n)

    def get_active_alerts(self,
                           level: AlertLevel | None = None) -> list[Alert]:
        return self._alert_engine.get_active(level)

    def get_alert_history(self, n: int = 100) -> list[Alert]:
        return self._alert_engine.get_history(n)

    def resolve_alert(self, alert_id: str) -> bool:
        return self._alert_engine.resolve(alert_id)

    def resolve_module_alerts(self, module: str) -> int:
        return self._alert_engine.resolve_module(module)

    def get_latency_history(self, module: str,
                             n: int = 100) -> list[float]:
        return self._aggregator.get_module_latency_history(module, n)

    def get_monitored_modules(self) -> list[str]:
        return list(MONITORED_MODULES)

    def inject_event(self, event_type: str,
                      data: dict | None = None) -> None:
        """直接注入一条事件（测试/模拟用）。"""
        self._collector.inject(event_type, data)

    # ── events ────────────────────────────────────────────────────────
    def dispatch_event(self, event_type: str,
                        data: dict | None = None) -> None:
        self.event_engine.put(Event(event_type, data or {}))

    # ── summary ───────────────────────────────────────────────────────
    def get_summary(self) -> dict:
        agg  = self._aggregator.summary()
        alrt = self._alert_engine.summary()
        return {
            "app":              APP_NAME,
            "phase":            1,
            "uptime":           self._uptime(),
            "modules":          len(MONITORED_MODULES),
            "event_types":      self._collector.total_event_types,
            "total_events":     self._collector.total_events_received,
            "total_errors":     self._collector.total_errors_received,
            "snapshot_count":   self._snapshot_count,
            "health_score":     agg.get("health_score", 100.0),
            "system_throughput":agg.get("system_throughput", 0.0),
            "avg_latency_ms":   agg.get("avg_latency_ms", 0.0),
            "active_count":     agg.get("active_count", 0),
            "offline_count":    agg.get("offline_count", 0),
            "alerts":           alrt,
        }

    def get_logs(self, limit: int = 200) -> list[str]:
        return self._log_records[-limit:]

    # ── internal ─────────────────────────────────────────────────────
    def _uptime(self) -> float:
        if self._started_at is None:
            return 0.0
        return round((datetime.now() - self._started_at).total_seconds(), 1)

    def _log(self, msg: str) -> None:
        ts = str(datetime.now())[:19]
        self._log_records.append(f"{ts}  {msg}")
        try:    self.write_log(msg)
        except: pass


__all__ = ["PerformanceMonitorEngine",
           "MetricCollector", "MetricAggregator", "AlertEngine"]
