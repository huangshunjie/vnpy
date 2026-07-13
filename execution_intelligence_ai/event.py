"""
execution_intelligence_ai/event.py

Execution Intelligence 2.0 — 事件常量定义。
"""

# 执行任务开始（收到父订单，开始规划拆单）
EVENT_EXECUTION_START = "eExecutionStart"

# 子订单已切片生成（拆单引擎输出）
EVENT_ORDER_SLICED = "eOrderSliced"

# 市场冲击估算完成
EVENT_IMPACT_ESTIMATED = "eImpactEstimated"

# 路由路径已选定
EVENT_ROUTE_SELECTED = "eRouteSelected"

# 执行任务全部完成
EVENT_EXECUTION_COMPLETED = "eExecutionCompleted"

# 反馈指标已更新（滑点/成交率/延迟等）
EVENT_FEEDBACK_UPDATED = "eFeedbackUpdated"

# 执行任务中止（风控或用户取消）
EVENT_EXECUTION_ABORTED = "eExecutionAborted"
