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
    AND      = "AND"
    OR       = "OR"
    NOT      = "NOT"
    SEQUENCE = "SEQUENCE"   # 顺序组：子条件按时间先后依次发生
    LEAF     = "LEAF"       # 叶节点（单个条件）


class ConditionCategory(Enum):
    """条件一级分类"""
    TREND      = "trend"
    PULLBACK   = "pullback"
    MOMENTUM   = "momentum"
    VOLUME     = "volume"
    KLINE      = "kline"
    VOLATILITY = "volatility"
    TIME       = "time"      # 时间/日内过滤
    EXIT       = "exit"
    STRENGTH   = "strength"   # 强势股
    DEVIATION  = "deviation"  # 均线偏离
    MARKET     = "market"     # 市场环境
    SCORE      = "score"      # 综合评分


class ConditionIndicator(Enum):
    """具体指标标识符"""
    # 趋势
    MA_SLOPE           = "MA_SLOPE"
    WEEKLY_MA_SLOPE    = "WEEKLY_MA_SLOPE"
    MA_ALIGNMENT       = "MA_ALIGNMENT"
    NEW_HIGH_N         = "NEW_HIGH_N"
    # 趋势升级
    MA_SLOPE_UP        = "MA_SLOPE_UP"          # MA斜率向上(指定周期)
    TREND_STRENGTH     = "TREND_STRENGTH"       # 均线趋势强度
    TREND_DAYS         = "TREND_DAYS"           # 趋势持续天数
    PRICE_ABOVE_MA     = "PRICE_ABOVE_MA"       # 价格站上均线
    TREND_INTACT       = "TREND_INTACT"         # 趋势未破坏
    MA_DEVIATIONFILTER = "MA_DEVIATION_FILTER" # MA乖离过滤
    MA_BINDONG         = "MA_BINDONG"           # 均线粘合
    TREND_SCORE        = "TREND_SCORE"          # 趋势评分

    # 回调
    PULLBACK_PCT       = "PULLBACK_PCT"
    PULLBACK_FROM_HIGH = "PULLBACK_FROM_HIGH"
    PULLBACK_TO_MA     = "PULLBACK_TO_MA"
    # 回调升级
    PULLBACK_TO_MA5    = "PULLBACK_TO_MA5"      # 回踩MA5
    PULLBACK_TO_MA10   = "PULLBACK_TO_MA10"     # 回踩MA10
    PULLBACK_TO_MA20   = "PULLBACK_TO_MA20"     # 回踩MA20
    PULLBACK_TO_MA30   = "PULLBACK_TO_MA30"     # 回踩MA30
    MA_DISTANCEPCT    = "MA_DISTANCE_PCT"      # 距离均线百分比
    RETRACEMENT_PCT    = "RETRACEMENT_PCT"      # 回撤幅度
    FIRST_PULLBACK     = "FIRST_PULLBACK"       # 首次回踩
    SHRINK_PULLBACK    = "SHRINK_PULLBACK"      # 缩量回调
    YIN_PULLBACK       = "YIN_PULLBACK"         # 阴线回调
    STRONG_PULLBACK_SCORE = "STRONG_PULLBACK_SCORE"  # 强势回调评分

    # 动量
    MACD_GOLDEN        = "MACD_GOLDEN"
    MACD_DEATH         = "MACD_DEATH"
    RSI_RANGE          = "RSI_RANGE"
    RETURN_N_DAYS      = "RETURN_N_DAYS"

    # 成交量
    VOLUME_RATIO       = "VOLUME_RATIO"
    VOLUME_PRICE_UP    = "VOLUME_PRICE_UP"
    VOLUME_SHRINK      = "VOLUME_SHRINK"
    # 成交量升级
    VOLUME_UP_PHASE    = "VOLUME_UP_PHASE"      # 上涨阶段量能
    VOLUME_LAYER       = "VOLUME_LAYER"         # 分层量能(VolumeLayerFactor)
    SHRINK_PULLBACK_VOL = "SHRINK_PULLBACK_VOL" # 缩量回调(量)
    VOLUME_YIN_FILTER  = "VOLUME_YIN_FILTER"    # 放量阴线过滤
    VOLUME_DIVERGENCE  = "VOLUME_DIVERGENCE"    # 量价背离
    VOLUME_TREND       = "VOLUME_TREND"         # 成交量趋势
    FUND_INTENSITY     = "FUND_INTENSITY"       # 资金介入强度

    # K线行为
    CONTINUOUS_RISE    = "CONTINUOUS_RISE"
    LIMIT_UP_COUNT     = "LIMIT_UP_COUNT"
    BIG_YANG_COUNT     = "BIG_YANG_COUNT"
    KLINE_STRENGTH     = "KLINE_STRENGTH"
    # K线升级
    KLINE_YIN          = "KLINE_YIN"            # 阴线
    KLINE_YANG         = "KLINE_YANG"           # 阳线
    KLINE_SHRINK_YIN   = "KLINE_SHRINK_YIN"     # 缩量阴线
    KLINE_VOL_YIN      = "KLINE_VOL_YIN"        # 放量阴线
    KLINE_LONG_LOWER   = "KLINE_LONG_LOWER"     # 长下影
    KLINE_DOJI         = "KLINE_DOJI"           # 十字星
    KLINE_BIG_YANG     = "KLINE_BIG_YANG"       # 大阳线(单根)
    KLINE_LIMIT_UP     = "KLINE_LIMIT_UP"       # 涨停K线
    KLINE_COMBO        = "KLINE_COMBO"          # K线组合

    # 波动
    ATR_RATIO          = "ATR_RATIO"
    BOLL_WIDTH         = "BOLL_WIDTH"

    # 强势股
    STRENGTH_RETURN_N  = "STRENGTH_RETURN_N"    # N日涨幅
    STRENGTH_MAX_GAIN  = "STRENGTH_MAX_GAIN"    # 最大涨幅
    STRENGTH_STAGE_HIGH = "STRENGTH_STAGE_HIGH" # 阶段新高
    STRENGTH_LIMIT_UP_COUNT = "STRENGTH_LIMIT_UP_COUNT"  # 涨停次数
    STRENGTH_BIG_YANG_COUNT = "STRENGTH_BIG_YANG_COUNT"  # 大阳线次数
    STRENGTH_VOL_BREAK = "STRENGTH_VOL_BREAK"   # 放量突破
    STRENGTH_SCORE     = "STRENGTH_SCORE"       # 强势股评分

    # 均线偏离
    DEV_MA5            = "DEV_MA5"              # MA5乖离率
    DEV_MA10           = "DEV_MA10"             # MA10乖离率
    DEV_MA20           = "DEV_MA20"             # MA20乖离率
    DEV_MA10_MA20      = "DEV_MA10_MA20"        # MA10-MA20距离
    DEV_OVERBOUGHT     = "DEV_OVERBOUGHT"       # 超涨过滤
    DEV_MA_DISTANCE    = "DEV_MA_DISTANCE"      # 均线距离过滤

    # 市场环境
    MARKET_INDEX_TREND = "MARKET_INDEX_TREND"   # 指数趋势
    MARKET_INDEX_MA    = "MARKET_INDEX_MA"      # 指数均线状态
    MARKET_UP_RATIO    = "MARKET_UP_RATIO"      # 涨跌比例
    MARKET_LIMIT_UP    = "MARKET_LIMIT_UP"      # 涨停数量
    MARKET_LIMIT_DOWN  = "MARKET_LIMIT_DOWN"    # 跌停数量
    MARKET_RISK        = "MARKET_RISK"          # 市场风险状态

    # 综合评分
    SCORE_NODE         = "SCORE_NODE"           # 评分节点

    # 卖出
    STOP_LOSS          = "STOP_LOSS"
    TAKE_PROFIT        = "TAKE_PROFIT"
    TRAILING_STOP      = "TRAILING_STOP"
    MAX_HOLD_DAYS      = "MAX_HOLD_DAYS"
    MA_BREAK_DOWN      = "MA_BREAK_DOWN"
    MACD_DEATH_SELL    = "MACD_DEATH_SELL"
    # 时间过滤
    TIME_OF_DAY        = "TIME_OF_DAY"


class SignalType(Enum):
    BUY  = "BUY"
    SELL = "SELL"


class SignalSource(Enum):
    SCAN     = "scan"
    BACKTEST = "backtest"
    REALTIME = "realtime"
