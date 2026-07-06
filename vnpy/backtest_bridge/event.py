"""
backtest_bridge/event.py

Backtesting Bridge — 事件常量。
"""

APP_NAME = "BacktestBridge"

# ── 生命周期 ──────────────────────────────────────────────────────────
EVENT_BRIDGE_STARTED        = "eBB_BridgeStarted"
EVENT_BRIDGE_STOPPED        = "eBB_BridgeStopped"

# ── 回测任务 ──────────────────────────────────────────────────────────
EVENT_RUN_STARTED           = "eBB_RunStarted"
EVENT_RUN_COMPLETED         = "eBB_RunCompleted"
EVENT_RUN_FAILED            = "eBB_RunFailed"
EVENT_BATCH_COMPLETED       = "eBB_BatchCompleted"

# ── 信号 ──────────────────────────────────────────────────────────────
EVENT_SIGNAL_INJECTED       = "eBB_SignalInjected"
EVENT_SIGNAL_CONSUMED       = "eBB_SignalConsumed"

# ── 结果 ──────────────────────────────────────────────────────────────
EVENT_RESULT_UPDATED        = "eBB_ResultUpdated"
EVENT_COMPARISON_READY      = "eBB_ComparisonReady"

# ── UI ────────────────────────────────────────────────────────────────
EVENT_BRIDGE_LOG            = "eBB_Log"
