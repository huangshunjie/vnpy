"""
execution_intelligence_ai/constant.py

Execution Intelligence 2.0 — 全局枚举常量。
"""

from enum import Enum

APP_NAME = "ExecutionIntelligenceAI"


class ExecutionStrategy(Enum):
    """执行策略类型。"""
    TWAP     = "twap"       # 时间加权均价
    VWAP     = "vwap"       # 成交量加权均价
    POV      = "pov"        # 成交量百分比
    ADAPTIVE = "adaptive"   # 自适应
    MARKET   = "market"     # 直接市价
    LIMIT    = "limit"      # 直接限价


class SliceStatus(Enum):
    """子订单状态。"""
    PENDING   = "pending"
    SUBMITTED = "submitted"
    PARTIAL   = "partial"
    FILLED    = "filled"
    CANCELLED = "cancelled"
    FAILED    = "failed"


class ImpactLevel(Enum):
    """市场冲击等级。"""
    NEGLIGIBLE = "negligible"   # 可忽略
    LOW        = "low"
    MEDIUM     = "medium"
    HIGH       = "high"
    SEVERE     = "severe"


class RoutingMode(Enum):
    """路由模式。"""
    BEST_PRICE  = "best_price"
    MIN_SLIPPAGE = "min_slippage"
    FASTEST     = "fastest"
    BALANCED    = "balanced"


class ExecutionPhase(Enum):
    """执行生命周期阶段。"""
    IDLE       = "idle"
    PLANNING   = "planning"
    EXECUTING  = "executing"
    MONITORING = "monitoring"
    COMPLETED  = "completed"
    ABORTED    = "aborted"


class FeedbackMetric(Enum):
    """执行质量指标。"""
    SLIPPAGE      = "slippage"
    FILL_RATE     = "fill_rate"
    LATENCY       = "latency"
    MARKET_IMPACT = "market_impact"
    EXECUTION_COST = "execution_cost"
    VWAP_DEVIATION = "vwap_deviation"
