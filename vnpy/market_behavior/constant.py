"""
market_behavior/constant.py
枚举常量定义
"""
from enum import Enum

APP_NAME    = "MarketBehavior"
APP_PATH    = "vnpy.market_behavior"
APP_VERSION = "1.0.0"


# ── 交易板块（涨跌停规则依赖） ────────────────────────────────────────
class BoardType(Enum):
    MAIN     = "main"       # 主板  ±10%
    STAR     = "star"       # 科创板 ±20%  首5日 ±无限
    GEM      = "gem"        # 创业板 ±20%  首5日 ±无限
    BSE      = "bse"        # 北交所 ±30%
    ST       = "st"         # ST    ±5%
    ST_STAR  = "st_star"    # *ST   ±5%


# ── 价格事件类型 ──────────────────────────────────────────────────────
class EventType(Enum):
    LIMIT_UP         = "limit_up"          # 涨停
    LIMIT_DOWN       = "limit_down"        # 跌停
    NEAR_LIMIT_UP    = "near_limit_up"     # 接近涨停（≥ threshold）
    NEAR_LIMIT_DOWN  = "near_limit_down"   # 接近跌停
    RISE_PCT         = "rise_pct"          # 大涨 N%
    FALL_PCT         = "fall_pct"          # 大跌 N%
    HIGH_VOLUME      = "high_volume"       # 放量
    LOW_VOLUME       = "low_volume"        # 缩量
    GAP_UP           = "gap_up"            # 向上跳空
    GAP_DOWN         = "gap_down"          # 向下跳空


# ── 连续行为类型 ──────────────────────────────────────────────────────
class ContinuousType(Enum):
    RISE             = "continuous_rise"     # 连续上涨
    FALL             = "continuous_fall"     # 连续下跌
    NEW_HIGH         = "continuous_new_high" # 连续创新高
    NEW_LOW          = "continuous_new_low"  # 连续创新低
    VOLUME_UP        = "continuous_vol_up"   # 连续放量
    VOLUME_DOWN      = "continuous_vol_down" # 连续缩量


# ── 单K形态类型 ───────────────────────────────────────────────────────
class PatternType(Enum):
    # 实体形态
    BIG_YANG             = "big_yang"              # 大阳线
    BIG_YIN              = "big_yin"               # 大阴线
    SMALL_YANG           = "small_yang"            # 小阳线
    SMALL_YIN            = "small_yin"             # 小阴线
    CONT_BIG_YANG        = "cont_big_yang"         # 连续大阳线
    CONT_BIG_YIN         = "cont_big_yin"          # 连续大阴线
    # 十字星系列
    DOJI                 = "doji"                  # 标准十字星
    GRAVESTONE_DOJI      = "gravestone_doji"       # 墓碑十字
    DRAGONFLY_DOJI       = "dragonfly_doji"        # 蜻蜓十字
    # 影线形态
    LONG_UPPER_SHADOW    = "long_upper_shadow"     # 长上影线
    LONG_LOWER_SHADOW    = "long_lower_shadow"     # 长下影线
    HAMMER               = "hammer"                # 锤子线
    INVERTED_HAMMER      = "inverted_hammer"       # 倒锤子线
    SHOOTING_STAR        = "shooting_star"         # 射击之星（流星线）
    # 走势形态
    HIGH_OPEN_LOW_CLOSE  = "high_open_low_close"   # 高开低走
    LOW_OPEN_HIGH_CLOSE  = "low_open_high_close"   # 低开高走
    # 旧别名（向后兼容）
    LONG_UPPER           = "long_upper"            # 长上影（旧名）
    LONG_LOWER           = "long_lower"            # 长下影（旧名）
    GAP_HIGH_OPEN        = "gap_high_open"         # 高开低走（旧名）
    GAP_LOW_OPEN         = "gap_low_open"          # 低开高走（旧名）


# ── K线组合模式类型 ───────────────────────────────────────────────────
class SequenceType(Enum):
    MORNING_STAR     = "morning_star"      # 早晨之星
    EVENING_STAR     = "evening_star"      # 黄昏之星
    THREE_WHITE      = "three_white"       # 三白兵
    THREE_BLACK      = "three_black"       # 三黑鸦
    YANG_YIN_YANG    = "yang_yin_yang"     # 两阳夹一阴
    YIN_YANG_YIN     = "yin_yang_yin"      # 两阴夹一阳
    BULLISH_ENGULF   = "bullish_engulf"    # 看涨吞没
    BEARISH_ENGULF   = "bearish_engulf"    # 看跌吞没
    DOUBLE_BOTTOM    = "double_bottom"     # 双底
    DOUBLE_TOP       = "double_top"        # 双顶
    CUSTOM           = "custom"            # 自定义 DSL


# ── 突破类型 ──────────────────────────────────────────────────────────
class BreakoutType(Enum):
    NEW_HIGH_N       = "new_high_n"        # N日新高
    NEW_LOW_N        = "new_low_n"         # N日新低
    VOLUME_BREAKOUT  = "volume_breakout"   # 量能突破
    VOLATILITY_BREAK = "volatility_break"  # 波动突破
    MA_CROSS_UP      = "ma_cross_up"       # 均线向上突破
    MA_CROSS_DOWN    = "ma_cross_down"     # 均线向下突破


# ── 行为因子类型 ──────────────────────────────────────────────────────
class FactorType(Enum):
    RISE_DAYS        = "rise_days"         # 上涨天数
    FALL_DAYS        = "fall_days"         # 下跌天数
    LIMIT_UP_COUNT   = "limit_up_count"    # 涨停次数
    LIMIT_DOWN_COUNT = "limit_down_count"  # 跌停次数
    BIG_YANG_COUNT   = "big_yang_count"    # 大阳线次数
    BREAKOUT_COUNT   = "breakout_count"    # 突破次数
    LONG_UPPER_COUNT = "long_upper_count"  # 长上影次数
    VOLATILITY       = "volatility"        # 波动强度
    KLINE_STRENGTH   = "kline_strength"    # 综合K线强度


# ── 行为标签类型 ──────────────────────────────────────────────────────
class LabelType(Enum):
    TREND_STRONG     = "trend_strong"      # 强趋势
    TREND_WEAK       = "trend_weak"        # 弱趋势
    CONTINUOUS_RISE  = "continuous_rise"   # 连续上涨
    LIMIT_DENSE      = "limit_dense"       # 涨停密集
    BREAKOUT         = "breakout"          # 突破
    HIGH_VOLATILITY  = "high_volatility"   # 高波动
    REVERSAL         = "reversal"          # 反转信号
    CONSOLIDATION    = "consolidation"     # 盘整


# ── 规则逻辑运算符 ────────────────────────────────────────────────────
class RuleOperator(Enum):
    AND = "and"
    OR  = "or"
    NOT = "not"


# ── 回测结果状态 ──────────────────────────────────────────────────────
class BacktestStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
