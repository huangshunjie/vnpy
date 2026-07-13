"""
live_production/engine/order_sync_engine.py  (Phase 4)

OrderSyncEngine — 订单一致性管理器。

职责：
  1. 维护本地订单状态快照
  2. 接收交易所回报，比对不一致
  3. 生成不一致报告，记录修复建议
  4. Phase 4: 检测 + 记录（不执行实际撤单/补单）

❌ 不执行任何撤单 / 补单操作
❌ 不直接访问交易所 API
✔  通过 EventEngine 广播不一致告警
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from ..constant import OrderSyncState
from ..utils.sync_utils import (
    MismatchRecord, SyncAction, compare_order_status, batch_compare
)


@dataclass
class OrderSnapshot:
    """本地订单快照。"""
    order_id:     str
    vt_orderid:   str   = ""
    symbol:       str   = ""
    direction:    str   = ""
    volume:       float = 0.0
    traded:       float = 0.0
    local_status: str   = "unknown"
    sync_state:   OrderSyncState = OrderSyncState.PENDING
    registered_at: datetime = field(default_factory=datetime.now)
    updated_at:   datetime  = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "order_id":     self.order_id,
            "vt_orderid":   self.vt_orderid,
            "symbol":       self.symbol,
            "direction":    self.direction,
            "volume":       self.volume,
            "traded":       self.traded,
            "local_status": self.local_status,
            "sync_state":   self.sync_state.value,
            "updated_at":   str(self.updated_at)[:19],
        }


class OrderSyncEngine:
    """订单一致性管理器（Phase 4）。"""

    def __init__(
        self,
        event_publish_fn: Callable,
        log_fn:           Callable,
    ) -> None:
        self._publish = event_publish_fn
        self._log     = log_fn
        self._lock    = threading.Lock()

        self._orders:    dict[str, OrderSnapshot]  = {}   # order_id -> snapshot
        self._mismatches: list[MismatchRecord]      = []
        self._max_mismatches = 500

        self._total_synced    = 0
        self._total_mismatch  = 0

    # ------------------------------------------------------------------ #
    #  订单注册 / 更新
    # ------------------------------------------------------------------ #

    def register_order(
        self,
        order_id:     str,
        vt_orderid:   str   = "",
        symbol:       str   = "",
        direction:    str   = "",
        volume:       float = 0.0,
        local_status: str   = "submitting",
    ) -> None:
        """注册一笔新订单到本地快照。"""
        with self._lock:
            self._orders[order_id] = OrderSnapshot(
                order_id     = order_id,
                vt_orderid   = vt_orderid,
                symbol       = symbol,
                direction    = direction,
                volume       = volume,
                local_status = local_status,
                sync_state   = OrderSyncState.PENDING,
            )
        self._log(f"[OrderSync] Registered order: {order_id}  {symbol}  {local_status}")

    def update_local_status(self, order_id: str, new_status: str) -> None:
        """更新本地订单状态（由 VeighNa 订单回调触发）。"""
        with self._lock:
            if order_id not in self._orders:
                return
            snap = self._orders[order_id]
            snap.local_status = new_status
            snap.updated_at   = datetime.now()

    # ------------------------------------------------------------------ #
    #  对账
    # ------------------------------------------------------------------ #

    def reconcile(
        self,
        exchange_statuses: dict[str, str],
    ) -> list[MismatchRecord]:
        """
        执行订单对账。

        Parameters
        ----------
        exchange_statuses : { order_id: exchange_status_str }

        Returns
        -------
        list[MismatchRecord]  本次发现的不一致记录
        """
        found: list[MismatchRecord] = []

        with self._lock:
            for order_id, snap in self._orders.items():
                ex_status = exchange_statuses.get(order_id)
                if ex_status is None:
                    continue

                rec = compare_order_status(
                    order_id        = order_id,
                    local_status    = snap.local_status,
                    exchange_status = ex_status,
                    vt_orderid      = snap.vt_orderid,
                )
                if rec is not None:
                    found.append(rec)
                    snap.sync_state = OrderSyncState.MISMATCH
                    self._total_mismatch += 1
                else:
                    snap.sync_state = OrderSyncState.SYNCED
                    self._total_synced += 1

            self._mismatches.extend(found)
            if len(self._mismatches) > self._max_mismatches:
                self._mismatches = self._mismatches[-self._max_mismatches:]

        if found:
            self._log(
                f"[OrderSync] Reconcile: {len(found)} mismatches found"
            )
            self._publish("eLiveProd.order.mismatch", {
                "count":    len(found),
                "order_ids": [r.order_id for r in found],
            })
        else:
            self._log(
                f"[OrderSync] Reconcile: all {len(exchange_statuses)} orders synced"
            )

        return found

    def batch_reconcile(self, orders: list[dict]) -> list[MismatchRecord]:
        """
        批量对账快捷方法。

        Parameters
        ----------
        orders : list[dict]，每项包含 order_id / local_status / exchange_status
        """
        mismatches = batch_compare(orders)
        with self._lock:
            self._mismatches.extend(mismatches)
            if len(self._mismatches) > self._max_mismatches:
                self._mismatches = self._mismatches[-self._max_mismatches:]
            self._total_mismatch += len(mismatches)
            self._total_synced   += len(orders) - len(mismatches)

        if mismatches:
            self._publish("eLiveProd.order.mismatch", {
                "count":    len(mismatches),
                "order_ids": [r.order_id for r in mismatches],
            })
            self._log(f"[OrderSync] Batch reconcile: {len(mismatches)} mismatches")
        else:
            self._log(
                f"[OrderSync] Batch reconcile: {len(orders)} orders clean"
            )
        return mismatches

    def mark_resolved(self, order_id: str) -> bool:
        """标记不一致已修复（人工确认后调用）。"""
        with self._lock:
            for rec in reversed(self._mismatches):
                if rec.order_id == order_id and not rec.resolved:
                    rec.resolved    = True
                    rec.resolved_at = datetime.now()
                    if order_id in self._orders:
                        self._orders[order_id].sync_state = OrderSyncState.SYNCED
                    self._log(f"[OrderSync] Resolved: {order_id}")
                    return True
        return False

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_all_orders(self) -> list[OrderSnapshot]:
        return list(self._orders.values())

    def get_mismatches(
        self,
        limit: int = 100,
        unresolved_only: bool = False,
    ) -> list[MismatchRecord]:
        recs = self._mismatches[-limit:]
        if unresolved_only:
            recs = [r for r in recs if not r.resolved]
        return recs

    def summary(self) -> dict:
        with self._lock:
            total  = len(self._orders)
            synced = sum(1 for s in self._orders.values()
                         if s.sync_state == OrderSyncState.SYNCED)
            pending = sum(1 for s in self._orders.values()
                          if s.sync_state == OrderSyncState.PENDING)
            mismatch = sum(1 for s in self._orders.values()
                           if s.sync_state == OrderSyncState.MISMATCH)
            unresolved = sum(1 for r in self._mismatches if not r.resolved)

        return {
            "total_orders":    total,
            "synced":          synced,
            "pending":         pending,
            "mismatch":        mismatch,
            "total_mismatch_records": len(self._mismatches),
            "unresolved":      unresolved,
            "cumulative_synced":   self._total_synced,
            "cumulative_mismatch": self._total_mismatch,
        }
