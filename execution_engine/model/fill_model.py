"""
execution_engine/model/fill_model.py

成交记录数据模型（Phase 2）。

FillRecord  : 单笔成交记录（一个订单可能有多笔部分成交）
FillSummary : 某订单所有成交的汇总统计
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FillRecord:
    """
    单笔成交记录。

    每次 FillEngine 模拟出成交时产生一条记录。
    一个订单在 Partial Fill 模式下可能产生多条 FillRecord。
    """
    fill_id:      str           = field(default_factory=lambda: str(uuid.uuid4())[:8])
    order_id:     str           = ""
    symbol:       str           = ""
    direction:    str           = ""            # "LONG" / "SHORT"

    # 成交细节
    fill_volume:  float         = 0.0           # 本次成交数量
    fill_price:   float         = 0.0           # 本次成交价格
    signal_price: float         = 0.0           # 对应信号价格（用于滑点计算）

    # 滑点（Phase 2 简单版；Phase 3 细化）
    slippage:     float         = 0.0           # fill_price - signal_price（方向调整后）
    slippage_pct: float         = 0.0           # slippage / signal_price

    # 时间戳
    filled_at:    datetime      = field(default_factory=datetime.now)

    # 信号来源
    source:       str           = ""            # "cta" / "portfolio" / "factor" / "manual"

    @property
    def notional(self) -> float:
        """成交金额（未乘合约乘数，Phase 3 补充）。"""
        return self.fill_volume * self.fill_price


@dataclass
class FillSummary:
    """
    某订单全部成交的汇总统计。

    由 FillEngine.summarize(order_id) 计算，
    用于 ExecutionTab 和 Report Tab 展示。
    """
    order_id:       str     = ""
    symbol:         str     = ""
    direction:      str     = ""

    total_volume:   float   = 0.0       # 合计成交量
    avg_fill_price: float   = 0.0       # 加权平均成交价
    signal_price:   float   = 0.0       # 参考信号价格

    # 滑点汇总
    total_slippage:     float = 0.0     # 总滑点绝对值（= avg_fill - signal）
    avg_slippage_pct:   float = 0.0     # 平均滑点百分比

    # 成交记录列表
    fills: list[FillRecord] = field(default_factory=list)

    # 时间戳
    first_fill_at: datetime | None = None
    last_fill_at:  datetime | None = None

    @property
    def fill_count(self) -> int:
        return len(self.fills)

    @property
    def total_notional(self) -> float:
        return sum(f.notional for f in self.fills)

    @classmethod
    def from_fills(cls, fills: list[FillRecord]) -> "FillSummary":
        """从成交记录列表计算汇总。"""
        if not fills:
            return cls()

        first = fills[0]
        total_vol = sum(f.fill_volume for f in fills)
        if total_vol <= 0:
            return cls(order_id=first.order_id, symbol=first.symbol)

        avg_price = sum(f.fill_price * f.fill_volume for f in fills) / total_vol
        signal_price = first.signal_price
        direction_sign = 1.0 if first.direction == "LONG" else -1.0
        total_slip = direction_sign * (avg_price - signal_price) * total_vol
        avg_slip_pct = (avg_price - signal_price) / signal_price \
            if signal_price > 0 else 0.0

        return cls(
            order_id        = first.order_id,
            symbol          = first.symbol,
            direction       = first.direction,
            total_volume    = total_vol,
            avg_fill_price  = avg_price,
            signal_price    = signal_price,
            total_slippage  = total_slip,
            avg_slippage_pct = avg_slip_pct,
            fills           = fills,
            first_fill_at   = fills[0].filled_at,
            last_fill_at    = fills[-1].filled_at,
        )
