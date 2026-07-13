"""
execution_engine/engine/cost_engine.py

CostEngine — 交易成本建模（Phase 3 实现）。

支持三类成本：
  1. COMMISSION : 手续费（固定金额 / 按成交额百分比 / 按手数固定）
  2. SLIPPAGE   : 滑点成本（来自 FillRecord，已由 SlippageEngine 计算）
  3. IMPACT     : 市场冲击成本（简化 square-root 模型）

输出：
  CostBreakdown  — 单笔订单的成本明细
  CostSummary    — 多笔订单的成本汇总
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from ..constant import CostType


# ─────────────────────────────────────────────────────────────────────────────
#  配置
# ─────────────────────────────────────────────────────────────────────────────

class CommissionMode(Enum):
    FIXED_PER_ORDER  = "fixed_per_order"   # 每笔订单固定费用
    RATE_ON_NOTIONAL = "rate_on_notional"  # 按成交额百分比（最常见）
    FIXED_PER_LOT    = "fixed_per_lot"     # 每手固定费用


@dataclass
class CostConfig:
    """成本模型配置。"""
    # 手续费
    commission_mode:  CommissionMode = CommissionMode.RATE_ON_NOTIONAL
    commission_rate:  float = 0.0003    # 0.03% 双边（买卖各一次）
    commission_fixed: float = 5.0       # FIXED_PER_ORDER / FIXED_PER_LOT 时使用

    # 市场冲击（square-root 模型）：impact = impact_factor × σ × √(Q/V)
    # impact_factor : 冲击系数（经验值 0.1~1.0）
    # daily_volume  : 日均成交量（用于相对量计算）
    impact_factor:  float = 0.3
    daily_volume:   float = 10000.0     # 日均成交量（手数）

    # 合约乘数（计算名义价值时使用）
    contract_multiplier: float = 1.0


# ─────────────────────────────────────────────────────────────────────────────
#  输出数据结构
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CostBreakdown:
    """
    单笔订单的完整成本明细。

    所有成本均为正值，代表对 PnL 的负面影响。
    net_impact = slippage_cost + commission + impact_cost
    """
    order_id:   str   = ""
    symbol:     str   = ""
    direction:  str   = ""

    # 价格
    signal_price:   float = 0.0
    avg_fill_price: float = 0.0
    filled_volume:  float = 0.0

    # 各成本分项（绝对金额，未乘合约乘数）
    slippage_cost:  float = 0.0    # = |avg_fill - signal| × volume
    commission:     float = 0.0    # 手续费
    impact_cost:    float = 0.0    # 市场冲击成本

    # 汇总
    total_cost:     float = 0.0    # = slippage_cost + commission + impact_cost
    net_impact:     float = 0.0    # = total_cost（方向中立，始终为正）

    # 成本率（相对于名义价值）
    total_cost_pct: float = 0.0    # total_cost / notional

    # 名义价值
    notional:       float = 0.0    # avg_fill_price × filled_volume × multiplier

    @property
    def cost_breakdown_str(self) -> str:
        return (
            f"手续费={self.commission:.4f}  "
            f"滑点={self.slippage_cost:.4f}  "
            f"冲击={self.impact_cost:.4f}  "
            f"合计={self.total_cost:.4f}  "
            f"成本率={self.total_cost_pct:.4%}"
        )


@dataclass
class CostSummary:
    """多笔订单的成本汇总统计。"""
    total_orders:       int   = 0

    # 成本汇总
    total_commission:   float = 0.0
    total_slippage:     float = 0.0
    total_impact:       float = 0.0
    total_cost:         float = 0.0
    total_notional:     float = 0.0

    # 平均成本率
    avg_cost_pct:       float = 0.0
    avg_commission_pct: float = 0.0
    avg_slippage_pct:   float = 0.0
    avg_impact_pct:     float = 0.0

    # 成本占比（各项 / total_cost）
    commission_share:   float = 0.0
    slippage_share:     float = 0.0
    impact_share:       float = 0.0

    # 各笔明细（用于图表）
    breakdowns: list[CostBreakdown] = field(default_factory=list)

    @classmethod
    def from_breakdowns(cls, bds: list[CostBreakdown]) -> "CostSummary":
        if not bds:
            return cls()
        s = cls(total_orders=len(bds), breakdowns=bds)
        s.total_commission = sum(b.commission    for b in bds)
        s.total_slippage   = sum(b.slippage_cost for b in bds)
        s.total_impact     = sum(b.impact_cost   for b in bds)
        s.total_cost       = sum(b.total_cost    for b in bds)
        s.total_notional   = sum(b.notional      for b in bds)

        if s.total_notional > 0:
            s.avg_cost_pct       = s.total_cost       / s.total_notional
            s.avg_commission_pct = s.total_commission / s.total_notional
            s.avg_slippage_pct   = s.total_slippage   / s.total_notional
            s.avg_impact_pct     = s.total_impact     / s.total_notional

        if s.total_cost > 0:
            s.commission_share = s.total_commission / s.total_cost
            s.slippage_share   = s.total_slippage   / s.total_cost
            s.impact_share     = s.total_impact     / s.total_cost

        return s


# ─────────────────────────────────────────────────────────────────────────────
#  CostEngine
# ─────────────────────────────────────────────────────────────────────────────

class CostEngine:
    """
    交易成本计算引擎（无状态，纯函数风格）。

    使用方式：
        engine   = CostEngine(config)
        breakdown = engine.compute(order, fills, daily_vol=0.015)
    """

    def __init__(self, config: CostConfig | None = None) -> None:
        self.config = config or CostConfig()

    # ------------------------------------------------------------------ #
    #  主接口
    # ------------------------------------------------------------------ #

    def compute(
        self,
        order_id:       str,
        symbol:         str,
        direction:      str,
        signal_price:   float,
        avg_fill_price: float,
        filled_volume:  float,
        daily_vol:      float = 0.015,
    ) -> CostBreakdown:
        """
        计算单笔订单的完整成本明细。

        Parameters
        ----------
        order_id       : 订单 ID
        symbol         : 合约代码
        direction      : "LONG" / "SHORT"
        signal_price   : 信号触发价
        avg_fill_price : 实际平均成交价
        filled_volume  : 成交数量
        daily_vol      : 日波动率（用于冲击成本计算，默认 1.5%）
        """
        if filled_volume <= 0 or avg_fill_price <= 0:
            return CostBreakdown(
                order_id=order_id, symbol=symbol, direction=direction,
                signal_price=signal_price, avg_fill_price=avg_fill_price,
            )

        cfg        = self.config
        multiplier = cfg.contract_multiplier
        notional   = avg_fill_price * filled_volume * multiplier

        # 1. 手续费
        commission = self._calc_commission(notional, filled_volume)

        # 2. 滑点成本（价格偏移 × 数量）
        if direction == "LONG":
            slip_abs = avg_fill_price - signal_price
        else:
            slip_abs = signal_price - avg_fill_price
        slippage_cost = max(slip_abs, 0.0) * filled_volume * multiplier

        # 3. 市场冲击成本（square-root 模型）
        impact_cost = self._calc_impact(
            signal_price, filled_volume, daily_vol, multiplier
        )

        total_cost    = commission + slippage_cost + impact_cost
        total_cost_pct = total_cost / notional if notional > 0 else 0.0

        return CostBreakdown(
            order_id        = order_id,
            symbol          = symbol,
            direction       = direction,
            signal_price    = signal_price,
            avg_fill_price  = avg_fill_price,
            filled_volume   = filled_volume,
            slippage_cost   = slippage_cost,
            commission      = commission,
            impact_cost     = impact_cost,
            total_cost      = total_cost,
            net_impact      = total_cost,
            total_cost_pct  = total_cost_pct,
            notional        = notional,
        )

    def compute_summary(
        self,
        breakdowns: list[CostBreakdown],
    ) -> CostSummary:
        """从多个 CostBreakdown 计算汇总。"""
        return CostSummary.from_breakdowns(breakdowns)

    def set_config(self, config: CostConfig) -> None:
        """替换成本配置（UI 修改后调用）。"""
        self.config = config

    def update_daily_volume(self, daily_volume: float) -> None:
        """更新日均成交量（动态行情数据）。"""
        if daily_volume > 0:
            self.config.daily_volume = daily_volume

    # ------------------------------------------------------------------ #
    #  内部计算
    # ------------------------------------------------------------------ #

    def _calc_commission(self, notional: float, volume: float) -> float:
        cfg = self.config
        mode = cfg.commission_mode
        if mode == CommissionMode.RATE_ON_NOTIONAL:
            return notional * cfg.commission_rate
        elif mode == CommissionMode.FIXED_PER_ORDER:
            return cfg.commission_fixed
        elif mode == CommissionMode.FIXED_PER_LOT:
            return cfg.commission_fixed * volume
        return 0.0

    def _calc_impact(
        self,
        signal_price: float,
        volume:       float,
        daily_vol:    float,
        multiplier:   float,
    ) -> float:
        """
        简化 square-root 市场冲击模型。

        impact_cost = impact_factor × σ × √(Q/V) × P × Q × multiplier

        其中：
          σ = daily_vol（日波动率）
          Q = 成交数量（手数）
          V = 日均成交量（手数）
          P = 信号价格
        """
        cfg = self.config
        if cfg.daily_volume <= 0 or volume <= 0:
            return 0.0

        participation = volume / cfg.daily_volume
        sqrt_part     = math.sqrt(max(participation, 0.0))
        impact_price  = (cfg.impact_factor
                         * daily_vol
                         * sqrt_part
                         * signal_price)
        return impact_price * volume * multiplier
