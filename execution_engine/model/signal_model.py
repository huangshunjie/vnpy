"""
execution_engine/model/signal_model.py

执行信号数据模型（Phase 4）。

ExecutionSignal : 统一信号格式，所有上游（Portfolio/CTA/Factor）的信号
                  均经 SignalAdapter 转换为此格式后进入执行流水线。
BatchOrderRequest : 批量订单请求容器。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..constant import SignalSource, PositionAction


@dataclass
class ExecutionSignal:
    """
    统一执行信号。

    来源：Portfolio Engine / CTA Strategy / Factor Research / 手动
    目标：SignalAdapter → list[OrderRequest] → ExecutionCoreEngine
    """
    signal_id:   str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source:      SignalSource = SignalSource.MANUAL
    action:      PositionAction = PositionAction.OPEN

    # 合约与方向
    symbol:      str   = ""
    direction:   str   = ""       # "LONG" / "SHORT"

    # 数量（二选一：绝对手数 或 目标权重，由 action 决定语义）
    volume:      float = 0.0      # 绝对手数（CTA / 手动）
    target_weight: float = 0.0    # 目标权重 [0,1]（Portfolio / Factor）
    current_weight: float = 0.0   # 当前权重（用于计算调仓量）

    # 价格
    signal_price: float = 0.0     # 信号触发时的参考价格
    portfolio_nav: float = 0.0    # 组合净值（Portfolio 信号使用，用于换算手数）

    # 元数据
    strategy_name: str = ""       # 策略名称（CTA 信号使用）
    factor_name:   str = ""       # 因子名称（Factor 信号使用）
    ic_value:      float = 0.0    # IC 值（Factor 信号使用）

    # 原始事件数据（调试用）
    raw_data: Any = field(default=None, repr=False)

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def is_valid(self) -> bool:
        """基础有效性校验。"""
        if not self.symbol:
            return False
        if self.direction not in ("LONG", "SHORT"):
            return False
        if self.source in (SignalSource.CTA, SignalSource.MANUAL):
            return self.volume > 0
        if self.source in (SignalSource.PORTFOLIO, SignalSource.FACTOR):
            return self.signal_price > 0
        return True

    @property
    def delta_weight(self) -> float:
        """目标权重与当前权重之差（调仓方向判断）。"""
        return self.target_weight - self.current_weight


@dataclass
class BatchOrderRequest:
    """
    批量订单请求（Phase 4 批量执行入口）。

    由 Portfolio Engine 调仓或 Factor 信号触发，
    包含多个 ExecutionSignal，由 SignalAdapter 批量转换。
    """
    batch_id:  str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source:    SignalSource = SignalSource.PORTFOLIO
    signals:   list[ExecutionSignal] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    # 执行优先级（数值越大越先执行，用于先卖后买的调仓顺序）
    priority:  int  = 0

    @property
    def count(self) -> int:
        return len(self.signals)

    @property
    def valid_signals(self) -> list[ExecutionSignal]:
        return [s for s in self.signals if s.is_valid]
