"""
system_console/model/console_model.py

ModuleEntry   — 单个模块的实时状态快照
SystemState   — 全系统状态汇总
ConsoleLog    — 控制台日志条目
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import ModuleState, ConsoleStatus


@dataclass
class ModuleEntry:
    """单个模块的实时状态。"""
    key:         str
    label:       str
    display:     str
    app_name:    str
    layer:       int

    state:       ModuleState  = ModuleState.UNKNOWN
    started_at:  datetime | None = None
    stopped_at:  datetime | None = None
    error_msg:   str          = ""

    # live metrics (从 PerformanceMonitor 读取)
    event_count: int   = 0
    error_count: int   = 0
    latency_ms:  float = 0.0
    throughput:  float = 0.0    # events/min
    error_rate:  float = 0.0

    @property
    def uptime_s(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.stopped_at or datetime.now()
        return round((end - self.started_at).total_seconds(), 1)

    def to_dict(self) -> dict:
        return {
            "key":         self.key,
            "label":       self.label,
            "display":     self.display,
            "app_name":    self.app_name,
            "layer":       self.layer,
            "state":       self.state.value,
            "uptime_s":    self.uptime_s,
            "event_count": self.event_count,
            "error_count": self.error_count,
            "latency_ms":  round(self.latency_ms, 2),
            "throughput":  round(self.throughput, 2),
            "error_rate":  round(self.error_rate, 4),
            "error_msg":   self.error_msg,
        }


@dataclass
class SystemState:
    """全系统状态汇总快照。"""
    status:        ConsoleStatus = ConsoleStatus.IDLE
    running_count: int   = 0
    stopped_count: int   = 0
    error_count:   int   = 0
    total_modules: int   = 18

    # aggregate metrics
    total_events:  int   = 0
    total_errors:  int   = 0
    avg_latency:   float = 0.0
    system_tput:   float = 0.0    # sum of all module throughputs
    health_score:  float = 100.0  # 0–100

    updated_at:    datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "status":        self.status.value,
            "running_count": self.running_count,
            "stopped_count": self.stopped_count,
            "error_count":   self.error_count,
            "total_modules": self.total_modules,
            "total_events":  self.total_events,
            "total_errors":  self.total_errors,
            "avg_latency":   round(self.avg_latency, 2),
            "system_tput":   round(self.system_tput, 2),
            "health_score":  round(self.health_score, 1),
            "updated_at":    str(self.updated_at)[:19],
        }


@dataclass
class ConsoleLog:
    """控制台日志条目。"""
    ts:      datetime = field(default_factory=datetime.now)
    module:  str      = "System"
    level:   str      = "INFO"   # INFO / WARN / ERROR
    message: str      = ""

    def to_line(self) -> str:
        return f"[{str(self.ts)[11:19]}] [{self.level:<5}] [{self.module:<28}] {self.message}"
