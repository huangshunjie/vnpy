"""
factor_research/constant.py

Factor Research 模块常量与枚举定义。

第一阶段只定义骨架，所有枚举值在后续阶段按需扩充。
严禁在此文件中写算法或业务逻辑。
"""

from enum import Enum


class FactorType(Enum):
    """因子类型"""
    ALPHA = "alpha"           # 选股因子
    RISK = "risk"             # 风险因子
    TECHNICAL = "technical"   # 技术因子
    FUNDAMENTAL = "fundamental"  # 基本面因子
    MACRO = "macro"           # 宏观因子


class FrequencyType(Enum):
    """因子数据频率"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class NormalizationMethod(Enum):
    """因子标准化方法（预留）"""
    ZSCORE = "zscore"
    RANK = "rank"
    MINMAX = "minmax"


class NeutralizeMethod(Enum):
    """因子中性化方法（预留）"""
    MARKET = "market"
    INDUSTRY = "industry"
    MARKET_INDUSTRY = "market_industry"


class FactorStatus(Enum):
    """因子计算任务状态"""
    IDLE = "idle"
    RUNNING = "running"
    FINISHED = "finished"
    ERROR = "error"


# --------------------------------------------------------------------------- #
#  App 级常量
# --------------------------------------------------------------------------- #

APP_NAME: str = "FactorResearch"

FACTOR_RESEARCH_VERSION: str = "0.1.0"
