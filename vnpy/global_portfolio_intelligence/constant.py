"""
global_portfolio_intelligence/constant.py

全局组合智能系统枚举常量。
"""
from enum import Enum


class OptimizationMode(Enum):
    """全局优化模式。"""
    SHARPE     = "sharpe"       # 最大化夏普比率
    DRAWDOWN   = "drawdown"     # 最小化最大回撤
    CAPACITY   = "capacity"     # 最大化容量利用率
    STABILITY  = "stability"    # 最大化收益稳定性
    BALANCED   = "balanced"     # 多目标加权均衡


class RebalanceTrigger(Enum):
    """再平衡触发类型。"""
    RISK_DRIFT          = "risk_drift"
    ALPHA_DECAY         = "alpha_decay"
    EXECUTION_INEFFICIENCY = "execution_inefficiency"
    REGIME_SHIFT        = "regime_shift"
    SCHEDULED           = "scheduled"
    MANUAL              = "manual"


class AllocationMode(Enum):
    """资金分配模式。"""
    EQUAL           = "equal"
    PERFORMANCE     = "performance"
    REGIME_BASED    = "regime_based"
    RISK_PARITY     = "risk_parity"


class SystemStatus(Enum):
    """系统运行状态。"""
    IDLE        = "idle"
    RUNNING     = "running"
    OPTIMIZING  = "optimizing"
    REBALANCING = "rebalancing"
    STOPPED     = "stopped"


APP_NAME = "GlobalPortfolioIntelligence"
