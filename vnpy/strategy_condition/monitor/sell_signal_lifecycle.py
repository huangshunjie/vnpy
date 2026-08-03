"""
strategy_condition/monitor/sell_signal_lifecycle.py

Sell Signal Lifecycle 四层数据模型。
用于 Strategy Runtime Diagnostics Center，完整展示：
  Condition → Signal → Decision → Execution

设计原则：
  - 纯数据容器，不包含评估逻辑
  - 每根 K 线上，对每个卖出条件生成一个 SellSignalLifecycle 实例
  - 支持序列化，便于持久化与回放
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..constant import (
    DecisionResult,
    RejectReason,
    SellLifecycleStage,
)


# ═══════════════════════════════════════════════════════════════
# Layer 1: Condition Layer（条件计算层）
# ═══════════════════════════════════════════════════════════════

@dataclass
class ConditionLayerResult:
    """
    条件计算结果。
    表示某个卖出条件在当前 bar 上是否满足。

    Attributes:
        condition_name: 条件显示名 (e.g. "追踪止盈")
        indicator: ConditionIndicator.value (e.g. "TRAILING_STOP")
        triggered: 条件是否满足
        score: 评分 [0, 1]
        trigger_time: 触发时间
        context: 计算上下文（用于调试和展示）
            e.g. {"entry_price": 18.0, "peak_price": 19.5,
                  "current_price": 18.2, "return_pct": 1.1,
                  "drawdown_pct": 6.7, "threshold": 10.0}
    """
    condition_name: str
    indicator: str
    triggered: bool
    score: float = 0.0
    trigger_time: Optional[datetime] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_name": self.condition_name,
            "indicator": self.indicator,
            "triggered": self.triggered,
            "score": round(self.score, 4),
            "trigger_time": str(self.trigger_time)[:19] if self.trigger_time else None,
            "context": self.context,
        }


# ═══════════════════════════════════════════════════════════════
# Layer 2: Signal Layer（交易信号层）
# ═══════════════════════════════════════════════════════════════

@dataclass
class SignalLayerResult:
    """
    信号生成结果。
    当 Condition 满足且有持仓时，生成 SELL 信号。

    Attributes:
        signal_created: 是否产生了卖出信号
        signal_source: 触发信号的条件名
        signal_time: 信号生成时间
    """
    signal_created: bool = False
    signal_source: str = ""
    signal_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_created": self.signal_created,
            "signal_source": self.signal_source,
            "signal_time": str(self.signal_time)[:19] if self.signal_time else None,
        }


# ═══════════════════════════════════════════════════════════════
# Layer 3: Decision Layer（交易决策层）
# ═══════════════════════════════════════════════════════════════

@dataclass
class DecisionCheck:
    """Decision 层单项检查结果"""
    check_name: str          # e.g. "T+1保护", "冷却期", "持仓检查"
    passed: bool             # True=允许通过, False=被拦截
    description: str = ""    # e.g. "买入日2026-07-17，当日不可卖出"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "description": self.description,
        }


@dataclass
class DecisionLayerResult:
    """
    交易决策结果。
    判断卖出信号是否被允许执行。

    Attributes:
        result: PENDING / APPROVED / REJECTED
        reject_reason: 拒绝原因枚举
        reject_description: 人类可读的拒绝描述
        checks: 全部检查项明细
    """
    result: DecisionResult = DecisionResult.PENDING
    reject_reason: RejectReason = RejectReason.NONE
    reject_description: str = ""
    checks: List[DecisionCheck] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result": self.result.value,
            "reject_reason": self.reject_reason.value,
            "reject_description": self.reject_description,
            "checks": [c.to_dict() for c in self.checks],
        }


# ═══════════════════════════════════════════════════════════════
# Layer 4: Execution Layer（执行层）
# ═══════════════════════════════════════════════════════════════

@dataclass
class ExecutionLayerResult:
    """
    最终执行结果。
    记录是否实际产生了交易。

    Attributes:
        executed: 是否已执行卖出
        execution_time: 成交时间
        execution_price: 成交价格
        volume: 成交量
        exit_reason: 退出原因 (e.g. "trailing_stop")
    """
    executed: bool = False
    execution_time: Optional[datetime] = None
    execution_price: float = 0.0
    volume: float = 0.0
    exit_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executed": self.executed,
            "execution_time": str(self.execution_time)[:19] if self.execution_time else None,
            "execution_price": round(self.execution_price, 4),
            "volume": self.volume,
            "exit_reason": self.exit_reason,
        }


# ═══════════════════════════════════════════════════════════════
# 聚合：SellSignalLifecycle
# ═══════════════════════════════════════════════════════════════

@dataclass
class SellSignalLifecycle:
    """
    卖出信号完整生命周期。
    每根 K 线上，对每个卖出条件生成一个实例。

    Attributes:
        symbol: 股票代码
        bar_index: K线索引
        dt: K线时间

        has_position: 当前是否持仓
        entry_price: 入场价格
        entry_time: 入场时间
        peak_price: 持仓期间最高价
        hold_bars: 持仓K线数

        condition: Layer 1 结果
        signal: Layer 2 结果
        decision: Layer 3 结果
        execution: Layer 4 结果
    """
    # 标识
    symbol: str = ""
    bar_index: int = 0
    dt: Optional[datetime] = None

    # 持仓上下文
    has_position: bool = False
    entry_price: float = 0.0
    entry_time: Optional[datetime] = None
    peak_price: float = 0.0
    hold_bars: int = 0

    # 四层结果
    condition: ConditionLayerResult = field(
        default_factory=lambda: ConditionLayerResult("", "", False))
    signal: SignalLayerResult = field(default_factory=SignalLayerResult)
    decision: DecisionLayerResult = field(default_factory=DecisionLayerResult)
    execution: ExecutionLayerResult = field(default_factory=ExecutionLayerResult)

    # ── 便捷属性 ──────────────────────────────────────────────

    @property
    def stage(self) -> SellLifecycleStage:
        """当前到达的最高阶段"""
        if self.execution.executed:
            return SellLifecycleStage.EXECUTION
        if self.decision.result != DecisionResult.PENDING:
            return SellLifecycleStage.DECISION
        if self.signal.signal_created:
            return SellLifecycleStage.SIGNAL
        return SellLifecycleStage.CONDITION

    @property
    def status_summary(self) -> str:
        """一行摘要，用于 UI tooltip"""
        if not self.condition.triggered:
            return "条件未满足"
        if not self.signal.signal_created:
            return "条件满足，无持仓不产生信号"
        if self.decision.result == DecisionResult.REJECTED:
            return f"信号被拒绝: {self.decision.reject_description}"
        if self.decision.result == DecisionResult.APPROVED:
            if self.execution.executed:
                return f"已执行卖出 @ {self.execution.execution_price:.2f}"
            return "已批准，等待执行"
        return "评估中"

    @property
    def is_rejected(self) -> bool:
        return self.decision.result == DecisionResult.REJECTED

    @property
    def is_executed(self) -> bool:
        return self.execution.executed

    # ── 序列化 ────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "bar_index": self.bar_index,
            "dt": str(self.dt)[:19] if self.dt else None,
            "has_position": self.has_position,
            "entry_price": round(self.entry_price, 4),
            "entry_time": str(self.entry_time)[:19] if self.entry_time else None,
            "peak_price": round(self.peak_price, 4),
            "hold_bars": self.hold_bars,
            "stage": self.stage.value,
            "status_summary": self.status_summary,
            "condition": self.condition.to_dict(),
            "signal": self.signal.to_dict(),
            "decision": self.decision.to_dict(),
            "execution": self.execution.to_dict(),
        }