"""
platform_engineering/constant.py
所有枚举常量定义。
"""
from enum import Enum


class HealthLevel(Enum):
    GREEN  = "green"
    YELLOW = "yellow"
    RED    = "red"


class MetricLayer(Enum):
    DATA     = "data"
    STRATEGY = "strategy"
    TRADING  = "trading"
    SYSTEM   = "system"


class MetricType(Enum):
    GAUGE     = "gauge"
    COUNTER   = "counter"
    HISTOGRAM = "histogram"
    RATE      = "rate"


class TaskStatus(Enum):
    PENDING   = "pending"
    QUEUED    = "queued"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    TIMEOUT   = "timeout"
    RETRYING  = "retrying"


class TaskType(Enum):
    BACKTEST          = "backtest"
    FACTOR_CALC       = "factor_calc"
    ML_TRAINING       = "ml_training"
    VALIDATION        = "validation"
    REPORT_GENERATION = "report_generation"
    DATA_UPDATE       = "data_update"
    CUSTOM            = "custom"


class TaskPriority(Enum):
    LOW    = 0
    NORMAL = 1
    HIGH   = 2
    URGENT = 3


class DeployStage(Enum):
    RESEARCH     = "research"
    VALIDATION   = "validation"
    APPROVAL     = "approval"
    PAPER_TRADING = "paper_trading"
    PRODUCTION   = "production"
    PAUSED       = "paused"
    ROLLED_BACK  = "rolled_back"
    RETIRED      = "retired"


class DeployAction(Enum):
    DEPLOY   = "deploy"
    PAUSE    = "pause"
    RESUME   = "resume"
    ROLLBACK = "rollback"
    FREEZE   = "freeze"
    RETIRE   = "retire"


class HealthStatus(Enum):
    HEALTHY  = "healthy"
    WARNING  = "warning"
    CRITICAL = "critical"
    RETIRE   = "retire"
    UNKNOWN  = "unknown"


class ConfigType(Enum):
    STRATEGY  = "strategy"
    RISK      = "risk"
    EXECUTION = "execution"
    DATA      = "data"
    SYSTEM    = "system"


class UserRole(Enum):
    ADMIN    = "admin"
    MANAGER  = "manager"
    ANALYST  = "analyst"
    TRADER   = "trader"
    VIEWER   = "viewer"


class PermissionAction(Enum):
    READ   = "read"
    WRITE  = "write"
    DEPLOY = "deploy"
    APPROVE = "approve"
    ADMIN  = "admin"


class AlertSeverity(Enum):
    INFO     = "info"
    WARNING  = "warning"
    ERROR    = "error"
    CRITICAL = "critical"


class WorkerStatus(Enum):
    IDLE    = "idle"
    BUSY    = "busy"
    OFFLINE = "offline"
    ERROR   = "error"
