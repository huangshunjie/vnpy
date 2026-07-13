"""
execution_engine/model/order_model.py

订单数据模型（Phase 2）。

设计原则：
  - 纯数据容器（dataclass），不含业务逻辑
  - OrderRequest  : 信号层产生的执行请求（不可变）
  - Order         : 引擎内部订单对象（含状态、成交进度）
  - 状态转移由 OrderEngine 负责，此处只定义合法转移表
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from ..constant import OrderStatus


# 合法状态转移表：{当前状态: {可转移到的状态集合}}
VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.CREATED:          {OrderStatus.SUBMITTED, OrderStatus.CANCELED},
    OrderStatus.SUBMITTED:        {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED,
                                   OrderStatus.CANCELED, OrderStatus.REJECTED},
    OrderStatus.PARTIALLY_FILLED: {OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED,
                                   OrderStatus.CANCELED},
    OrderStatus.FILLED:           set(),   # 终态
    OrderStatus.CANCELED:         set(),   # 终态
    OrderStatus.REJECTED:         set(),   # 终态
}


@dataclass
class OrderRequest:
    """
    执行请求（信号层 → 执行引擎的入参）。

    由 Strategy / Portfolio / Factor 产生，传入 ExecutionEngine.send_order()。
    一旦创建不可修改（模拟真实下单请求的不可撤回性）。
    """
    symbol:      str            # 合约代码（格式：symbol.exchange）
    direction:   str            # "LONG" / "SHORT"
    volume:      float          # 目标数量（手数）
    signal_price: float         # 信号触发时的参考价格

    # 可选配置
    order_type:  str   = "MARKET"     # "MARKET" / "LIMIT"
    limit_price: float = 0.0          # LIMIT 单价格（MARKET 单忽略）
    source:      str   = "manual"     # 信号来源标记（"cta" / "portfolio" / "factor" / "manual"）

    # 自动生成
    request_id:  str   = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at:  datetime = field(default_factory=datetime.now)


@dataclass
class Order:
    """
    引擎内部订单对象（贯穿整个生命周期）。

    由 OrderEngine.create_from_request() 创建，
    持续被 FillEngine / OrderEngine 更新直到终态。
    """
    # 基础字段（来自 OrderRequest）
    order_id:    str
    symbol:      str
    direction:   str
    volume:      float          # 目标总量
    signal_price: float
    order_type:  str
    limit_price: float
    source:      str

    # 状态与进度
    status:       OrderStatus = OrderStatus.CREATED
    filled_volume: float      = 0.0    # 已成交数量
    avg_fill_price: float     = 0.0    # 加权平均成交价

    # 时间戳
    created_at:   datetime = field(default_factory=datetime.now)
    submitted_at: datetime | None = None
    filled_at:    datetime | None = None
    canceled_at:  datetime | None = None

    # 拒绝原因（REJECTED 状态时填充）
    reject_reason: str = ""

    @property
    def remaining_volume(self) -> float:
        """未成交数量。"""
        return max(0.0, self.volume - self.filled_volume)

    @property
    def fill_rate(self) -> float:
        """成交比例 [0, 1]。"""
        if self.volume <= 0:
            return 0.0
        return min(1.0, self.filled_volume / self.volume)

    @property
    def is_active(self) -> bool:
        """是否仍在活跃状态（非终态）。"""
        return self.status not in (
            OrderStatus.FILLED,
            OrderStatus.CANCELED,
            OrderStatus.REJECTED,
        )

    @property
    def is_terminal(self) -> bool:
        return not self.is_active

    def can_transition_to(self, new_status: OrderStatus) -> bool:
        """检查状态转移是否合法。"""
        return new_status in VALID_TRANSITIONS.get(self.status, set())

    @classmethod
    def from_request(cls, req: OrderRequest) -> "Order":
        """从 OrderRequest 创建订单（初始状态 CREATED）。"""
        return cls(
            order_id    = req.request_id,
            symbol      = req.symbol,
            direction   = req.direction,
            volume      = req.volume,
            signal_price = req.signal_price,
            order_type  = req.order_type,
            limit_price = req.limit_price,
            source      = req.source,
            created_at  = req.created_at,
        )
