"""
live_production/model/order_state_model.py

OrderSyncRecord — 订单同步状态记录（Phase 1 Stub）。
Phase 4 实现订单一致性检查逻辑。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from ..constant import OrderSyncState


@dataclass
class OrderSyncRecord:
    """订单同步记录（stub）。"""
    order_id:     str            = ""
    vt_orderid:   str            = ""
    sync_state:   OrderSyncState = OrderSyncState.PENDING
    local_status: str            = ""
    exchange_status: str         = ""
    mismatch_reason: str         = ""
    created_at:   datetime       = field(default_factory=datetime.now)
    updated_at:   datetime       = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "order_id":       self.order_id,
            "vt_orderid":     self.vt_orderid,
            "sync_state":     self.sync_state.value,
            "local_status":   self.local_status,
            "exchange_status": self.exchange_status,
            "mismatch_reason": self.mismatch_reason,
            "updated_at":     str(self.updated_at)[:19],
        }
