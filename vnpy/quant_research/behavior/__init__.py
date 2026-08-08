"""
quant_research/behavior/__init__.py

K-Line Market Behavior Lab
K线市场行为研究引擎
"""

from .kline_calculator import KLineFeatureCalculator
from .feature_registry import FeatureRegistry, get_global_registry
from .feature_engine import FeatureEngine
from .condition_builder import ConditionBuilder
from .sampling_engine import SamplingEngine
from .event_searcher import EventSearcher
from .forward_analyzer import ForwardReturnAnalyzer
from .statistics import StatisticsEngine

__all__ = [
    "KLineFeatureCalculator",
    "FeatureRegistry",
    "get_global_registry",
    "FeatureEngine",
    "ConditionBuilder",
    "SamplingEngine",
    "EventSearcher", 
    "ForwardReturnAnalyzer",
    "StatisticsEngine",
]
