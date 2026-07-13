"""
performance_monitor/constant.py

Performance Monitor — 枚举常量。
"""
from enum import Enum

APP_NAME = "PerformanceMonitor"

# ── 16个受监控模块 ────────────────────────────────────────────────────
MONITORED_MODULES = [
    "data_intelligence_ai",
    "alpha_factory_2",
    "market_regime_ai",
    "portfolio_engine",
    "capital_allocation_ai",
    "risk_engine_2",
    "strategy_lifecycle_ai",
    "execution_engine",
    "execution_intelligence_ai",
    "adaptive_learning_ai",
    "global_portfolio_intelligence",
    "live_production",
    "quant_os",
    "factor_research",
    "research_validation",
    "system_integration_bus",
]


class MetricType(Enum):
    """指标类型。"""
    LATENCY     = "latency"      # 事件间延迟 (ms)
    THROUGHPUT  = "throughput"   # 事件吞吐量 (events/min)
    ERROR_RATE  = "error_rate"   # 错误率 [0,1]
    EVENT_COUNT = "event_count"  # 累计事件数
    QUEUE_DEPTH = "queue_depth"  # 队列深度（未处理消息数）
    UPTIME      = "uptime"       # 模块存活时间 (s)
    CUSTOM      = "custom"       # 自定义指标


class AlertLevel(Enum):
    """告警级别（严重程度升序）。"""
    INFO     = "info"
    WARNING  = "warning"
    CRITICAL = "critical"
    FATAL    = "fatal"


class ModuleStatus(Enum):
    """模块运行状态。"""
    UNKNOWN   = "unknown"
    ACTIVE    = "active"      # 有事件流动
    IDLE      = "idle"        # 存活但无近期事件
    DEGRADED  = "degraded"    # 错误率升高 / 延迟过大
    OFFLINE   = "offline"     # 超时无心跳


class AggWindow(Enum):
    """聚合时间窗口。"""
    W10S  = 10     # 10秒
    W1M   = 60     # 1分钟
    W5M   = 300    # 5分钟
    W15M  = 900    # 15分钟
    W1H   = 3600   # 1小时
