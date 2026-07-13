"""
market_reality_ai/__init__.py

Market Reality Simulation System — Phase 1 top-level exports.
"""
from .app    import MarketRealityApp
from .engine_main import RealitySimulationEngine
from .constant import (
    APP_NAME, APP_VERSION,
    SimulationMode, SimulationStatus, SurvivalGrade,
    ExecutionDeviationType, ImpactType,
    StressScenarioType, FailureModeType, FailureSeverity,
)
from .event import (
    EVENT_REALITY_STARTED, EVENT_REALITY_STOPPED,
    EVENT_SIMULATION_SESSION_STARTED, EVENT_SIMULATION_SESSION_ENDED,
    EVENT_SIMULATION_ABORTED,
    EVENT_EXECUTION_SIMULATED,
    EVENT_STRESS_TEST_STARTED, EVENT_STRESS_TEST_COMPLETED,
    EVENT_STRESS_SCENARIO_TRIGGERED,
    EVENT_SURVIVAL_SCORE_UPDATED,
    EVENT_WALKFORWARD_STARTED, EVENT_WALKFORWARD_UPDATED,
    EVENT_WALKFORWARD_COMPLETED,
    EVENT_FAILURE_MODE_DETECTED, EVENT_FAILURE_CASCADE_TRIGGERED,
    EVENT_FAILURE_REPORT_READY,
    EVENT_REALITY_LOG, EVENT_REALITY_WARNING, EVENT_REALITY_CRITICAL,
)

__all__ = [
    "MarketRealityApp", "RealitySimulationEngine",
    "APP_NAME", "APP_VERSION",
    "SimulationMode", "SimulationStatus", "SurvivalGrade",
    "ExecutionDeviationType", "ImpactType",
    "StressScenarioType", "FailureModeType", "FailureSeverity",
    "EVENT_REALITY_STARTED", "EVENT_REALITY_STOPPED",
    "EVENT_EXECUTION_SIMULATED",
    "EVENT_STRESS_TEST_STARTED", "EVENT_STRESS_TEST_COMPLETED",
    "EVENT_SURVIVAL_SCORE_UPDATED",
    "EVENT_WALKFORWARD_STARTED", "EVENT_WALKFORWARD_COMPLETED",
    "EVENT_FAILURE_MODE_DETECTED", "EVENT_FAILURE_REPORT_READY",
    "EVENT_REALITY_LOG",
]
