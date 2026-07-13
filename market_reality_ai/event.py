"""
market_reality_ai/event.py

Market Reality Simulation System — 事件常量。
Phase 1: 定义全部事件名称，供 engine 派发和 UI 订阅。
"""

APP_NAME = "MarketRealityAI"

# ── 生命周期 ──────────────────────────────────────────────────────────
EVENT_REALITY_STARTED             = "eRS_RealityStarted"
EVENT_REALITY_STOPPED             = "eRS_RealityStopped"

# ── 仿真会话 ──────────────────────────────────────────────────────────
EVENT_SIMULATION_SESSION_STARTED  = "eRS_SessionStarted"
EVENT_SIMULATION_SESSION_ENDED    = "eRS_SessionEnded"
EVENT_SIMULATION_ABORTED          = "eRS_SimulationAborted"

# ── Phase 2: 执行现实 ─────────────────────────────────────────────────
EVENT_EXECUTION_SIMULATED         = "eRS_ExecutionSimulated"
EVENT_SLIPPAGE_RECORDED           = "eRS_SlippageRecorded"
EVENT_FILL_DEGRADED               = "eRS_FillDegraded"
EVENT_ORDER_REJECTED              = "eRS_OrderRejected"
EVENT_LATENCY_RECORDED            = "eRS_LatencyRecorded"

# ── Phase 3: 市场冲击 ─────────────────────────────────────────────────
EVENT_IMPACT_ESTIMATED            = "eRS_ImpactEstimated"
EVENT_LIQUIDITY_STATE_UPDATED     = "eRS_LiquidityStateUpdated"
EVENT_SPREAD_WIDENED              = "eRS_SpreadWidened"

# ── Phase 4: 压力测试 ─────────────────────────────────────────────────
EVENT_STRESS_TEST_STARTED         = "eRS_StressTestStarted"
EVENT_STRESS_TEST_COMPLETED       = "eRS_StressTestCompleted"
EVENT_STRESS_SCENARIO_TRIGGERED   = "eRS_StressScenarioTriggered"
EVENT_SURVIVAL_SCORE_UPDATED      = "eRS_SurvivalScoreUpdated"

# ── Phase 4: Walk-Forward ────────────────────────────────────────────
EVENT_WALKFORWARD_STARTED         = "eRS_WalkForwardStarted"
EVENT_WALKFORWARD_UPDATED         = "eRS_WalkForwardUpdated"
EVENT_WALKFORWARD_COMPLETED       = "eRS_WalkForwardCompleted"

# ── Phase 5: 失败模式 ─────────────────────────────────────────────────
EVENT_FAILURE_MODE_DETECTED       = "eRS_FailureModeDetected"
EVENT_FAILURE_CASCADE_TRIGGERED   = "eRS_FailureCascadeTriggered"
EVENT_FAILURE_REPORT_READY        = "eRS_FailureReportReady"

# ── 日志 ──────────────────────────────────────────────────────────────
EVENT_REALITY_LOG                 = "eRS_Log"
EVENT_REALITY_WARNING             = "eRS_Warning"
EVENT_REALITY_CRITICAL            = "eRS_Critical"
