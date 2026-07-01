"""
portfolio_engine/constant.py

枚举常量定义。所有业务枚举集中在此，不依赖任何其他模块。
"""

from enum import Enum


class WeightMethod(Enum):
    """权重分配方法。"""
    EQUAL             = "equal"           # 等权：w_i = 1/N
    VOLATILITY_TARGET = "vol_target"      # 波动率目标：w_i ∝ 1/σ_i
    RISK_PARITY       = "risk_parity"     # 风险平价：w_i ∝ 1/RC_i
    FACTOR_DRIVEN     = "factor_driven"   # 因子驱动：由 FactorBridge 提供权重


class RebalanceFreq(Enum):
    """调仓频率。"""
    DAILY   = "daily"
    WEEKLY  = "weekly"
    MONTHLY = "monthly"
    MANUAL  = "manual"


class RiskMetric(Enum):
    """风险指标类型（Phase 3 使用）。"""
    BETA             = "beta"
    SECTOR_EXPOSURE  = "sector"
    FACTOR_EXPOSURE  = "factor"
    DRAWDOWN         = "drawdown"


class StrategyType(Enum):
    """策略类型（用于 StrategySlot 标记）。"""
    CTA    = "cta"
    FACTOR = "factor"
    CUSTOM = "custom"


APP_NAME: str = "PortfolioEngine"
