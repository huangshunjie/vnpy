"""
execution_engine/constant.py

业务枚举常量定义（Phase 1）。
"""

from enum import Enum

APP_NAME: str = "ExecutionEngine"


class OrderStatus(Enum):
    """订单状态（Phase 2 使用）。"""
    CREATED          = "created"
    SUBMITTED        = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED           = "filled"
    CANCELED         = "canceled"
    REJECTED         = "rejected"


class SlippageModel(Enum):
    """滑点模型类型（Phase 2/3 使用）。"""
    FIXED      = "fixed"       # 固定滑点（Tick 数）
    PERCENTAGE = "percentage"  # 百分比滑点
    VOLATILITY = "volatility"  # 波动率自适应滑点


class FillMode(Enum):
    """成交模式（Phase 2 使用）。"""
    IMMEDIATE = "immediate"   # 立即全成
    PARTIAL   = "partial"     # 随机部分成交


class CostType(Enum):
    """成本类型（Phase 3 使用）。"""
    COMMISSION = "commission"  # 手续费
    SLIPPAGE   = "slippage"    # 滑点成本
    IMPACT     = "impact"      # 市场冲击成本


class SignalSource(Enum):
    """执行信号来源（Phase 4）。"""
    MANUAL    = "manual"
    PORTFOLIO = "portfolio"
    CTA       = "cta"
    FACTOR    = "factor"
    BATCH     = "batch"


class PositionAction(Enum):
    """仓位动作（Phase 4 信号解析使用）。"""
    OPEN      = "open"
    CLOSE     = "close"
    REBALANCE = "rebalance"
