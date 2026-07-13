"""
execution_engine/model/execution_model.py

执行记录与统计数据模型（Phase 2）。

ExecutionRecord : 单次完整执行过程的快照（信号 → 成交 → 结果）
ExecutionStats  : 多笔执行的汇总统计（用于 Report Tab）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExecutionRecord:
    """
    单次完整执行记录。

    一条 ExecutionRecord 对应一个 OrderRequest 从创建到终态的完整过程。
    由 ExecutionEngine 在订单进入终态时生成，写入历史列表并发送事件。
    """
    record_id:    str = ""
    order_id:     str = ""
    symbol:       str = ""
    direction:    str = ""          # "LONG" / "SHORT"
    source:       str = ""          # 信号来源

    # 价格信息
    signal_price:   float = 0.0     # 信号触发价
    avg_fill_price: float = 0.0     # 实际平均成交价
    slippage:       float = 0.0     # avg_fill - signal（方向调整后，正值=不利滑点）
    slippage_pct:   float = 0.0     # slippage / signal_price

    # 数量
    target_volume:  float = 0.0     # 目标数量
    filled_volume:  float = 0.0     # 实际成交数量
    fill_rate:      float = 0.0     # 成交率 [0, 1]

    # 成交模式
    fill_mode:      str   = ""      # "immediate" / "partial"
    slippage_model: str   = ""      # "fixed" / "percentage" / "volatility"

    # Phase 3: 成本明细（由 CostEngine 填充）
    commission:     float = 0.0     # 手续费
    slippage_cost:  float = 0.0     # 滑点成本
    impact_cost:    float = 0.0     # 市场冲击成本
    total_cost:     float = 0.0     # 总成本
    total_cost_pct: float = 0.0     # 成本率
    notional:       float = 0.0     # 名义价值
    net_pnl_impact: float = 0.0     # 净 PnL 影响 (= -total_cost)

    # 时间戳
    created_at:   datetime = field(default_factory=datetime.now)
    filled_at:    datetime | None = None

    # 最终状态
    final_status: str = ""          # OrderStatus.value

    # 关联成交数
    fill_count:   int = 0

    @property
    def execution_delay_ms(self) -> float:
        """从创建到最终成交的延迟（毫秒）。"""
        if self.filled_at is None:
            return float("nan")
        delta = (self.filled_at - self.created_at).total_seconds()
        return delta * 1000.0

    @property
    def is_complete(self) -> bool:
        return self.fill_rate >= 1.0 - 1e-9


@dataclass
class ExecutionStats:
    """
    多笔执行的汇总统计（Report Tab 使用）。

    由 ExecutionEngine.compute_stats() 计算，
    基于 ExecutionRecord 列表聚合。
    """
    total_orders:     int   = 0
    filled_orders:    int   = 0
    partial_orders:   int   = 0
    canceled_orders:  int   = 0
    rejected_orders:  int   = 0

    # 成交质量
    avg_fill_rate:       float = 0.0    # 平均成交率
    avg_slippage:        float = 0.0    # 平均滑点（绝对值）
    avg_slippage_pct:    float = 0.0    # 平均滑点百分比
    total_slippage_cost: float = 0.0    # 滑点总成本（= Σ slippage × filled_volume）

    # 执行效率
    avg_delay_ms:     float = 0.0       # 平均执行延迟（毫秒）

    # 方向分布
    long_count:       int   = 0
    short_count:      int   = 0

    # 来源分布
    source_breakdown: dict[str, int] = field(default_factory=dict)

    # 计算时间
    computed_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_records(cls, records: list[ExecutionRecord]) -> "ExecutionStats":
        """从执行记录列表计算汇总统计。"""
        if not records:
            return cls()

        from ..constant import OrderStatus

        stats = cls(total_orders=len(records))

        status_map = {
            "filled":           "filled_orders",
            "partially_filled": "partial_orders",
            "canceled":         "canceled_orders",
            "rejected":         "rejected_orders",
        }
        for rec in records:
            attr = status_map.get(rec.final_status)
            if attr:
                setattr(stats, attr, getattr(stats, attr) + 1)

            if rec.direction == "LONG":
                stats.long_count += 1
            else:
                stats.short_count += 1

            stats.source_breakdown[rec.source] = \
                stats.source_breakdown.get(rec.source, 0) + 1

        n = len(records)
        fill_rates = [r.fill_rate for r in records]
        slippages  = [r.slippage for r in records]
        slip_pcts  = [r.slippage_pct for r in records]
        delays     = [r.execution_delay_ms for r in records
                      if not (r.execution_delay_ms != r.execution_delay_ms)]

        stats.avg_fill_rate      = sum(fill_rates) / n
        stats.avg_slippage       = sum(slippages) / n
        stats.avg_slippage_pct   = sum(slip_pcts) / n
        stats.total_slippage_cost = sum(
            r.slippage * r.filled_volume for r in records
        )
        stats.avg_delay_ms = sum(delays) / len(delays) if delays else 0.0
        stats.computed_at  = datetime.now()
        return stats
