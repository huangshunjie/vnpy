"""
live_production/model/health_model.py

HealthSnapshot — 系统健康快照（Phase 1 Stub）。
Phase 5 实现完整健康指标采集逻辑。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import SystemHealthState


@dataclass
class HealthSnapshot:
    """系统健康快照（stub）。"""
    health_state:      SystemHealthState = SystemHealthState.UNKNOWN
    latency_ms:        float = 0.0      # 网关往返延迟
    order_success_rate: float = 0.0     # 订单成功率（0-1）
    data_delay_s:      float = 0.0      # 行情延迟（秒）
    heartbeat_ok:      bool  = False    # 心跳正常
    last_heartbeat_at: datetime | None = None
    snapshot_at:       datetime = field(default_factory=datetime.now)
    notes:             str = ""

    def to_dict(self) -> dict:
        return {
            "health_state":       self.health_state.value,
            "latency_ms":         round(self.latency_ms, 1),
            "order_success_rate": round(self.order_success_rate, 3),
            "data_delay_s":       round(self.data_delay_s, 1),
            "heartbeat_ok":       self.heartbeat_ok,
            "snapshot_at":        str(self.snapshot_at)[:19],
            "notes":              self.notes,
        }
