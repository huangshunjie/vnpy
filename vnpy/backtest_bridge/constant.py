"""
backtest_bridge/constant.py

Backtesting Bridge — 枚举常量。
"""
from enum import Enum

APP_NAME = "BacktestBridge"


class SignalSource(Enum):
    """信号来源模块。"""
    ALPHA_FACTORY        = "alpha_factory"       # AlphaFactory 2.0
    MARKET_REGIME        = "market_regime"        # MarketRegimeAI
    DATA_FUSION          = "data_fusion"          # DataIntelligenceAI (DIL)
    PORTFOLIO            = "portfolio"            # PortfolioEngine
    FACTOR               = "factor"              # FactorResearch
    RISK                 = "risk"                # RiskEngine2
    STRATEGY_LIFECYCLE   = "strategy_lifecycle"  # StrategyLifecycleAI
    COMBINED             = "combined"            # 多模块融合信号
    CUSTOM               = "custom"              # 自定义信号


class BridgeMode(Enum):
    """回测驱动模式。"""
    SIGNAL_DRIVEN  = "signal_driven"   # 外部信号驱动（各模块输出 → 回测）
    FACTOR_DRIVEN  = "factor_driven"   # 因子驱动（FactorResearch → 权重）
    FUSION_DRIVEN  = "fusion_driven"   # 融合信号驱动（DIL FusedState → 回测）
    HYBRID         = "hybrid"          # 信号 + 风控 + 规模混合驱动


class RunStatus(Enum):
    """单次回测运行状态。"""
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"


class PositionSizing(Enum):
    """仓位规模方法。"""
    FIXED_UNIT      = "fixed_unit"      # 固定手数
    FIXED_NOTIONAL  = "fixed_notional"  # 固定名义金额
    SIGNAL_SCALED   = "signal_scaled"   # 按信号强度缩放
    RISK_PARITY     = "risk_parity"     # 风险平价
    KELLY           = "kelly"           # Kelly 准则（近似）


class SignalDirection(Enum):
    """信号方向。"""
    LONG    = 1
    FLAT    = 0
    SHORT   = -1
