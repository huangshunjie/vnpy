"""
execution_engine/engine/fill_engine.py

FillEngine — 成交模拟引擎（Phase 2 实现）。

支持两种成交模式：
  1. IMMEDIATE : 立即全量成交（信号价 + 滑点 → 一次性完成）
  2. PARTIAL   : 随机部分成交（每次触发成交一定比例，直到全成或取消）

设计原则：
  - 无状态计算（成交历史由 OrderEngine 持有）
  - 所有随机数通过 seed 控制，保证回测可复现
  - 返回 FillRecord 列表，调用方自行更新 Order 状态
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime

from ..constant import FillMode
from ..model.fill_model import FillRecord
from ..model.order_model import Order
from .slippage_engine import SlippageEngine, SlippageConfig


@dataclass
class FillConfig:
    """成交模拟配置。"""
    mode:        FillMode = FillMode.IMMEDIATE

    # PARTIAL 模式参数
    min_fill_ratio: float = 0.2    # 单次最小成交比例
    max_fill_ratio: float = 0.8    # 单次最大成交比例
    fill_attempts:  int   = 3      # 最多分几次成交（超过后强制全成）

    # 随机种子（回测可复现）
    random_seed:  int | None = None


class FillEngine:
    """
    成交模拟引擎（无状态，纯函数风格）。

    使用方式：
        engine = FillEngine(fill_config, slippage_engine)
        fills  = engine.simulate(order)
    """

    def __init__(
        self,
        config: FillConfig | None = None,
        slippage_engine: SlippageEngine | None = None,
    ) -> None:
        self.config          = config or FillConfig()
        self.slippage_engine = slippage_engine or SlippageEngine()
        self._rng            = random.Random(self.config.random_seed)

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def simulate(self, order: Order) -> list[FillRecord]:
        """
        对一个活跃订单模拟成交，返回本次产生的 FillRecord 列表。

        Parameters
        ----------
        order : 处于 SUBMITTED 或 PARTIALLY_FILLED 状态的订单

        Returns
        -------
        list[FillRecord]  本次成交记录（可能为空，表示本次未成交）
        """
        if not order.is_active:
            return []
        if order.remaining_volume <= 1e-9:
            return []

        if self.config.mode == FillMode.IMMEDIATE:
            return self._fill_immediate(order)
        elif self.config.mode == FillMode.PARTIAL:
            return self._fill_partial(order)
        return []

    def simulate_all(self, order: Order) -> list[FillRecord]:
        """
        持续模拟直到订单全成或达到最大尝试次数。

        只负责计算并返回 FillRecord 列表，不修改 order 任何字段。
        状态更新由调用方（ExecutionCoreEngine）通过 OrderEngine.apply_fills() 统一完成。
        """
        from datetime import datetime as _dt

        all_fills: list[FillRecord] = []
        remaining   = order.remaining_volume   # 本地变量跟踪剩余量
        attempts    = 0
        max_attempts = self.config.fill_attempts + 1

        while remaining > 1e-9:
            attempts += 1

            if self.config.mode == FillMode.IMMEDIATE:
                vol = remaining
            else:
                ratio = self._rng.uniform(
                    self.config.min_fill_ratio, self.config.max_fill_ratio
                )
                vol = remaining * ratio
                if vol <= 1e-9:
                    break

            price = self.slippage_engine.apply(
                order.signal_price, direction=order.direction, volume=vol
            )
            slip, slip_pct = self.slippage_engine.compute_slippage(
                order.signal_price, price, order.direction
            )
            all_fills.append(FillRecord(
                order_id=order.order_id, symbol=order.symbol,
                direction=order.direction, fill_volume=vol,
                fill_price=price, signal_price=order.signal_price,
                slippage=slip, slippage_pct=slip_pct,
                filled_at=_dt.now(), source=order.source,
            ))
            remaining -= vol

            # IMMEDIATE 模式一次全成
            if self.config.mode == FillMode.IMMEDIATE:
                break

            # 超出最大尝试次数 → 强制成交剩余
            if attempts >= max_attempts and remaining > 1e-9:
                price2 = self.slippage_engine.apply(
                    order.signal_price, direction=order.direction, volume=remaining
                )
                slip2, slip_pct2 = self.slippage_engine.compute_slippage(
                    order.signal_price, price2, order.direction
                )
                all_fills.append(FillRecord(
                    order_id=order.order_id, symbol=order.symbol,
                    direction=order.direction, fill_volume=remaining,
                    fill_price=price2, signal_price=order.signal_price,
                    slippage=slip2, slippage_pct=slip_pct2,
                    filled_at=_dt.now(), source=order.source,
                ))
                break

        return all_fills

    def set_config(self, config: FillConfig) -> None:
        """替换成交配置（UI 修改后调用）。"""
        self.config = config
        self._rng   = random.Random(config.random_seed)

    # ------------------------------------------------------------------ #
    #  内部成交逻辑
    # ------------------------------------------------------------------ #

    def _fill_immediate(self, order: Order) -> list[FillRecord]:
        """立即全量成交：一次性成交全部剩余数量。"""
        vol   = order.remaining_volume
        price = self.slippage_engine.apply(
            order.signal_price,
            direction=order.direction,
            volume=vol,
        )
        slip, slip_pct = self.slippage_engine.compute_slippage(
            order.signal_price, price, order.direction
        )
        return [FillRecord(
            order_id     = order.order_id,
            symbol       = order.symbol,
            direction    = order.direction,
            fill_volume  = vol,
            fill_price   = price,
            signal_price = order.signal_price,
            slippage     = slip,
            slippage_pct = slip_pct,
            filled_at    = datetime.now(),
            source       = order.source,
        )]

    def _fill_partial(self, order: Order) -> list[FillRecord]:
        """
        随机部分成交：本次成交 [min_ratio, max_ratio] × remaining_volume。
        """
        ratio = self._rng.uniform(
            self.config.min_fill_ratio,
            self.config.max_fill_ratio,
        )
        vol   = order.remaining_volume * ratio
        vol   = max(vol, 0.0)

        if vol <= 1e-9:
            return []

        price = self.slippage_engine.apply(
            order.signal_price,
            direction=order.direction,
            volume=vol,
        )
        slip, slip_pct = self.slippage_engine.compute_slippage(
            order.signal_price, price, order.direction
        )
        return [FillRecord(
            order_id     = order.order_id,
            symbol       = order.symbol,
            direction    = order.direction,
            fill_volume  = vol,
            fill_price   = price,
            signal_price = order.signal_price,
            slippage     = slip,
            slippage_pct = slip_pct,
            filled_at    = datetime.now(),
            source       = order.source,
        )]

    def _fill_remaining(self, order: Order) -> list[FillRecord]:
        """强制成交剩余数量（超出最大尝试次数时调用）。"""
        vol = order.remaining_volume
        if vol <= 1e-9:
            return []
        price = self.slippage_engine.apply(
            order.signal_price,
            direction=order.direction,
            volume=vol,
        )
        slip, slip_pct = self.slippage_engine.compute_slippage(
            order.signal_price, price, order.direction
        )
        return [FillRecord(
            order_id     = order.order_id,
            symbol       = order.symbol,
            direction    = order.direction,
            fill_volume  = vol,
            fill_price   = price,
            signal_price = order.signal_price,
            slippage     = slip,
            slippage_pct = slip_pct,
            filled_at    = datetime.now(),
            source       = order.source,
        )]

    @staticmethod
    def _recalc_avg_price(order: Order, new_fill: FillRecord) -> float:
        """重新计算加权平均成交价（增量更新）。"""
        prev_vol = order.filled_volume - new_fill.fill_volume
        prev_val = order.avg_fill_price * prev_vol
        new_val  = new_fill.fill_price  * new_fill.fill_volume
        total    = order.filled_volume
        if total <= 0:
            return new_fill.fill_price
        return (prev_val + new_val) / total
