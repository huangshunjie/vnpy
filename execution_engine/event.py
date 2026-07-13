"""
execution_engine/event.py

事件常量定义（Phase 1 基础 + Phase 4 上游信号）。
"""

# ── Phase 1：内部执行事件 ────────────────────────────────────────────────────
EVENT_EXECUTION_LOG   = "eExecutionLog"
EVENT_ORDER_UPDATE    = "eOrderUpdate"
EVENT_FILL_UPDATE     = "eFillUpdate"
EVENT_EXECUTION_ERROR = "eExecutionError"

# ── Phase 4：上游信号事件（监听外部模块） ────────────────────────────────────
# Portfolio Engine → Execution Engine
EVENT_PORTFOLIO_SIGNAL = "ePortfolioSignal"

# CTA Strategy → Execution Engine
EVENT_CTA_SIGNAL       = "eCtaSignal"

# Factor Research → Execution Engine
EVENT_FACTOR_SIGNAL    = "eFactorSignal"

# 批量执行请求（通用，任意上游均可发送）
EVENT_BATCH_ORDER_REQ  = "eBatchOrderReq"

# 执行完成回报（Execution → 上游，Phase 4 反馈链路）
EVENT_EXECUTION_DONE   = "eExecutionDone"
