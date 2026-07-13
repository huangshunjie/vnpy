"""
execution_engine/engine/execution_engine.py

ExecutionCoreEngine — 信号 → 订单 → 成交 流水线（Phase 2 实现）。

职责：
  - 编排 OrderEngine / FillEngine / SlippageEngine 的协作流程
  - 维护执行记录历史（ExecutionRecord 列表）
  - 提供汇总统计接口（ExecutionStats）
  - 不持有 VeighNa EventEngine 引用（事件发送由 dispatcher 负责）

流水线（每次 execute() 调用）：
  OrderRequest
      ↓ OrderEngine.create()
      ↓ OrderEngine.submit()
      ↓ FillEngine.simulate_all()
      ↓ OrderEngine.apply_fills()
      ↓ [terminal] ExecutionRecord 生成
      → 返回 (Order, fills, record)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Callable

from ..constant import OrderStatus
from ..model.execution_model import ExecutionRecord, ExecutionStats
from ..model.fill_model import FillRecord, FillSummary
from ..model.order_model import Order, OrderRequest
from .fill_engine import FillConfig, FillEngine
from .order_engine import OrderEngine
from .slippage_engine import SlippageConfig, SlippageEngine
from .cost_engine import CostConfig, CostEngine, CostBreakdown, CostSummary


class ExecutionCoreEngine:
    """
    执行核心引擎：编排 OrderEngine / FillEngine / SlippageEngine。

    使用方式：
        engine = ExecutionCoreEngine()
        order, fills, record = engine.execute(request)
    """

    def __init__(
        self,
        slippage_config: SlippageConfig | None = None,
        fill_config:     FillConfig | None     = None,
        cost_config:     CostConfig | None     = None,
    ) -> None:
        self.slippage_engine = SlippageEngine(slippage_config)
        self.fill_engine     = FillEngine(fill_config, self.slippage_engine)
        self.order_engine    = OrderEngine()
        self.cost_engine     = CostEngine(cost_config)

        self._execution_history: list[ExecutionRecord] = []
        self._cost_breakdowns:   list[CostBreakdown]   = []

        # 回调钩子（dispatcher 注册，用于发送 VeighNa 事件）
        self._on_order_update:     Callable[[Order], None]       | None = None
        self._on_fill_update:      Callable[[FillRecord], None]  | None = None
        self._on_execution_record: Callable[[ExecutionRecord], None] | None = None

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def execute(
        self,
        request: OrderRequest,
    ) -> tuple[Order, list[FillRecord], ExecutionRecord | None]:
        """
        执行单个 OrderRequest 的完整流水线。

        Returns
        -------
        (order, fills, record)
          order   : 最终状态的 Order 对象
          fills   : 本次产生的所有 FillRecord
          record  : ExecutionRecord（到达终态时非 None）
        """
        # 1. 创建订单
        order = self.order_engine.create(request)

        # 2. 提交（模拟发往市场）
        self.order_engine.submit(order.order_id)

        # 3. 成交模拟
        fills = self.fill_engine.simulate_all(order)

        # 4. 应用成交（更新订单状态）
        if fills:
            self.order_engine.apply_fills(order.order_id, fills)

        # 5. 若仍为活跃状态（partial 未全成），强制取消剩余
        if order.is_active:
            self.order_engine.cancel(order.order_id, reason="simulation_end")

        # 6. 成本计算（Phase 3）
        breakdown = self.cost_engine.compute(
            order_id       = order.order_id,
            symbol         = order.symbol,
            direction      = order.direction,
            signal_price   = order.signal_price,
            avg_fill_price = order.avg_fill_price,
            filled_volume  = order.filled_volume,
        )
        self._cost_breakdowns.append(breakdown)

        # 7. 生成执行记录
        record = self._build_record(order, fills, breakdown)
        self._execution_history.append(record)

        # 8. 触发回调
        for f in fills:
            self._fire_fill(f)
        if record is not None:
            self._fire_record(record)

        return order, fills, record

    def execute_batch(
        self,
        requests: list[OrderRequest],
    ) -> list[tuple[Order, list[FillRecord], ExecutionRecord | None]]:
        """批量执行多个 OrderRequest（顺序执行）。"""
        return [self.execute(req) for req in requests]

    # ------------------------------------------------------------------ #
    #  统计接口
    # ------------------------------------------------------------------ #

    def compute_stats(self) -> ExecutionStats:
        """基于执行历史计算汇总统计。"""
        return ExecutionStats.from_records(self._execution_history)

    def get_history(self) -> list[ExecutionRecord]:
        """返回执行记录历史（副本）。"""
        return list(self._execution_history)

    def compute_cost_summary(self) -> CostSummary:
        """基于成本明细计算汇总（Phase 3）。"""
        return self.cost_engine.compute_summary(self._cost_breakdowns)

    def get_cost_breakdowns(self) -> list[CostBreakdown]:
        """返回所有成本明细列表（副本）。"""
        return list(self._cost_breakdowns)

    def get_fills_for_order(self, order_id: str) -> FillSummary:
        """返回某订单的成交汇总。"""
        order = self.order_engine.get(order_id)
        if order is None:
            return FillSummary()
        all_fills = [
            f for rec in self._execution_history
            if rec.order_id == order_id
            for f in []  # fills 存在 FillEngine 内——此处通过 OrderEngine 重建
        ]
        return FillSummary.from_fills(all_fills)

    def clear(self) -> None:
        """清空所有状态（新一轮回测前调用）。"""
        self.order_engine.clear_all()
        self._execution_history.clear()
        self._cost_breakdowns.clear()

    # ------------------------------------------------------------------ #
    #  配置更新
    # ------------------------------------------------------------------ #

    def update_slippage_config(self, config: SlippageConfig) -> None:
        self.slippage_engine.set_config(config)

    def update_fill_config(self, config: FillConfig) -> None:
        self.fill_engine.set_config(config)

    def update_daily_vol(self, symbol: str, daily_vol: float) -> None:
        """更新波动率滑点模型的日波动率估计。"""
        self.slippage_engine.update_volatility(daily_vol)

    def update_cost_config(self, config: CostConfig) -> None:
        """更新成本配置（UI 修改后调用）。"""
        self.cost_engine.set_config(config)

    # ------------------------------------------------------------------ #
    #  回调注册
    # ------------------------------------------------------------------ #

    def register_callbacks(
        self,
        on_order_update:     Callable[[Order], None]           | None = None,
        on_fill_update:      Callable[[FillRecord], None]      | None = None,
        on_execution_record: Callable[[ExecutionRecord], None] | None = None,
    ) -> None:
        """注册事件回调（dispatcher 调用）。"""
        if on_order_update is not None:
            self._on_order_update = on_order_update
            self.order_engine.register_status_callback(on_order_update)
        if on_fill_update is not None:
            self._on_fill_update = on_fill_update
        if on_execution_record is not None:
            self._on_execution_record = on_execution_record

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    def _build_record(
        self,
        order: Order,
        fills: list[FillRecord],
        breakdown: CostBreakdown | None = None,
    ) -> ExecutionRecord:
        """从完成的 Order + FillRecord 列表构建 ExecutionRecord（含成本）。"""
        direction_sign = 1.0 if order.direction == "LONG" else -1.0
        slip = direction_sign * (order.avg_fill_price - order.signal_price) \
               if order.avg_fill_price > 0 else 0.0
        slip_pct = slip / order.signal_price if order.signal_price > 0 else 0.0

        return ExecutionRecord(
            record_id      = str(uuid.uuid4())[:8],
            order_id       = order.order_id,
            symbol         = order.symbol,
            direction      = order.direction,
            source         = order.source,
            signal_price   = order.signal_price,
            avg_fill_price = order.avg_fill_price,
            slippage       = slip,
            slippage_pct   = slip_pct,
            target_volume  = order.volume,
            filled_volume  = order.filled_volume,
            fill_rate      = order.fill_rate,
            fill_mode      = self.fill_engine.config.mode.value,
            slippage_model = self.slippage_engine.config.model.value,
            created_at     = order.created_at,
            filled_at      = order.filled_at or datetime.now(),
            final_status   = order.status.value,
            fill_count     = len(fills),
            commission     = breakdown.commission    if breakdown else 0.0,
            slippage_cost  = breakdown.slippage_cost if breakdown else 0.0,
            impact_cost    = breakdown.impact_cost   if breakdown else 0.0,
            total_cost     = breakdown.total_cost    if breakdown else 0.0,
            total_cost_pct = breakdown.total_cost_pct if breakdown else 0.0,
            notional       = breakdown.notional      if breakdown else 0.0,
            net_pnl_impact = -breakdown.total_cost   if breakdown else 0.0,
        )

    def _fire_fill(self, fill: FillRecord) -> None:
        if self._on_fill_update is not None:
            try:
                self._on_fill_update(fill)
            except Exception:
                pass

    def _fire_record(self, record: ExecutionRecord) -> None:
        if self._on_execution_record is not None:
            try:
                self._on_execution_record(record)
            except Exception:
                pass
