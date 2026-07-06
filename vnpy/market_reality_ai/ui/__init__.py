"""
market_reality_ai/ui/__init__.py
"""
from .widget        import RealitySimulationWidget
from .dashboard_tab import DashboardTab
from .execution_tab import ExecutionTab
from .stress_tab    import StressTab
from .walkforward_tab import WalkForwardTab
from .failure_tab   import FailureTab
from .log_tab       import LogTab

__all__ = [
    "RealitySimulationWidget",
    "DashboardTab", "ExecutionTab", "StressTab",
    "WalkForwardTab", "FailureTab", "LogTab",
]
