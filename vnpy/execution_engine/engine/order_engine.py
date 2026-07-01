"""
execution_engine/engine/order_engine.py

OrderEngine — 订单生命周期状态机（Phase 2 实现）。

职责：
  - 从 OrderRequest 创建 Order
  - 管理所有活跃订单（active_orders）和历史订单（order_history）
  - 驱动订单状态转移（validate → submit → fill → terminal）
  - 提供查询接口（按 ID / 状态 / 来源 / 合约过滤）

状态机：
  CREATED → SUBMITTED → PARTIALLY_FILLED → FILLED (terminal)
                      ↘ CANCELED (terminal)
                      ↘ REJECTED (terminal)
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ..constant import OrderStatus
from ..model.fill_model import FillRecord
from ..model.order_model import Order, OrderRequest, VALID_TRANSITIONS


class OrderEngine:
    """
    订单生命周期状态机（无外部 IO，纯内存）。

    使用方式：
        engine = OrderEngine()
        order  = engine.create(request)
        engine.submit(order.order_id)
        fills  = fill_engine.simulate(order)
        engine.apply_fills(order.order_id, fills)
    """

    def __init__(self) -> None:
        # 活跃订单：order_id → Order
        self._active:  dict[str, Order] = {}
        # 历史订单（已到终态）：order_id → Order
        self._history: dict[str, Order] = {}
        # 状态变更回调（dispatcher 注册，用于发 Event）
        self._on_status_change: Callable[[Order], None] | None = None

    # ------------------------------------------------------------------ #
    #  订单创建
    # ------------------------------------------------------------------ #

    def create(self, request: OrderRequest) -> Order:
        """从 OrderRequest 创建订单并加入活跃列表。"""
        order = Order.from_request(request)
        self._active[order.order_id] = order
        self._notify(order)
        return order

    # ------------------------------------------------------------------ #
    #  状态转移
    # ------------------------------------------------------------------ #

    def submit(self, order_id: str) -> bool:
        """
        将订单标记为 SUBMITTED（模拟发送到市场）。

        Returns
        -------
        bool  转移是否成功
        """
        order = self._active.get(order_id)
        if order is None:
            return False
        return self._transition(order, OrderStatus.SUBMITTED,
                                submitted_at=datetime.now())

    def apply_fills(
        self,
        order_id: str,
        fills: list[FillRecord],
    ) -> bool:
        """
        应用成交记录，更新订单状态和成交进度。

        - 更新 filled_volume / avg_fill_price
        - 若剩余量 = 0 → FILLED；否则 → PARTIALLY_FILLED
        - 若订单已在终态则忽略

        Returns
        -------
        bool  是否有实际状态变更
        """
        order = self._active.get(order_id)
        if order is None or not order.is_active:
            return False
        if not fills:
            return False

        for f in fills:
            prev_vol = order.filled_volume
            order.filled_volume += f.fill_volume
            # 加权平均价格
            prev_val = order.avg_fill_price * prev_vol
            new_val  = f.fill_price * f.fill_volume
            total    = order.filled_volume
            order.avg_fill_price = (prev_val + new_val) / total if total > 0 else f.fill_price

        # 判断新状态
        if order.remaining_volume <= 1e-9:
            self._transition(order, OrderStatus.FILLED, filled_at=datetime.now())
        else:
            self._transition(order, OrderStatus.PARTIALLY_FILLED)

        return True

    def cancel(self, order_id: str, reason: str = "user_cancel") -> bool:
        """取消订单。"""
        order = self._active.get(order_id)
        if order is None or not order.is_active:
            return False
        order.reject_reason = reason
        return self._transition(order, OrderStatus.CANCELED,
                                canceled_at=datetime.now())

    def reject(self, order_id: str, reason: str = "") -> bool:
        """拒绝订单（如参数校验失败）。"""
        order = self._active.get(order_id)
        if order is None:
            return False
        order.reject_reason = reason
        return self._transition(order, OrderStatus.REJECTED)

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get(self, order_id: str) -> Order | None:
        """按 ID 查询（活跃 + 历史）。"""
        return self._active.get(order_id) or self._history.get(order_id)

    def get_active(self) -> list[Order]:
        """返回所有活跃订单列表（副本）。"""
        return list(self._active.values())

    def get_history(self) -> list[Order]:
        """返回所有历史订单列表（副本）。"""
        return list(self._history.values())

    def get_all(self) -> list[Order]:
        return self.get_active() + self.get_history()

    def filter_by_status(self, status: OrderStatus) -> list[Order]:
        return [o for o in self.get_all() if o.status == status]

    def filter_by_symbol(self, symbol: str) -> list[Order]:
        return [o for o in self.get_all() if o.symbol == symbol]

    def filter_by_source(self, source: str) -> list[Order]:
        return [o for o in self.get_all() if o.source == source]

    @property
    def active_count(self) -> int:
        return len(self._active)

    @property
    def total_count(self) -> int:
        return len(self._active) + len(self._history)

    def clear_history(self) -> None:
        """清空历史订单（新一轮回测前调用）。"""
        self._history.clear()

    def clear_all(self) -> None:
        """清空所有订单。"""
        self._active.clear()
        self._history.clear()

    # ------------------------------------------------------------------ #
    #  回调注册
    # ------------------------------------------------------------------ #

    def register_status_callback(
        self,
        callback: Callable[[Order], None],
    ) -> None:
        """注册状态变更回调（dispatcher 用于发 EVENT_ORDER_UPDATE）。"""
        self._on_status_change = callback

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    def _transition(
        self,
        order: Order,
        new_status: OrderStatus,
        **kwargs,
    ) -> bool:
        """执行状态转移，更新时间戳，触发回调，移入历史。"""
        if not order.can_transition_to(new_status):
            return False

        order.status = new_status

        # 更新可选时间戳字段
        for k, v in kwargs.items():
            if hasattr(order, k):
                setattr(order, k, v)

        # 终态：移入历史
        if order.is_terminal:
            self._history[order.order_id] = order
            self._active.pop(order.order_id, None)

        self._notify(order)
        return True

    def _notify(self, order: Order) -> None:
        """触发状态变更回调。"""
        if self._on_status_change is not None:
            try:
                self._on_status_change(order)
            except Exception:
                pass
