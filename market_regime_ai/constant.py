"""
market_regime_ai/constant.py

Market Regime Intelligence System — 枚举常量（Phase 1）。
"""

from enum import Enum
from pathlib import Path

APP_NAME = "MarketRegimeAI"
APP_PATH = Path(__file__).parent


class MarketRegime(str, Enum):
    """市场状态（顶层分类）。"""
    BULL        = "bull"           # 牛市 / 上涨趋势
    BEAR        = "bear"           # 熊市 / 下跌趋势
    SIDEWAYS    = "sideways"       # 震荡 / 横盘
    HIGH_VOL    = "high_vol"       # 高波动状态
    LOW_LIQ     = "low_liq"        # 低流动性状态
    UNKNOWN     = "unknown"        # 未知 / 初始化中


class VolatilityRegime(str, Enum):
    """波动率状态。"""
    LOW         = "low"
    NORMAL      = "normal"
    HIGH        = "high"
    EXTREME     = "extreme"


class TrendDirection(str, Enum):
    """趋势方向。"""
    STRONG_UP   = "strong_up"
    WEAK_UP     = "weak_up"
    FLAT        = "flat"
    WEAK_DOWN   = "weak_down"
    STRONG_DOWN = "strong_down"


class LiquidityLevel(str, Enum):
    """流动性水平。"""
    HIGH        = "high"
    NORMAL      = "normal"
    LOW         = "low"
    VERY_LOW    = "very_low"


class RegimeConfidence(str, Enum):
    """状态判断置信度。"""
    HIGH        = "high"      # > 0.75
    MEDIUM      = "medium"    # 0.50 ~ 0.75
    LOW         = "low"       # < 0.50


class StrategyRecommendation(str, Enum):
    """策略推荐（Phase 4 实现）。"""
    MOMENTUM        = "momentum"         # Bull → 动量
    DEFENSIVE       = "defensive"        # Bear → 防御
    MEAN_REVERSION  = "mean_reversion"   # Sideways → 均值回归
    RISK_REDUCTION  = "risk_reduction"   # High Vol → 降险
    REDUCE_FREQ     = "reduce_freq"      # Low Liq → 降频
    NEUTRAL         = "neutral"          # 无明确建议
