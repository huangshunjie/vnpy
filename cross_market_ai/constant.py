"""
cross_market_ai/constant.py

Cross-Market Intelligence System — 枚举常量。
Phase 1: 定义完整，逻辑留待后续阶段实现。
"""
from enum import Enum

APP_NAME    = "CrossMarketAI"
APP_VERSION = "1.0.0-phase1"


class MarketType(Enum):
    """支持的市场类型（market-agnostic 设计）。"""
    EQUITY_CN       = "equity_cn"        # A股（沪深）
    FUTURES_CN      = "futures_cn"       # 国内商品/金融期货
    EQUITY_US       = "equity_us"        # 美股
    CRYPTO          = "crypto"           # 加密货币
    FOREX           = "forex"            # 外汇
    FIXED_INCOME    = "fixed_income"     # 固定收益
    CUSTOM          = "custom"           # 自定义市场


class MappingStatus(Enum):
    """市场结构映射状态。"""
    IDLE        = "idle"
    RUNNING     = "running"
    COMPLETED   = "completed"
    FAILED      = "failed"


class TransferStatus(Enum):
    """Alpha 迁移状态。"""
    IDLE        = "idle"
    TRANSFERRING = "transferring"
    COMPLETED   = "completed"
    REJECTED    = "rejected"


class RegimeAlignStatus(Enum):
    """Regime 对齐状态。"""
    IDLE      = "idle"
    ALIGNING  = "aligning"
    ALIGNED   = "aligned"
    DIVERGED  = "diverged"


class UniversalityGrade(Enum):
    """Alpha 普适性等级。"""
    UNIVERSAL   = "universal"    # 跨所有市场成立
    PORTABLE    = "portable"     # 可迁移至相似结构市场
    LOCAL       = "local"        # 仅在原市场有效
    FRAGILE     = "fragile"      # 结构依赖极强，不可迁移


class ValidationStatus(Enum):
    """跨市场验证状态。"""
    IDLE        = "idle"
    RUNNING     = "running"
    PASSED      = "passed"
    DEGRADED    = "degraded"
    FAILED      = "failed"


class EngineStatus(Enum):
    """顶层引擎运行状态。"""
    IDLE     = "idle"
    RUNNING  = "running"
    STOPPED  = "stopped"
