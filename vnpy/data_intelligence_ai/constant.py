"""
data_intelligence_ai/constant.py

数据智能系统枚举常量。
"""
from enum import Enum


class DataType(Enum):
    """数据类型。"""
    MARKET     = "market"        # 行情数据
    ALPHA      = "alpha"         # Alpha 因子
    EXECUTION  = "execution"     # 执行反馈
    PORTFOLIO  = "portfolio"     # 组合状态
    RISK       = "risk"          # 风险信号
    REGIME     = "regime"        # 市场状态


class FeatureType(Enum):
    """特征类型。"""
    PRICE       = "price"
    VOLUME      = "volume"
    VOLATILITY  = "volatility"
    ALPHA       = "alpha"
    REGIME      = "regime"
    EXECUTION   = "execution"


class QualityStatus(Enum):
    """数据质量状态。"""
    CLEAN      = "clean"
    MISSING    = "missing"
    OUTLIER    = "outlier"
    DELAYED    = "delayed"
    INCONSISTENT = "inconsistent"
    UNKNOWN    = "unknown"


class FusionMode(Enum):
    """融合模式。"""
    WEIGHTED_AVERAGE = "weighted_average"
    LATEST_WINS      = "latest_wins"
    CONSENSUS        = "consensus"
    REGIME_AWARE     = "regime_aware"


class SystemStatus(Enum):
    """系统状态。"""
    IDLE       = "idle"
    INGESTING  = "ingesting"
    COMPUTING  = "computing"
    FUSING     = "fusing"
    STREAMING  = "streaming"
    STOPPED    = "stopped"


APP_NAME = "DataIntelligenceAI"
