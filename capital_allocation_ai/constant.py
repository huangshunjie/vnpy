"""
capital_allocation_ai/constant.py

Capital Allocation Intelligence System 枚举常量（Phase 1）。
"""

from enum import Enum

APP_NAME = "CapitalAllocationAI"
APP_PATH = "capital_allocation_ai"


class AllocationStatus(str, Enum):
    PENDING    = "pending"
    ACTIVE     = "active"
    REDUCED    = "reduced"
    SUSPENDED  = "suspended"
    RETIRED    = "retired"


class ScoringDimension(str, Enum):
    IC_MEAN    = "ic_mean"
    STABILITY  = "stability"
    CAPACITY   = "capacity"
    DECAY      = "decay"
    SHARPE     = "sharpe"


class RebalanceTrigger(str, Enum):
    SCHEDULED  = "scheduled"    # 定时再平衡
    RISK       = "risk"         # 风险超限触发
    SCORE      = "score"        # 评分变化触发
    MANUAL     = "manual"       # 手动触发


class RiskBudgetType(str, Enum):
    VOLATILITY = "volatility"
    DRAWDOWN   = "drawdown"
    EXPOSURE   = "exposure"


class CapitalFlowDirection(str, Enum):
    INCREASE   = "increase"     # 增加资金
    DECREASE   = "decrease"     # 减少资金
    TRANSFER   = "transfer"     # 资金迁移
    HOLD       = "hold"         # 维持不变
