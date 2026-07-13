"""
execution_intelligence_ai/engine/slicing_engine.py  (Phase 2)

SlicingEngine — 智能拆单引擎。

支持四种拆单策略：
  TWAP     — 均匀时间分配
  VWAP     — 历史成交量加权分配
  POV      — 按市场实时成交量百分比参与
  Adaptive — 波动率 + 流动性动态调整
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable

from ..constant import ExecutionStrategy, SliceStatus
from ..model.slicing_model import SlicePlan, OrderSliceState, SlicingParams
from ..utils.slicing_utils import (
    calc_twap_schedule,
    calc_vwap_schedule,
    calc_pov_slice,
    estimate_pov_n_slices,
    build_adaptive_schedule,
    validate_slice_plan,
)
from ..utils.execution_utils import generate_slice_id


class SlicingEngine:
    """
    智能拆单引擎（Phase 2 完整实现）。

    核心职责：
      接收父订单 + SlicingParams → 生成 SlicePlan（切片序列）
      不负责发单 / 路由 / 反馈，只负责"计划"
    """

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log = log_fn or (lambda m: None)
        self._active_plans: dict[str, SlicePlan] = {}  # execution_id → plan

    def init(self) -> None:
        self._log("[SlicingEngine] init()")

    def start(self) -> None:
        self._log("[SlicingEngine] start()")

    def stop(self) -> None:
        self._active_plans.clear()
        self._log("[SlicingEngine] stop()")

    # ------------------------------------------------------------------ #
    #  主入口
    # ------------------------------------------------------------------ #

    def slice_order(
        self,
        execution_id: str,
        order_data: dict,
        params: SlicingParams | None = None,
    ) -> SlicePlan:
        """
        将父订单拆分为切片序列，返回 SlicePlan。

        order_data 必须包含：
          symbol, exchange, direction, total_volume
        可选：target_price, start_dt
        """
        if params is None:
            params = SlicingParams()

        symbol        = order_data.get("symbol", "")
        exchange      = order_data.get("exchange", "")
        direction     = order_data.get("direction", "long")
        total_volume  = float(order_data.get("total_volume", 0.0))
        target_price  = float(order_data.get("target_price", 0.0))
        start_dt      = order_data.get("start_dt", datetime.now())
        if isinstance(start_dt, str):
            start_dt = datetime.fromisoformat(start_dt)

        if total_volume <= 0:
            self._log(f"[SlicingEngine] WARN: total_volume <= 0 for {execution_id}")
            return SlicePlan(execution_id=execution_id,
                             symbol=symbol, exchange=exchange,
                             direction=direction, total_volume=0.0,
                             params=params)

        strategy = params.strategy

        if strategy == ExecutionStrategy.TWAP:
            schedule = self._twap(total_volume, params, start_dt)
        elif strategy == ExecutionStrategy.VWAP:
            schedule = self._vwap(total_volume, params, start_dt)
        elif strategy == ExecutionStrategy.POV:
            schedule = self._pov(total_volume, params, start_dt)
        elif strategy == ExecutionStrategy.ADAPTIVE:
            schedule = self._adaptive(total_volume, params, start_dt)
        else:
            # MARKET / LIMIT — 单片直接发
            schedule = [(start_dt, total_volume)]

        # 应用最小/最大单片量约束
        schedule = self._apply_volume_constraints(schedule, params, total_volume)

        # 构建 OrderSliceState 列表
        slices: list[OrderSliceState] = []
        for i, (sched_t, vol) in enumerate(schedule):
            slices.append(OrderSliceState(
                slice_id     = generate_slice_id(execution_id, i),
                execution_id = execution_id,
                sequence     = i,
                symbol       = symbol,
                exchange     = exchange,
                direction    = direction,
                volume       = vol,
                target_price = target_price,
                status       = SliceStatus.PENDING,
                scheduled_at = sched_t,
            ))

        plan = SlicePlan(
            execution_id = execution_id,
            symbol       = symbol,
            exchange     = exchange,
            direction    = direction,
            total_volume = total_volume,
            params       = params,
            slices       = slices,
        )

        self._active_plans[execution_id] = plan
        self._log(
            f"[SlicingEngine] plan created: {execution_id} "
            f"strategy={strategy.value} n_slices={len(slices)} "
            f"total_vol={total_volume}"
        )
        return plan

    # ------------------------------------------------------------------ #
    #  POV 实时更新（每 bar 调用一次）
    # ------------------------------------------------------------------ #

    def update_pov_slice(
        self,
        execution_id: str,
        market_volume_this_bar: float,
    ) -> OrderSliceState | None:
        """
        POV 模式：根据本 bar 的市场成交量，返回下一个应执行的切片。
        调用方需要自行更新 remaining_volume。
        """
        plan = self._active_plans.get(execution_id)
        if plan is None:
            return None

        remaining = plan.total_volume - plan.total_filled_volume
        if remaining <= 0:
            return None

        params = plan.params
        vol = calc_pov_slice(
            market_volume_this_bar = market_volume_this_bar,
            pov_rate               = params.pov_rate,
            remaining_volume       = remaining,
            min_vol                = params.min_slice_volume,
        )
        if vol <= 0:
            return None

        seq = len(plan.slices)
        new_slice = OrderSliceState(
            slice_id     = generate_slice_id(execution_id, seq),
            execution_id = execution_id,
            sequence     = seq,
            symbol       = plan.symbol,
            exchange     = plan.exchange,
            direction    = plan.direction,
            volume       = vol,
            target_price = 0.0,
            status       = SliceStatus.PENDING,
            scheduled_at = datetime.now(),
        )
        plan.slices.append(new_slice)
        self._log(
            f"[SlicingEngine] POV bar slice: {execution_id} "
            f"seq={seq} vol={vol:.2f} remaining={remaining - vol:.2f}"
        )
        return new_slice

    # ------------------------------------------------------------------ #
    #  状态更新（填报成交）
    # ------------------------------------------------------------------ #

    def mark_slice_filled(
        self,
        execution_id: str,
        slice_id: str,
        filled_volume: float,
        filled_price: float,
    ) -> bool:
        """更新某切片的成交状态，返回是否找到并更新。"""
        plan = self._active_plans.get(execution_id)
        if plan is None:
            return False
        for s in plan.slices:
            if s.slice_id == slice_id:
                s.filled_volume = filled_volume
                s.filled_price  = filled_price
                if s.target_price > 0:
                    sign = 1 if s.direction == "long" else -1
                    s.slippage_bps = round(
                        sign * (filled_price - s.target_price)
                        / s.target_price * 10000, 4)
                s.status    = (SliceStatus.FILLED
                               if filled_volume >= s.volume * 0.999
                               else SliceStatus.PARTIAL)
                s.filled_at = datetime.now()
                return True
        return False

    # ------------------------------------------------------------------ #
    #  查询
    # ------------------------------------------------------------------ #

    def get_plan(self, execution_id: str) -> SlicePlan | None:
        return self._active_plans.get(execution_id)

    def get_all_plans(self) -> list[SlicePlan]:
        return list(self._active_plans.values())

    def summary(self) -> dict:
        return {
            "phase":        2,
            "status":       "active",
            "active_plans": len(self._active_plans),
            "strategies":   [s.value for s in ExecutionStrategy],
        }

    # ------------------------------------------------------------------ #
    #  内部：策略调度
    # ------------------------------------------------------------------ #

    def _twap(
        self,
        total_volume: float,
        params: SlicingParams,
        start_dt: datetime,
    ) -> list[tuple[datetime, float]]:
        return calc_twap_schedule(
            total_volume     = total_volume,
            n_slices         = max(1, params.n_slices),
            start_dt         = start_dt,
            interval_seconds = max(1, params.interval_seconds),
        )

    def _vwap(
        self,
        total_volume: float,
        params: SlicingParams,
        start_dt: datetime,
    ) -> list[tuple[datetime, float]]:
        profile = params.volume_profile
        if not profile:
            # 无历史数据 → 退化为等权 TWAP
            self._log("[SlicingEngine] VWAP: no volume_profile, fallback to TWAP")
            return self._twap(total_volume, params, start_dt)
        return calc_vwap_schedule(
            total_volume     = total_volume,
            volume_profile   = profile,
            start_dt         = start_dt,
            interval_seconds = max(1, params.interval_seconds),
        )

    def _pov(
        self,
        total_volume: float,
        params: SlicingParams,
        start_dt: datetime,
    ) -> list[tuple[datetime, float]]:
        """
        POV 初始计划：用估算片数生成等分骨架（实际执行时由 update_pov_slice 动态调整）。
        """
        n = estimate_pov_n_slices(
            total_volume              = total_volume,
            avg_market_volume_per_bar = total_volume / max(params.n_slices, 1),
            pov_rate                  = params.pov_rate,
        )
        n = max(1, min(n, 500))
        return calc_twap_schedule(
            total_volume     = total_volume,
            n_slices         = n,
            start_dt         = start_dt,
            interval_seconds = max(1, params.interval_seconds),
        )

    def _adaptive(
        self,
        total_volume: float,
        params: SlicingParams,
        start_dt: datetime,
    ) -> list[tuple[datetime, float]]:
        return build_adaptive_schedule(
            total_volume      = total_volume,
            n_slices          = max(1, params.n_slices),
            start_dt          = start_dt,
            interval_seconds  = max(1, params.interval_seconds),
            volatilities      = params.volatility_seq,
            liquidity_scores  = params.liquidity_seq,
        )

    # ------------------------------------------------------------------ #
    #  内部：量约束
    # ------------------------------------------------------------------ #

    def _apply_volume_constraints(
        self,
        schedule: list[tuple[datetime, float]],
        params: SlicingParams,
        total_volume: float,
    ) -> list[tuple[datetime, float]]:
        """强制每片量在 [min_slice_volume, max_slice_volume] 范围内。"""
        min_v = params.min_slice_volume
        max_v = params.max_slice_volume if params.max_slice_volume > 0 else float("inf")

        if min_v <= 0 and max_v == float("inf"):
            return schedule

        constrained: list[tuple[datetime, float]] = []
        for t, vol in schedule:
            vol = max(min_v, min(vol, max_v))
            constrained.append((t, round(vol, 6)))

        # 重新归一化：保持总量不变
        total_c = sum(v for _, v in constrained)
        if total_c <= 0:
            return schedule
        if abs(total_c - total_volume) > 0.01:
            factor = total_volume / total_c
            constrained = [(t, round(v * factor, 6))
                           for t, v in constrained]
            # 尾差补齐
            if constrained:
                allocated = sum(v for _, v in constrained[:-1])
                t_last, _ = constrained[-1]
                constrained[-1] = (t_last, round(total_volume - allocated, 6))

        return constrained
