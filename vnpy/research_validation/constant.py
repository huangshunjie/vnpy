"""
research_validation/constant.py

Research Validation System 常量定义（Phase 1）。
"""

from enum import Enum


APP_NAME = "ResearchValidation"


class ValidationStatus(Enum):
    """验证任务状态。"""
    IDLE       = "idle"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    CANCELLED  = "cancelled"


class RegimeType(Enum):
    """市场状态类型（Phase 3）。"""
    BULL      = "bull"       # 牛市
    BEAR      = "bear"       # 熊市
    SIDEWAYS  = "sideways"   # 横盘震荡
    UNKNOWN   = "unknown"    # 无法识别


class BiasType(Enum):
    """偏差类型（Phase 5）。"""
    LOOK_AHEAD    = "look_ahead"     # 前视偏差
    DATA_LEAKAGE  = "data_leakage"   # 数据泄露
    SURVIVORSHIP  = "survivorship"   # 幸存者偏差


class StabilityLevel(Enum):
    """因子稳定性等级（Phase 4）。"""
    HIGH    = "high"     # IC > 0.05，稳定
    MEDIUM  = "medium"   # IC 0.02 ~ 0.05，中等
    LOW     = "low"      # IC < 0.02，不稳定
    INVALID = "invalid"  # 数据不足，无法判断


class ValidationWindow(Enum):
    """Walk Forward 窗口类型（Phase 2）。"""
    TRAIN = "train"
    TEST  = "test"


class OOSSplit(Enum):
    """OOS 数据切分方式（Phase 2）。"""
    TIME_BASED   = "time_based"    # 按时间切分（推荐）
    RATIO_BASED  = "ratio_based"   # 按比例切分
