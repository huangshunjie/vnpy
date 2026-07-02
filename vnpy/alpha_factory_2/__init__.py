"""
alpha_factory_2/__init__.py

Alpha Factory 2.0 — 工业化Alpha生产系统（Phase 1）。
"""

from .app      import AlphaFactory2App
from .constant import AlphaStatus, AlphaType, ScoringDimension, APP_NAME

__all__ = [
    "AlphaFactory2App",
    "AlphaStatus",
    "AlphaType",
    "ScoringDimension",
    "APP_NAME",
]
