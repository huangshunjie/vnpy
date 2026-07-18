"""
strategy_condition/constant.py
模块级枚举常量
"""
from enum import Enum

APP_NAME    = "StrategyCondition"
APP_PATH    = "vnpy.strategy_condition"
APP_VERSION = "1.0.0"


class NodeOp(Enum):
    """条件树节点逻辑运算符"""
    AND  = "AND"
    OR   = "OR"
    NOT  = "NOT"
    LEAF = "LEAF"   # 叶节点（单个条件）


class ConditionCategory(Enum):
    """条件一级分类"""
    TREND      = "trend"
    PULLBACK   = "pullback"
    MOMENTUM   = "momentum"
    VOLUME     = "volume"
    KLINE      = "kline"
    VOLATILITY = "volatility"
    EXIT       = "exit"


class ConditionIndicator(Enum):
    """具体指标标识符"""
    # 趋势
    MA_SLOPE           = "MA_SLOPE"
    WEEKLY_MA_SLOPE    = "WEEKLY_MA_SLOPE"
    MA_ALIGNMENT       = "MA_ALIGNMENT"
    NEW_HIGH_N         = "NEW_HIGH_N"
    # 回调
    PULLBACK_PCT       = "PULLBACK_PCT"
    PULLBACK_FROM_HIGH = "PULLBACK_FROM_HIGH"
    PULLBACK_TO_MA     = "PULLBACK_TO_MA"
    # 动量
    MACD_GOLDEN        = "MACD_GOLDEN"
    MACD_DEATH         = "MACD_DEATH"
    RSI_RANGE          = "RSI_RANGE"
    RETURN_N_DAYS      = "RETURN_N_DAYS"
    # 成交量
    VOLUME_RATIO       = "VOLUME_RATIO"
    VOLUME_PRICE_UP    = "VOLUME_PRICE_UP"
    VOLUME_SHRINK      = "VOLUME_SHRINK"
    # K线行为
    CONTINUOUS_RISE    = "CONTINUOUS_RISE"
    LIMIT_UP_COUNT     = "LIMIT_UP_COUNT"
    BIG_YANG_COUNT     = "BIG_YANG_COUNT"
    KLINE_STRENGTH     = "KLINE_STRENGTH"
    # 波动
    ATR_RATIO          = "ATR_RATIO"
    BOLL_WIDTH         = "BOLL_WIDTH"
    # 卖出
    STOP_LOSS          = "STOP_LOSS"
    TAKE_PROFIT        = "TAKE_PROFIT"
    TRAILING_STOP      = "TRAILING_STOP"
    MAX_HOLD_DAYS      = "MAX_HOLD_DAYS"
    MA_BREAK_DOWN      = "MA_BREAK_DOWN"
    MACD_DEATH_SELL    = "MACD_DEATH_SELL"


class SignalType(Enum):
    BUY  = "BUY"
    SELL = "SELL"


class SignalSource(Enum):
    SCAN     = "scan"
    BACKTEST = "backtest"
    REALTIME = "realtime"
