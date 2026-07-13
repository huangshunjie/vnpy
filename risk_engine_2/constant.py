"""
risk_engine_2/constant.py

风控系统枚举常量（Phase 1 占位，Phase 2+ 填充）。
"""

from enum import Enum

APP_NAME: str = "RiskEngine2"


class RiskLevel(Enum):
    """风险等级（Phase 2）。"""
    NORMAL   = "normal"    # 正常
    WARNING  = "warning"   # 预警
    CRITICAL = "critical"  # 严重
    BREACH   = "breach"    # 已突破限制


class LimitType(Enum):
    """限制类型（Phase 2）。"""
    POSITION    = "position"     # 单票仓位
    TOTAL       = "total"        # 总仓位
    LEVERAGE    = "leverage"     # 杠杆
    BETA        = "beta"         # Beta 暴露
    INDUSTRY    = "industry"     # 行业集中度
    DRAWDOWN    = "drawdown"     # 最大回撤
    DAILY_LOSS  = "daily_loss"   # 当日亏损


class AlertType(Enum):
    """预警类型（Phase 3）。"""
    POSITION_BREACH  = "position_breach"
    LEVERAGE_BREACH  = "leverage_breach"
    DRAWDOWN_BREACH  = "drawdown_breach"
    DAILY_LOSS_BREACH= "daily_loss_breach"
    SYSTEM_ERROR     = "system_error"


class RiskAction(Enum):
    """风控动作（Phase 3）。"""
    ALERT            = "alert"           # 仅告警，不阻断
    BLOCK            = "block"           # 阻断该笔订单
    REDUCE_POSITION  = "reduce_position" # 触发减仓
    HALT_TRADING     = "halt_trading"    # 暂停交易
