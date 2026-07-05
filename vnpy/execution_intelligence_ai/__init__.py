"""
execution_intelligence_ai  —  Execution Intelligence 2.0
Phase 1 (skeleton) package exports.
"""

from .app    import ExecutionIntelligenceApp
from .dispatcher import ExecutionIntelligenceEngine
from .constant import (
    APP_NAME,
    ExecutionStrategy,
    SliceStatus,
    ImpactLevel,
    RoutingMode,
    ExecutionPhase,
    FeedbackMetric,
)
from .event import (
    EVENT_EXECUTION_START,
    EVENT_ORDER_SLICED,
    EVENT_IMPACT_ESTIMATED,
    EVENT_ROUTE_SELECTED,
    EVENT_EXECUTION_COMPLETED,
    EVENT_FEEDBACK_UPDATED,
    EVENT_EXECUTION_ABORTED,
)
from .model.execution_model import ExecutionState
from .model.slicing_model   import OrderSliceState
from .model.impact_model    import ImpactState
from .model.routing_model   import RoutingState
from .model.feedback_model  import FeedbackState

__all__ = [
    "APP_NAME",
    "ExecutionIntelligenceApp",
    "ExecutionIntelligenceEngine",
    # constants
    "ExecutionStrategy",
    "SliceStatus",
    "ImpactLevel",
    "RoutingMode",
    "ExecutionPhase",
    "FeedbackMetric",
    # events
    "EVENT_EXECUTION_START",
    "EVENT_ORDER_SLICED",
    "EVENT_IMPACT_ESTIMATED",
    "EVENT_ROUTE_SELECTED",
    "EVENT_EXECUTION_COMPLETED",
    "EVENT_FEEDBACK_UPDATED",
    "EVENT_EXECUTION_ABORTED",
    # models
    "ExecutionState",
    "OrderSliceState",
    "ImpactState",
    "RoutingState",
    "FeedbackState",
]
