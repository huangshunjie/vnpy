"""
adaptive_learning_ai/__init__.py
"""
from .app    import AdaptiveLearningApp
from .engine import GlobalLearningEngine
from .constant import (
    APP_NAME, LearningMode, FeedbackType,
    AdaptationTarget, UpdateStrategy, SystemStatus,
)
from .event import (
    EVENT_FEEDBACK_RECEIVED,
    EVENT_LEARNING_STARTED,
    EVENT_MODEL_UPDATED,
    EVENT_SYSTEM_ADAPTED,
    EVENT_LEARNING_CYCLE_COMPLETED,
)

__all__ = [
    "AdaptiveLearningApp",
    "GlobalLearningEngine",
    "APP_NAME",
    "LearningMode",
    "FeedbackType",
    "AdaptationTarget",
    "UpdateStrategy",
    "SystemStatus",
    "EVENT_FEEDBACK_RECEIVED",
    "EVENT_LEARNING_STARTED",
    "EVENT_MODEL_UPDATED",
    "EVENT_SYSTEM_ADAPTED",
    "EVENT_LEARNING_CYCLE_COMPLETED",
]
