"""
backtest_bridge/__init__.py
"""
from .app    import BacktestBridgeApp
from .engine import BacktestBridgeEngine
from .constant import (
    APP_NAME, SignalSource, BridgeMode, RunStatus,
    PositionSizing, SignalDirection,
)
from .event import (
    EVENT_BRIDGE_STARTED, EVENT_BRIDGE_STOPPED,
    EVENT_RUN_STARTED, EVENT_RUN_COMPLETED, EVENT_RUN_FAILED,
    EVENT_BATCH_COMPLETED, EVENT_SIGNAL_INJECTED,
    EVENT_RESULT_UPDATED, EVENT_COMPARISON_READY, EVENT_BRIDGE_LOG,
)

__all__ = [
    "BacktestBridgeApp", "BacktestBridgeEngine",
    "APP_NAME", "SignalSource", "BridgeMode", "RunStatus",
    "PositionSizing", "SignalDirection",
    "EVENT_BRIDGE_STARTED", "EVENT_BRIDGE_STOPPED",
    "EVENT_RUN_STARTED", "EVENT_RUN_COMPLETED", "EVENT_RUN_FAILED",
    "EVENT_BATCH_COMPLETED", "EVENT_SIGNAL_INJECTED",
    "EVENT_RESULT_UPDATED", "EVENT_COMPARISON_READY", "EVENT_BRIDGE_LOG",
]
