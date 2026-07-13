"""
factor_research/event.py

Factor Research 模块专用事件类型定义。

命名规范：与 vnpy.trader.event 保持一致，前缀统一使用 EVENT_FACTOR_。
所有事件均通过 VeighNa EventEngine 总线广播，Engine 发出、Widget 订阅。
"""

# 日志消息事件
# data: str — 日志文本
EVENT_FACTOR_LOG = "eFactorLog"

# 计算进度事件
# data: ProgressData — 当前进度信息（已完成 / 总数 / 当前因子名）
EVENT_FACTOR_PROGRESS = "eFactorProgress"

# 计算全部完成事件
# data: None 或 摘要对象（第一阶段为 None）
EVENT_FACTOR_FINISHED = "eFactorFinished"

# 计算异常事件
# data: str — 错误描述文字
EVENT_FACTOR_ERROR = "eFactorError"

# 图表数据就绪事件（某个 Tab 的渲染数据已准备好）
# data: dict — {"tab": str, "payload": Any}
EVENT_FACTOR_PLOT_READY = "eFactorPlotReady"
