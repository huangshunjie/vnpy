"""
portfolio_engine/event.py

Portfolio Engine 事件常量。

命名空间前缀 "ePortfolio." 与 VeighNa 原有事件（eLog / eTick 等）
完全隔离，不干扰 CTA / Factor 事件。

用法：
    from .event import EVENT_PORTFOLIO_UPDATE
    self.event_engine.put(Event(EVENT_PORTFOLIO_UPDATE, payload))
"""

EVENT_PORTFOLIO_UPDATE   = "ePortfolio.update"    # 组合状态更新（净值 / 权重）
EVENT_PORTFOLIO_RISK     = "ePortfolio.risk"      # 风险指标更新
EVENT_PORTFOLIO_REBALANCE = "ePortfolio.rebalance" # 调仓触发
EVENT_PORTFOLIO_LOG      = "ePortfolio.log"       # 日志消息
