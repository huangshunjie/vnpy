"""
screening/constant.py

Quant Screening Platform — 枚举常量（Phase 1）。
"""

from enum import Enum
from pathlib import Path

APP_NAME = "QuantScreening"
APP_PATH = Path(__file__).parent


class MarketUniverse(str, Enum):
    """市场股票池。"""
    ALL_A          = "all_a"           # 全市场 A 股
    CSI_300        = "csi_300"         # 沪深300
    CSI_500        = "csi_500"         # 中证500
    CSI_1000       = "csi_1000"        # 中证1000
    CUSTOM         = "custom"          # 自定义


class UniverseFilter(str, Enum):
    """基础过滤规则类型。"""
    EXCLUDE_ST          = "exclude_st"           # 排除 ST / *ST
    EXCLUDE_SUSPENDED   = "exclude_suspended"     # 排除停牌
    EXCLUDE_DELISTING   = "exclude_delisting"     # 排除退市整理
    MIN_LISTING_DAYS    = "min_listing_days"      # 最低上市天数
    MIN_DAILY_TURNOVER  = "min_daily_turnover"    # 最低日均成交额
    MIN_MARKET_CAP      = "min_market_cap"        # 最低市值


class ConditionOperator(str, Enum):
    """条件逻辑运算符。"""
    AND = "AND"
    OR  = "OR"
    NOT = "NOT"


class CompareOperator(str, Enum):
    """数值比较运算符。"""
    GT  = ">"
    GTE = ">="
    LT  = "<"
    LTE = "<="
    EQ  = "=="
    NEQ = "!="


class ConditionFieldType(str, Enum):
    """条件字段来源类型。"""
    FUNDAMENTAL = "fundamental"   # 基本面：ROE、PE、PB 等
    TECHNICAL   = "technical"     # 技术面：MA、RSI、MACD 等
    CAPITAL     = "capital"       # 资金面：成交额、换手率等
    FACTOR      = "factor"        # 因子值（来自 Alpha Factory）
    RISK        = "risk"          # 风险指标：波动率、Beta 等


class ScoreMethod(str, Enum):
    """多因子评分加权方式。"""
    EQUAL_WEIGHT = "equal_weight"   # 等权
    IC_WEIGHT    = "ic_weight"      # IC 加权
    ICIR_WEIGHT  = "icir_weight"    # ICIR 加权
    MANUAL       = "manual"         # 手动指定权重


class RankDirection(str, Enum):
    """因子排序方向。"""
    ASC  = "asc"   # 升序（值越小越好，如 PE）
    DESC = "desc"  # 降序（值越大越好，如 ROE）


class PortfolioWeightMethod(str, Enum):
    """组合权重方式。"""
    EQUAL        = "equal"          # 等权
    MARKET_CAP   = "market_cap"     # 市值权重
    RISK_PARITY  = "risk_parity"    # 风险平价
    OPTIMIZED    = "optimized"      # 优化权重


class ScreeningStatus(str, Enum):
    """选股任务状态。"""
    IDLE      = "idle"
    RUNNING   = "running"
    DONE      = "done"
    ERROR     = "error"


class TemplateCategory(str, Enum):
    """选股模板分类。"""
    VALUE    = "value"      # 价值选股
    GROWTH   = "growth"     # 成长选股
    QUALITY  = "quality"    # 质量选股
    MOMENTUM = "momentum"   # 动量选股
    MULTI    = "multi"      # 多因子策略
    CUSTOM   = "custom"     # 自定义
