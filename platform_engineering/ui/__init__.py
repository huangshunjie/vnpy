"""platform_engineering/ui/__init__.py"""
from .widget import PlatformEngineeringWidget
from .stub_tabs import (
    DashboardTab, ObservabilityTab, TaskTab, DeploymentTab,
    StrategyHealthTab, ConfigTab, ApiTab, SecurityTab, LogTab,
)

__all__ = [
    "PlatformEngineeringWidget",
    "DashboardTab", "ObservabilityTab", "TaskTab", "DeploymentTab",
    "StrategyHealthTab", "ConfigTab", "ApiTab", "SecurityTab", "LogTab",
]
