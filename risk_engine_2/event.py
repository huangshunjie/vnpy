"""
risk_engine_2/event.py

风控系统事件常量定义（Phase 1 ~ Phase 5）。
"""

# ── 内部风控事件（Phase 1）────────────────────────────────────────────────────
EVENT_RISK_UPDATE   = "eRiskUpdate"    # 风险指标刷新（所有子引擎更新后发布）
EVENT_RISK_ALERT    = "eRiskAlert"     # 风险预警触发（超阈值时发布）
EVENT_RISK_LIMIT    = "eRiskLimit"     # 风控限制触发（阻断交易时发布）
EVENT_RISK_DRAWDOWN = "eRiskDrawdown"  # 回撤预警（实时回撤超阈值时发布）
EVENT_RISK_LOG      = "eRiskLog"       # 风控日志（内部操作记录）

# ── Phase 5：系统联动事件 ─────────────────────────────────────────────────────

# Portfolio Engine → Risk Engine
#   data: dict {"nav": float, "weights": {symbol: float}, "positions": list}
EVENT_RISK_PORTFOLIO_UPDATE = "eRisk.portfolioUpdate"

# Factor Research → Risk Engine
#   data: dict {"factor": str, "exposures": {symbol: float}, "ic": float}
EVENT_RISK_FACTOR_EXPOSURE  = "eRisk.factorExposure"

# Risk Engine → Execution Engine（下单前拦截反馈）
#   data: LimitReport
EVENT_RISK_ORDER_GATE       = "eRisk.orderGate"

# Risk Engine → 全局广播（风格漂移预警）
#   data: dict {"factor": str, "drift": float, "threshold": float}
EVENT_RISK_STYLE_DRIFT      = "eRisk.styleDrift"

# Risk Engine 状态变更（Phase 5 全局通知）
#   data: dict {"status": "running"|"halted"|"warning", "message": str}
EVENT_RISK_STATUS           = "eRisk.status"
