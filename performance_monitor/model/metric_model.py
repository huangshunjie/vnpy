"""
performance_monitor/model/metric_model.py

MetricPoint      — 单个时间点的指标采样
ModuleMetrics    — 单个模块的全量指标集合
SystemSnapshot   — 全系统瞬时快照
Alert            — 告警记录
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import MetricType, AlertLevel, ModuleStatus


@dataclass
class MetricPoint:
    """单个时间点的指标采样。"""
    module:     str
    metric:     MetricType
    value:      float
    unit:       str        = ""     # ms / events/min / % / count
    sampled_at: datetime   = field(default_factory=datetime.now)
    tags:       dict       = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "module":     self.module,
            "metric":     self.metric.value,
            "value":      round(self.value, 4),
            "unit":       self.unit,
            "sampled_at": str(self.sampled_at)[:19],
        }


@dataclass
class ModuleMetrics:
    """单个模块的全量实时指标。"""
    module:     str
    status:     ModuleStatus = ModuleStatus.UNKNOWN

    # 核心指标（最近值）
    latency_ms:    float = 0.0     # 最近一次事件处理延迟 (ms)
    throughput:    float = 0.0     # 事件/分钟
    error_rate:    float = 0.0     # [0, 1]
    event_count:   int   = 0       # 累计事件数
    error_count:   int   = 0       # 累计错误数
    queue_depth:   int   = 0       # 待处理消息数

    # 统计（1min 窗口）
    avg_latency_1m: float = 0.0
    p95_latency_1m: float = 0.0
    p99_latency_1m: float = 0.0
    max_latency_1m: float = 0.0
    throughput_1m:  float = 0.0
    error_rate_1m:  float = 0.0

    # 时间
    first_seen:  datetime | None = None
    last_seen:   datetime | None = None
    last_error:  datetime | None = None

    # 原始时间序列缓冲（内部使用，不序列化）
    _latency_buf: deque = field(default_factory=lambda: deque(maxlen=300))
    _event_ts_buf:deque = field(default_factory=lambda: deque(maxlen=600))
    _error_ts_buf:deque = field(default_factory=lambda: deque(maxlen=200))

    @property
    def uptime_s(self) -> float:
        if self.first_seen is None:
            return 0.0
        return round((datetime.now() - self.first_seen).total_seconds(), 1)

    @property
    def last_seen_ago_s(self) -> float:
        if self.last_seen is None:
            return 99999.0
        return round((datetime.now() - self.last_seen).total_seconds(), 1)

    def to_dict(self) -> dict:
        return {
            "module":          self.module,
            "status":          self.status.value,
            "latency_ms":      round(self.latency_ms,     2),
            "throughput":      round(self.throughput,     2),
            "error_rate":      round(self.error_rate,     4),
            "event_count":     self.event_count,
            "error_count":     self.error_count,
            "queue_depth":     self.queue_depth,
            "avg_latency_1m":  round(self.avg_latency_1m, 2),
            "p95_latency_1m":  round(self.p95_latency_1m, 2),
            "p99_latency_1m":  round(self.p99_latency_1m, 2),
            "max_latency_1m":  round(self.max_latency_1m, 2),
            "throughput_1m":   round(self.throughput_1m,  2),
            "error_rate_1m":   round(self.error_rate_1m,  4),
            "uptime_s":        self.uptime_s,
            "last_seen_ago_s": self.last_seen_ago_s,
            "last_seen":       str(self.last_seen)[:19] if self.last_seen else "",
        }


@dataclass
class SystemSnapshot:
    """全系统瞬时快照 — 汇总所有16个模块。"""
    snapshot_id:    str      = ""
    taken_at:       datetime = field(default_factory=datetime.now)

    # 系统级汇总
    total_events:   int   = 0
    total_errors:   int   = 0
    system_throughput: float = 0.0   # events/min (全系统合计)
    system_error_rate: float = 0.0   # 全系统平均错误率
    avg_latency_ms: float = 0.0      # 全系统平均延迟

    # 模块状态统计
    active_count:   int = 0
    idle_count:     int = 0
    degraded_count: int = 0
    offline_count:  int = 0
    unknown_count:  int = 0

    # 各模块快照
    modules: dict[str, dict] = field(default_factory=dict)

    # 告警摘要
    active_alerts:  int = 0
    critical_alerts:int = 0

    # 性能健康分 [0, 100]
    health_score:   float = 100.0

    def to_dict(self) -> dict:
        return {
            "snapshot_id":       self.snapshot_id,
            "taken_at":          str(self.taken_at)[:19],
            "total_events":      self.total_events,
            "total_errors":      self.total_errors,
            "system_throughput": round(self.system_throughput, 2),
            "system_error_rate": round(self.system_error_rate, 4),
            "avg_latency_ms":    round(self.avg_latency_ms,    2),
            "active_count":      self.active_count,
            "idle_count":        self.idle_count,
            "degraded_count":    self.degraded_count,
            "offline_count":     self.offline_count,
            "unknown_count":     self.unknown_count,
            "active_alerts":     self.active_alerts,
            "critical_alerts":   self.critical_alerts,
            "health_score":      round(self.health_score, 1),
            "modules":           self.modules,
        }


@dataclass
class Alert:
    """单条告警记录。"""
    alert_id:   str        = ""
    module:     str        = ""
    level:      AlertLevel = AlertLevel.INFO
    metric:     MetricType = MetricType.CUSTOM
    message:    str        = ""
    value:      float      = 0.0
    threshold:  float      = 0.0
    fired_at:   datetime   = field(default_factory=datetime.now)
    resolved:   bool       = False
    resolved_at:datetime | None = None

    def to_dict(self) -> dict:
        return {
            "alert_id":    self.alert_id,
            "module":      self.module,
            "level":       self.level.value,
            "metric":      self.metric.value,
            "message":     self.message,
            "value":       round(self.value,     4),
            "threshold":   round(self.threshold, 4),
            "fired_at":    str(self.fired_at)[:19],
            "resolved":    self.resolved,
            "resolved_at": str(self.resolved_at)[:19] if self.resolved_at else "",
        }
