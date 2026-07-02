"""
alpha_factory_2/constant.py

Alpha Factory 2.0 枚举常量（Phase 1）。
"""

from enum import Enum

APP_NAME = "AlphaFactory2"
APP_PATH = "alpha_factory_2"


class AlphaStatus(str, Enum):
    GENERATED = "generated"
    SCORED    = "scored"
    SCREENED  = "screened"
    LIVE      = "live"
    DEGRADED  = "degraded"
    RETIRED   = "retired"
    REJECTED  = "rejected"


class AlphaType(str, Enum):
    LINEAR_COMBO  = "linear_combo"   # w1*F1 + w2*F2 + ...
    WEIGHTED      = "weighted"       # 加权组合
    FILTERED      = "filtered"       # 筛选组合
    RANDOM        = "random"         # 随机组合（Phase 2）


class ScoringDimension(str, Enum):
    IC         = "ic"
    RANK_IC    = "rank_ic"
    STABILITY  = "stability"
    TURNOVER   = "turnover"
    DECAY      = "decay"


class ScreeningRule(str, Enum):
    IC_THRESHOLD         = "ic_threshold"
    STABILITY_THRESHOLD  = "stability_threshold"
    DECAY_THRESHOLD      = "decay_threshold"
    LOW_SCORE_RETIRE     = "low_score_retire"
