"""
strategy_lifecycle_ai  —  Strategy Lifecycle Intelligence System
Phase 5 (Final) complete package exports.
"""

from .app        import StrategyLifecycleApp
from .dispatcher import LifecycleEngine
from .constant   import (
    APP_NAME,
    StrategyPhase,
    PerformanceRating,
    DecayLevel,
    EvolutionType,
    RetirementReason,
)
from .event import (
    EVENT_STRATEGY_REGISTERED,
    EVENT_STRATEGY_UPDATED,
    EVENT_STRATEGY_DECAY_DETECTED,
    EVENT_STRATEGY_EVOLVED,
    EVENT_STRATEGY_RETIRED,
    EVENT_PERFORMANCE_UPDATE,
    EVENT_DECAY_LEVEL_CHANGED,
    EVENT_EVOLUTION_TRIGGERED,
    EVENT_LIFECYCLE_HEARTBEAT,
)
from .model.strategy_model    import StrategyState
from .model.performance_model import PerformanceState, PerformanceHistory
from .model.decay_model       import DecayState, DecayHistory
from .model.evolution_model   import EvolutionRecord, EvolutionHistory
from .engine.retirement_engine import RetirementEvaluation, RetirementRecord

__all__ = [
    "APP_NAME",
    "StrategyLifecycleApp",
    "LifecycleEngine",
    # constants
    "StrategyPhase",
    "PerformanceRating",
    "DecayLevel",
    "EvolutionType",
    "RetirementReason",
    # events
    "EVENT_STRATEGY_REGISTERED",
    "EVENT_STRATEGY_UPDATED",
    "EVENT_STRATEGY_DECAY_DETECTED",
    "EVENT_STRATEGY_EVOLVED",
    "EVENT_STRATEGY_RETIRED",
    "EVENT_PERFORMANCE_UPDATE",
    "EVENT_DECAY_LEVEL_CHANGED",
    "EVENT_EVOLUTION_TRIGGERED",
    "EVENT_LIFECYCLE_HEARTBEAT",
    # models
    "StrategyState",
    "PerformanceState",
    "PerformanceHistory",
    "DecayState",
    "DecayHistory",
    "EvolutionRecord",
    "EvolutionHistory",
    "RetirementEvaluation",
    "RetirementRecord",
]
