"""
strategy_lifecycle_ai/constant.py  (Phase 1)

Strategy Lifecycle Intelligence System — 枚举常量。
"""

from enum import Enum

APP_NAME = "StrategyLifecycleAI"


class StrategyPhase(Enum):
    """策略生命周期阶段。"""
    REGISTERED = "registered"   # 已注册，未激活
    INCUBATION = "incubation"   # 孵化期（新策略观察期）
    LIVE       = "live"         # 正常运行
    PEAK       = "peak"         # 表现峰值
    DECAY      = "decay"        # 衰减期
    RECOVERING = "recovering"   # 恢复中（进化后）
    RETIRED    = "retired"      # 已退役
    ARCHIVED   = "archived"     # 已归档


class DecayLevel(Enum):
    """衰减程度。"""
    NONE     = "none"       # 无衰减
    MILD     = "mild"       # 轻微衰减
    MODERATE = "moderate"   # 中度衰减
    SEVERE   = "severe"     # 严重衰减
    CRITICAL = "critical"   # 危急（触发退役）


class EvolutionType(Enum):
    """策略进化类型。"""
    NONE           = "none"             # 无进化
    PARAM_MUTATION = "param_mutation"   # 参数变异
    WEIGHT_ADJUST  = "weight_adjust"    # 因子权重调整
    RECOMBINATION  = "recombination"    # 策略重组
    CLONING        = "cloning"          # 强策略克隆


class RetirementReason(Enum):
    """退役原因。"""
    MANUAL           = "manual"            # 手动退役
    PERSISTENT_DECAY = "persistent_decay"  # 持续衰减
    NEGATIVE_SHARPE  = "negative_sharpe"   # Sharpe 为负
    DRAWDOWN_BREACH  = "drawdown_breach"   # 回撤超限
    LOW_ACTIVITY     = "low_activity"      # 长期低活跃


class PerformanceRating(Enum):
    """策略表现评级。"""
    EXCELLENT = "excellent"   # ≥ 2.0 Sharpe
    GOOD      = "good"        # ≥ 1.0 Sharpe
    NEUTRAL   = "neutral"     # ≥ 0.0 Sharpe
    WEAK      = "weak"        # < 0.0 Sharpe
    UNKNOWN   = "unknown"     # 数据不足
