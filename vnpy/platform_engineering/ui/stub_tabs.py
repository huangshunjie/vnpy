"""
platform_engineering/ui/stub_tabs.py
Phase 2-8 全部替换为真实实现。
"""
from __future__ import annotations

from .dashboard       import DashboardTab       # Phase 2
from .monitor         import ObservabilityTab   # Phase 2
from .log             import LogTab             # Phase 2
from .task            import TaskTab            # Phase 3
from .deployment      import DeploymentTab      # Phase 4
from .strategy_health import StrategyHealthTab  # Phase 5
from .config          import ConfigTab          # Phase 6
from .api             import ApiTab             # Phase 7
from .security        import SecurityTab        # Phase 8

__all__ = [
    "DashboardTab", "ObservabilityTab", "TaskTab", "DeploymentTab",
    "StrategyHealthTab", "ConfigTab", "ApiTab", "SecurityTab", "LogTab",
]
