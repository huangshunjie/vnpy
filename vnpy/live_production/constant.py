"""
live_production/constant.py

Live Production System 枚举常量（Phase 1 定义，Phase 2+ 实现状态机）。
"""

from enum import Enum

APP_NAME    = "LiveProduction"
APP_PATH    = "live_production"


class TradingState(str, Enum):
    """实盘交易状态机。"""
    INIT      = "init"
    RUNNING   = "running"
    DEGRADED  = "degraded"    # 部分模块异常，降级运行
    RECOVERY  = "recovery"    # 恢复中
    STOPPED   = "stopped"


class SystemHealthState(str, Enum):
    """系统整体健康等级。"""
    HEALTHY   = "healthy"
    WARNING   = "warning"
    CRITICAL  = "critical"
    UNKNOWN   = "unknown"


class OrderSyncState(str, Enum):
    """订单同步状态。"""
    SYNCED    = "synced"      # 本地与交易所一致
    PENDING   = "pending"     # 等待确认
    MISMATCH  = "mismatch"    # 不一致，需要对账
    REPAIRING = "repairing"   # 修复中


class FailoverMode(str, Enum):
    """故障切换模式。"""
    FULL       = "full"        # 全功能运行
    PARTIAL    = "partial"     # 部分降级
    SAFE_MODE  = "safe_mode"   # 安全模式（只平仓，不开仓）
