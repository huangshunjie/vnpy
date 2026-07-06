"""
system_integration_bus/model/bus_model.py

BusMessage      — 总线上传递的单条消息
PipelineRecord  — 单次管道周期的完整记录
EngineHealthRecord — 子引擎健康快照
BusState        — 总线当前状态快照
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import BusChannel, PipelineStage, MessagePriority, HealthStatus, BusStatus


@dataclass
class BusMessage:
    """总线上传递的单条消息。"""
    msg_id:     str             = ""
    channel:    BusChannel      = BusChannel.SYSTEM
    stage:      PipelineStage   = PipelineStage.INGEST
    priority:   MessagePriority = MessagePriority.NORMAL
    source:     str             = ""    # 发送方模块名
    target:     str             = ""    # 目标模块名（空 = 广播）
    event_type: str             = ""    # 原始 VeighNa 事件类型
    payload:    dict            = field(default_factory=dict)
    created_at: datetime        = field(default_factory=datetime.now)
    forwarded:  bool            = False

    def to_dict(self) -> dict:
        return {
            "msg_id":     self.msg_id,
            "channel":    self.channel.value,
            "stage":      self.stage.value,
            "priority":   self.priority.value,
            "source":     self.source,
            "target":     self.target,
            "event_type": self.event_type,
            "forwarded":  self.forwarded,
            "created_at": str(self.created_at)[:19],
        }


@dataclass
class PipelineRecord:
    """单次完整管道周期（Ingest→Signal→Allocate→Execute→Learn）。"""
    cycle_id:      str   = ""
    cycle_num:     int   = 0
    started_at:    datetime = field(default_factory=datetime.now)
    completed_at:  datetime | None = None

    # 各阶段消息计数
    stage_counts:  dict  = field(default_factory=dict)
    # 各阶段耗时 (ms)
    stage_latency: dict  = field(default_factory=dict)
    # 哪些阶段成功完成
    stages_done:   list[str] = field(default_factory=list)
    # 是否有阶段跳过（对应模块离线）
    stages_skipped:list[str] = field(default_factory=list)

    total_messages: int  = 0
    success:        bool = True
    error_msg:      str  = ""

    @property
    def duration_ms(self) -> float:
        if self.completed_at is None:
            return 0.0
        return round((self.completed_at - self.started_at).total_seconds() * 1000, 2)

    def to_dict(self) -> dict:
        return {
            "cycle_id":      self.cycle_id,
            "cycle_num":     self.cycle_num,
            "started_at":    str(self.started_at)[:19],
            "completed_at":  str(self.completed_at)[:19] if self.completed_at else "",
            "duration_ms":   self.duration_ms,
            "stage_counts":  self.stage_counts,
            "stage_latency": self.stage_latency,
            "stages_done":   self.stages_done,
            "stages_skipped":self.stages_skipped,
            "total_messages":self.total_messages,
            "success":       self.success,
            "error_msg":     self.error_msg,
        }


@dataclass
class EngineHealthRecord:
    """单个子引擎健康快照。"""
    engine_name:   str          = ""
    module:        str          = ""       # vnpy module name
    status:        HealthStatus = HealthStatus.UNKNOWN
    last_seen:     datetime     = field(default_factory=datetime.now)
    message_count: int          = 0        # 总线上收到的消息数
    error_count:   int          = 0
    latency_ms:    float        = 0.0      # 最近一次响应延迟
    metadata:      dict         = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "engine_name":   self.engine_name,
            "module":        self.module,
            "status":        self.status.value,
            "last_seen":     str(self.last_seen)[:19],
            "message_count": self.message_count,
            "error_count":   self.error_count,
            "latency_ms":    round(self.latency_ms, 2),
        }


@dataclass
class BusState:
    """总线当前状态快照。"""
    status:          BusStatus = BusStatus.IDLE
    cycle_count:     int   = 0
    total_messages:  int   = 0
    forwarded_count: int   = 0
    error_count:     int   = 0
    dropped_count:   int   = 0

    # 每个通道的消息计数
    channel_counts:  dict  = field(default_factory=dict)
    # 每个子引擎的健康状态
    engine_health:   dict  = field(default_factory=dict)   # {name: HealthStatus.value}

    # 活跃通道
    active_channels: list[str] = field(default_factory=list)
    # 离线引擎
    offline_engines: list[str] = field(default_factory=list)

    # 最近周期延迟 (ms)
    avg_cycle_ms:    float = 0.0
    throughput_mpm:  float = 0.0   # messages per minute

    updated_at:      datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "status":          self.status.value,
            "cycle_count":     self.cycle_count,
            "total_messages":  self.total_messages,
            "forwarded_count": self.forwarded_count,
            "error_count":     self.error_count,
            "dropped_count":   self.dropped_count,
            "channel_counts":  self.channel_counts,
            "engine_health":   self.engine_health,
            "active_channels": self.active_channels,
            "offline_engines": self.offline_engines,
            "avg_cycle_ms":    round(self.avg_cycle_ms,   2),
            "throughput_mpm":  round(self.throughput_mpm, 2),
            "updated_at":      str(self.updated_at)[:19],
        }
