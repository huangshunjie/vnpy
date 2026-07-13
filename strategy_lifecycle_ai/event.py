"""
strategy_lifecycle_ai/event.py  (Phase 1)

Strategy Lifecycle Intelligence System — 事件常量。
"""

# Phase 1 — 生命周期核心事件
EVENT_STRATEGY_REGISTERED     = "eStrategyRegistered"
EVENT_STRATEGY_UPDATED        = "eStrategyUpdated"
EVENT_STRATEGY_DECAY_DETECTED = "eStrategyDecayDetected"
EVENT_STRATEGY_EVOLVED        = "eStrategyEvolved"
EVENT_STRATEGY_RETIRED        = "eStrategyRetired"

# Phase 2+ 扩展事件
EVENT_PERFORMANCE_UPDATE      = "eStrategyPerformanceUpdate"
EVENT_DECAY_LEVEL_CHANGED     = "eStrategyDecayLevelChanged"
EVENT_EVOLUTION_TRIGGERED     = "eStrategyEvolutionTriggered"
EVENT_LIFECYCLE_HEARTBEAT     = "eStrategyLifecycleHeartbeat"
