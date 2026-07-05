"""
adaptive_learning_ai/constant.py

自适应学习系统枚举常量。
"""
from enum import Enum


class LearningMode(Enum):
    """学习模式。"""
    ONLINE      = "online"       # 实时在线学习
    BATCH       = "batch"        # 批量离线学习
    INCREMENTAL = "incremental"  # 增量学习
    REINFORCED  = "reinforced"   # 强化反馈学习


class FeedbackType(Enum):
    """反馈来源类型。"""
    EXECUTION_SLIPPAGE   = "execution_slippage"
    STRATEGY_PERFORMANCE = "strategy_performance"
    PORTFOLIO_DRIFT      = "portfolio_drift"
    RISK_VIOLATION       = "risk_violation"
    ALPHA_DECAY          = "alpha_decay"
    REGIME_MISMATCH      = "regime_mismatch"


class AdaptationTarget(Enum):
    """自适应目标。"""
    ALPHA_WEIGHTS        = "alpha_weights"
    STRATEGY_ALLOCATION  = "strategy_allocation"
    PORTFOLIO_WEIGHTS    = "portfolio_weights"
    EXECUTION_PARAMS     = "execution_params"
    RISK_THRESHOLDS      = "risk_thresholds"


class UpdateStrategy(Enum):
    """参数更新策略。"""
    REPLACE     = "replace"      # 完全替换
    BLEND       = "blend"        # 加权混合
    INCREMENTAL = "incremental"  # 增量叠加
    ROLLBACK    = "rollback"     # 回滚到上一版本


class SystemStatus(Enum):
    """系统状态。"""
    IDLE       = "idle"
    COLLECTING = "collecting"
    LEARNING   = "learning"
    ADAPTING   = "adapting"
    UPDATING   = "updating"
    STOPPED    = "stopped"


APP_NAME = "AdaptiveLearningAI"
