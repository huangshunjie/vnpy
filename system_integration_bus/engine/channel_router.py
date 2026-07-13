"""
system_integration_bus/engine/channel_router.py

ChannelRouter — 事件路由器。

职责：
  - 订阅所有子系统的 VeighNa 事件
  - 将原始事件转化为 BusMessage 并投入总线
  - 维护 channel → handler 路由表
  - 支持优先级过滤和目标定向转发
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable
import uuid

from vnpy.event import EventEngine, Event

from ..constant import BusChannel, PipelineStage, MessagePriority
from ..model.bus_model import BusMessage

# ── 事件 → (Channel, PipelineStage, Priority) 映射表 ─────────────────
# 格式: {event_type_prefix_or_exact: (channel, stage, priority)}

_EVENT_MAP: dict[str, tuple[BusChannel, PipelineStage, MessagePriority]] = {
    # ── DIL ──────────────────────────────────────────────────────────
    "eDI_DataFused":           (BusChannel.DATA_INTELLIGENCE, PipelineStage.INGEST,   MessagePriority.NORMAL),
    "eDI_FeatureUpdated":      (BusChannel.DATA_INTELLIGENCE, PipelineStage.INGEST,   MessagePriority.LOW),
    "eDI_DataQualityChecked":  (BusChannel.DATA_INTELLIGENCE, PipelineStage.INGEST,   MessagePriority.LOW),
    "eDI_DataIngested":        (BusChannel.DATA_INTELLIGENCE, PipelineStage.INGEST,   MessagePriority.LOW),
    "eDI_DataUpdated":         (BusChannel.DATA_INTELLIGENCE, PipelineStage.INGEST,   MessagePriority.NORMAL),

    # ── Alpha Factory ─────────────────────────────────────────────────
    "eAlphaFactory.generated": (BusChannel.ALPHA, PipelineStage.SIGNAL, MessagePriority.HIGH),
    "eAlphaFactory.scored":    (BusChannel.ALPHA, PipelineStage.SIGNAL, MessagePriority.HIGH),
    "eAlphaFactory.screened":  (BusChannel.ALPHA, PipelineStage.SIGNAL, MessagePriority.HIGH),
    "eAlphaFactory.live":      (BusChannel.ALPHA, PipelineStage.SIGNAL, MessagePriority.HIGH),
    "eAlphaFactory.rejected":  (BusChannel.ALPHA, PipelineStage.SIGNAL, MessagePriority.LOW),
    "eAlphaFactory.retired":   (BusChannel.ALPHA, PipelineStage.SIGNAL, MessagePriority.LOW),

    # ── Market Regime ─────────────────────────────────────────────────
    "eMarketRegimeDetected":   (BusChannel.REGIME, PipelineStage.SIGNAL, MessagePriority.HIGH),
    "eMarketRegimeChanged":    (BusChannel.REGIME, PipelineStage.SIGNAL, MessagePriority.HIGH),
    "eMarketVolatilityUpdate": (BusChannel.REGIME, PipelineStage.SIGNAL, MessagePriority.NORMAL),
    "eMarketTrendUpdate":      (BusChannel.REGIME, PipelineStage.SIGNAL, MessagePriority.NORMAL),
    "eMarketDecisionSignal":   (BusChannel.REGIME, PipelineStage.SIGNAL, MessagePriority.HIGH),

    # ── Portfolio Engine ──────────────────────────────────────────────
    "ePortfolio.update":       (BusChannel.PORTFOLIO, PipelineStage.ALLOCATE, MessagePriority.NORMAL),
    "ePortfolio.risk":         (BusChannel.PORTFOLIO, PipelineStage.ALLOCATE, MessagePriority.HIGH),
    "ePortfolio.rebalance":    (BusChannel.PORTFOLIO, PipelineStage.ALLOCATE, MessagePriority.HIGH),

    # ── Capital Allocation ────────────────────────────────────────────
    "eCapitalAI.allocation_updated": (BusChannel.CAPITAL, PipelineStage.ALLOCATE, MessagePriority.HIGH),
    "eCapitalAI.rebalance_trigger":  (BusChannel.CAPITAL, PipelineStage.ALLOCATE, MessagePriority.HIGH),
    "eCapitalAI.risk_budget_updated":(BusChannel.CAPITAL, PipelineStage.ALLOCATE, MessagePriority.NORMAL),
    "eCapitalAI.capital_update":     (BusChannel.CAPITAL, PipelineStage.ALLOCATE, MessagePriority.NORMAL),

    # ── Risk Engine ───────────────────────────────────────────────────
    "eRiskAlert":              (BusChannel.RISK, PipelineStage.ALLOCATE, MessagePriority.CRITICAL),
    "eRiskLimit":              (BusChannel.RISK, PipelineStage.ALLOCATE, MessagePriority.CRITICAL),
    "eRiskDrawdown":           (BusChannel.RISK, PipelineStage.ALLOCATE, MessagePriority.CRITICAL),
    "eRiskUpdate":             (BusChannel.RISK, PipelineStage.ALLOCATE, MessagePriority.NORMAL),
    "eRisk.orderGate":         (BusChannel.RISK, PipelineStage.EXECUTE,  MessagePriority.CRITICAL),
    "eRisk.styleDrift":        (BusChannel.RISK, PipelineStage.ALLOCATE, MessagePriority.HIGH),

    # ── Strategy Lifecycle ────────────────────────────────────────────
    "eStrategyDecayDetected":  (BusChannel.STRATEGY_LIFECYCLE, PipelineStage.SIGNAL, MessagePriority.HIGH),
    "eStrategyEvolved":        (BusChannel.STRATEGY_LIFECYCLE, PipelineStage.SIGNAL, MessagePriority.HIGH),
    "eStrategyRetired":        (BusChannel.STRATEGY_LIFECYCLE, PipelineStage.SIGNAL, MessagePriority.NORMAL),
    "eStrategyRegistered":     (BusChannel.STRATEGY_LIFECYCLE, PipelineStage.SIGNAL, MessagePriority.NORMAL),
    "eStrategyUpdated":        (BusChannel.STRATEGY_LIFECYCLE, PipelineStage.SIGNAL, MessagePriority.LOW),

    # ── Execution Engine ──────────────────────────────────────────────
    "eOrderUpdate":            (BusChannel.EXECUTION, PipelineStage.EXECUTE, MessagePriority.HIGH),
    "eFillUpdate":             (BusChannel.EXECUTION, PipelineStage.EXECUTE, MessagePriority.HIGH),
    "eExecutionDone":          (BusChannel.EXECUTION, PipelineStage.EXECUTE, MessagePriority.NORMAL),
    "eExecutionError":         (BusChannel.EXECUTION, PipelineStage.EXECUTE, MessagePriority.HIGH),

    # ── Execution Intelligence ────────────────────────────────────────
    "eExecutionCompleted":     (BusChannel.EXECUTION_INTEL, PipelineStage.EXECUTE, MessagePriority.NORMAL),
    "eImpactEstimated":        (BusChannel.EXECUTION_INTEL, PipelineStage.EXECUTE, MessagePriority.LOW),
    "eRouteSelected":          (BusChannel.EXECUTION_INTEL, PipelineStage.EXECUTE, MessagePriority.LOW),
    "eExecutionAborted":       (BusChannel.EXECUTION_INTEL, PipelineStage.EXECUTE, MessagePriority.HIGH),

    # ── Adaptive Learning ─────────────────────────────────────────────
    "eAL_SystemAdapted":           (BusChannel.LEARNING, PipelineStage.LEARN, MessagePriority.NORMAL),
    "eAL_ModelUpdated":            (BusChannel.LEARNING, PipelineStage.LEARN, MessagePriority.NORMAL),
    "eAL_LearningCycleCompleted":  (BusChannel.LEARNING, PipelineStage.LEARN, MessagePriority.LOW),
    "eAL_FeedbackReceived":        (BusChannel.LEARNING, PipelineStage.LEARN, MessagePriority.LOW),
}

# ── 模块名映射 ────────────────────────────────────────────────────────
_SOURCE_MAP: dict[str, str] = {
    "eDI_":         "data_intelligence_ai",
    "eAlphaFactory":"alpha_factory_2",
    "eMarket":      "market_regime_ai",
    "ePortfolio.":  "portfolio_engine",
    "eCapitalAI.":  "capital_allocation_ai",
    "eRisk":        "risk_engine_2",
    "eStrategy":    "strategy_lifecycle_ai",
    "eOrder":       "execution_engine",
    "eFill":        "execution_engine",
    "eExecution":   "execution_intelligence_ai",
    "eAL_":         "adaptive_learning_ai",
}

def _resolve_source(event_type: str) -> str:
    for prefix, mod in _SOURCE_MAP.items():
        if event_type.startswith(prefix):
            return mod
    return "unknown"


class ChannelRouter:
    """
    事件路由器。

    工作流：
      1. 向 EventEngine 注册所有已知事件的 handler
      2. 收到事件时构建 BusMessage
      3. 按 channel + priority 分发给注册的总线 handler
    """

    def __init__(
        self,
        event_engine: EventEngine,
        log_fn: Callable | None = None,
    ) -> None:
        self._ee      = event_engine
        self._log     = log_fn or (lambda m: None)

        # channel → list of handler callbacks
        self._channel_handlers: dict[BusChannel, list[Callable]] = {
            ch: [] for ch in BusChannel}
        # priority gate: 低于此优先级的消息直接丢弃（值越小越高）
        self._min_priority: MessagePriority = MessagePriority.LOW

        self._msg_count:  int = 0
        self._drop_count: int = 0

    # ── subscription ─────────────────────────────────────────────────
    def start(self) -> None:
        """向 EventEngine 注册所有已知事件 handler。"""
        for event_type in _EVENT_MAP:
            self._ee.register(event_type, self._on_event)
        self._log(f"[ChannelRouter] registered {len(_EVENT_MAP)} event handlers")

    def stop(self) -> None:
        for event_type in _EVENT_MAP:
            try:
                self._ee.unregister(event_type, self._on_event)
            except Exception:
                pass
        self._log("[ChannelRouter] unregistered all handlers")

    def register_channel_handler(
        self,
        channel:  BusChannel,
        handler:  Callable,
    ) -> None:
        """注册一个通道消息 handler（BusMessage → None）。"""
        self._channel_handlers[channel].append(handler)

    def set_min_priority(self, priority: MessagePriority) -> None:
        self._min_priority = priority

    # ── event → BusMessage ───────────────────────────────────────────
    def _on_event(self, event: Event) -> None:
        mapping = _EVENT_MAP.get(event.type)
        if mapping is None:
            return

        channel, stage, priority = mapping

        # priority gate
        if priority.value > self._min_priority.value:
            self._drop_count += 1
            return

        msg = BusMessage(
            msg_id     = f"MSG_{uuid.uuid4().hex[:8].upper()}",
            channel    = channel,
            stage      = stage,
            priority   = priority,
            source     = _resolve_source(event.type),
            event_type = event.type,
            payload    = event.data if isinstance(event.data, dict) else {},
        )
        self._dispatch(msg)

    def _dispatch(self, msg: BusMessage) -> None:
        self._msg_count += 1
        handlers = self._channel_handlers.get(msg.channel, [])
        for h in handlers:
            try:
                h(msg)
            except Exception as e:
                self._log(f"[ChannelRouter] handler error ch={msg.channel.value}: {e}")

    # ── direct send (from pipeline) ───────────────────────────────────
    def send(self, msg: BusMessage) -> None:
        """直接发送一条 BusMessage（不经过 EventEngine）。"""
        self._dispatch(msg)

    def broadcast(self, msg: BusMessage) -> None:
        """广播：发送给所有通道的 handler。"""
        self._msg_count += 1
        for channel_handlers in self._channel_handlers.values():
            for h in channel_handlers:
                try:
                    h(msg)
                except Exception as e:
                    self._log(f"[ChannelRouter] broadcast error: {e}")

    # ── stats ─────────────────────────────────────────────────────────
    @property
    def msg_count(self) -> int:
        return self._msg_count

    @property
    def drop_count(self) -> int:
        return self._drop_count
