"""
system_integration_bus/constant.py

System Integration Bus — 枚举常量。
"""
from enum import Enum

APP_NAME = "SystemIntegrationBus"


class BusChannel(Enum):
    """总线通道 — 对应系统中每一层的数据流方向。"""
    DATA_INTELLIGENCE   = "data_intelligence"    # DIL 输出
    ALPHA               = "alpha"                # Alpha Factory 输出
    REGIME              = "regime"               # Market Regime 输出
    PORTFOLIO           = "portfolio"            # Portfolio Engine 输出
    CAPITAL             = "capital"              # Capital Allocation 输出
    RISK                = "risk"                 # Risk Engine 输出
    STRATEGY_LIFECYCLE  = "strategy_lifecycle"   # Strategy Lifecycle 输出
    EXECUTION           = "execution"            # Execution Engine 输出
    EXECUTION_INTEL     = "execution_intel"      # Execution Intelligence 输出
    LEARNING            = "learning"             # Adaptive Learning 输出
    GLOBAL_PORTFOLIO    = "global_portfolio"     # Global Portfolio 输出
    SYSTEM              = "system"               # 总线内部系统消息


class PipelineStage(Enum):
    """
    数据管道五阶段（对应 DIL 闭环链路）。

    Data → Feature → Alpha → Portfolio → Execution → Learning
    """
    INGEST    = "ingest"      # Stage 1: 数据接入（DIL）
    SIGNAL    = "signal"      # Stage 2: 信号生成（Alpha + Regime）
    ALLOCATE  = "allocate"    # Stage 3: 组合配置（Portfolio + Capital + Risk）
    EXECUTE   = "execute"     # Stage 4: 执行（Execution + EI）
    LEARN     = "learn"       # Stage 5: 学习反馈（Adaptive Learning）


class BusStatus(Enum):
    """总线运行状态。"""
    IDLE      = "idle"
    RUNNING   = "running"
    PAUSED    = "paused"
    DEGRADED  = "degraded"   # 部分子系统不可用，降级运行
    STOPPED   = "stopped"


class MessagePriority(Enum):
    """消息优先级。"""
    CRITICAL  = 0   # 风险限额触发、熔断
    HIGH      = 1   # Alpha 信号、Regime 切换
    NORMAL    = 2   # 常规数据更新
    LOW       = 3   # 日志、统计


class HealthStatus(Enum):
    """子引擎健康状态。"""
    HEALTHY   = "healthy"
    DEGRADED  = "degraded"
    OFFLINE   = "offline"
    UNKNOWN   = "unknown"
