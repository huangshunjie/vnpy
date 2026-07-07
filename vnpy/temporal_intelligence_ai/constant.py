"""
temporal_intelligence_ai/constant.py

时间智能系统枚举常量。
"""
from enum import Enum


APP_NAME = "TemporalIntelligenceAI"


class CyclePhase(Enum):
    """市场周期阶段。"""
    EXPANSION   = "expansion"    # 扩张期
    PEAK        = "peak"         # 顶部
    CONTRACTION = "contraction"  # 收缩期
    TROUGH      = "trough"       # 底部
    TRANSITION  = "transition"   # 过渡期
    UNKNOWN     = "unknown"


class DecayMode(Enum):
    """Alpha 衰减模式。"""
    EXPONENTIAL        = "exponential"         # 指数衰减
    REGIME_DEPENDENT   = "regime_dependent"    # Regime 依赖衰减
    VOLATILITY_ADJUSTED = "volatility_adjusted" # 波动率调整衰减


class RegimeType(Enum):
    """市场 Regime 类型。"""
    BULL_QUIET       = "bull_quiet"        # 牛市低波动
    BULL_VOLATILE    = "bull_volatile"     # 牛市高波动
    BEAR_QUIET       = "bear_quiet"        # 熊市低波动
    BEAR_VOLATILE    = "bear_volatile"     # 熊市高波动
    SIDEWAYS         = "sideways"          # 横盘整理
    CRISIS           = "crisis"            # 危机状态
    UNKNOWN          = "unknown"


class SignalHorizon(Enum):
    """信号时间维度。"""
    SHORT_TERM  = "short_term"   # 短期 (t-1 ~ t-5)
    MID_TERM    = "mid_term"     # 中期 (t-5 ~ t-20)
    LONG_TERM   = "long_term"    # 长期结构 (t-20+)


class TransitionType(Enum):
    """状态转移类型。"""
    REGIME_SHIFT         = "regime_shift"          # 市场 Regime 切换
    VOLATILITY_BREAK     = "volatility_break"       # 波动率突破
    LIQUIDITY_REGIME     = "liquidity_regime"       # 流动性 Regime 变化
    CYCLE_TRANSITION     = "cycle_transition"       # 周期阶段转换


class TemporalSystemStatus(Enum):
    """系统运行状态。"""
    IDLE      = "idle"
    RUNNING   = "running"
    ANALYZING = "analyzing"
    STOPPED   = "stopped"
    ERROR     = "error"
