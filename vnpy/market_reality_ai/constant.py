"""
market_reality_ai/constant.py

Market Reality Simulation System — 枚举常量。
Phase 1: 定义完整，逻辑留待后续阶段实现。
"""
from enum import Enum

APP_NAME     = "MarketRealityAI"
APP_VERSION  = "1.0.0-phase1"


# ── 仿真模式 ──────────────────────────────────────────────────────────
class SimulationMode(Enum):
    EXECUTION_REALITY = "execution_reality"   # Phase 2
    MARKET_IMPACT     = "market_impact"        # Phase 3
    STRESS_TEST       = "stress_test"          # Phase 4
    WALK_FORWARD      = "walk_forward"         # Phase 4
    FAILURE_MODE      = "failure_mode"         # Phase 5
    FULL_SIMULATION   = "full_simulation"      # all phases combined


# ── 仿真运行状态 ──────────────────────────────────────────────────────
class SimulationStatus(Enum):
    IDLE       = "idle"
    RUNNING    = "running"
    PAUSED     = "paused"
    COMPLETED  = "completed"
    FAILED     = "failed"
    ABORTED    = "aborted"


# ── 系统生存评分等级 ──────────────────────────────────────────────────
class SurvivalGrade(Enum):
    """系统生存能力评级（Phase 4/5 计算）。"""
    S   = "S"    # 极端条件下仍可生存
    A   = "A"    # 正常极端事件可生存
    B   = "B"    # 轻度压力可生存，重度有风险
    C   = "C"    # 仅基础条件可生存
    F   = "F"    # 无法生存


# ── 执行现实偏差类型（Phase 2） ───────────────────────────────────────
class ExecutionDeviationType(Enum):
    SLIPPAGE        = "slippage"
    PARTIAL_FILL    = "partial_fill"
    REJECTION       = "rejection"
    LATENCY         = "latency"
    SPREAD_WIDENING = "spread_widening"
    QUEUE_JUMP      = "queue_jump"


# ── 市场冲击类型（Phase 3） ───────────────────────────────────────────
class ImpactType(Enum):
    TEMPORARY  = "temporary"   # 短暂冲击，随后恢复
    PERMANENT  = "permanent"   # 永久价格影响
    DECAY      = "decay"       # 衰减式冲击


# ── 压力场景类型（Phase 4） ───────────────────────────────────────────
class StressScenarioType(Enum):
    FLASH_CRASH          = "flash_crash"
    LIQUIDITY_DRY_UP     = "liquidity_dry_up"
    EXTREME_VOLATILITY   = "extreme_volatility"
    REGIME_COLLAPSE      = "regime_collapse"
    CORRELATION_BREAKDOWN= "correlation_breakdown"
    FAT_TAIL_EVENT       = "fat_tail_event"
    CUSTOM               = "custom"


# ── 失败模式类型（Phase 5） ───────────────────────────────────────────
class FailureModeType(Enum):
    STRATEGY_FAILURE     = "strategy_failure"
    EXECUTION_BREAKDOWN  = "execution_breakdown"
    RISK_OVERFLOW        = "risk_overflow"
    DATA_INCONSISTENCY   = "data_inconsistency"
    LIQUIDITY_FAILURE    = "liquidity_failure"
    LIQUIDITY_CRISIS     = "liquidity_crisis"
    SYSTEM_TIMEOUT       = "system_timeout"
    SYSTEM_OVERLOAD      = "system_overload"
    MODEL_BREAKDOWN      = "model_breakdown"
    CASCADE_FAILURE      = "cascade_failure"


# ── 失败严重度 ────────────────────────────────────────────────────────
class FailureSeverity(Enum):
    LOW      = 1
    MEDIUM   = 2
    HIGH     = 3
    CRITICAL = 4
    FATAL    = 5
