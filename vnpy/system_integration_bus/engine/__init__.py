"""
system_integration_bus/engine/__init__.py

SystemBusEngine — VeighNa BaseEngine 子类，系统集成总线顶层引擎。

职责：
  - 实例化并连接 ChannelRouter / PipelineEngine / HealthMonitor
  - 向所有子引擎暴露统一查询接口
  - 负责跨模块信号转发（Regime → DIL, Risk Gate → Execution 等）
  - 管理总线生命周期
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable
import uuid

from vnpy.event import EventEngine, Event
from vnpy.trader.engine import BaseEngine, MainEngine

from ..constant import (
    APP_NAME, BusChannel, PipelineStage, MessagePriority,
    BusStatus, HealthStatus,
)
from ..event import (
    EVENT_BUS_STARTED, EVENT_BUS_STOPPED, EVENT_BUS_DEGRADED,
    EVENT_STAGE_INGEST, EVENT_STAGE_SIGNAL, EVENT_STAGE_ALLOCATE,
    EVENT_STAGE_EXECUTE, EVENT_STAGE_LEARN,
    EVENT_BUS_MESSAGE, EVENT_ENGINE_HEALTH, EVENT_ENGINE_OFFLINE,
    EVENT_ENGINE_RECOVERED, EVENT_PIPELINE_CYCLE, EVENT_PIPELINE_ERROR,
    EVENT_SIGNAL_FORWARDED, EVENT_RISK_GATE, EVENT_REGIME_BROADCAST,
)
from .channel_router   import ChannelRouter
from .pipeline_engine  import PipelineEngine
from .health_monitor   import HealthMonitor
from ..model.bus_model import BusMessage, PipelineRecord, EngineHealthRecord, BusState

# ── stage → event type 映射 ───────────────────────────────────────────
_STAGE_EVENTS = {
    PipelineStage.INGEST:   EVENT_STAGE_INGEST,
    PipelineStage.SIGNAL:   EVENT_STAGE_SIGNAL,
    PipelineStage.ALLOCATE: EVENT_STAGE_ALLOCATE,
    PipelineStage.EXECUTE:  EVENT_STAGE_EXECUTE,
    PipelineStage.LEARN:    EVENT_STAGE_LEARN,
}


class SystemBusEngine(BaseEngine):
    """
    系统集成总线引擎（VeighNa BaseEngine）。

    核心接口：
      init() / start() / stop()
      get_bus_state()         → BusState
      get_pipeline_history()  → list[PipelineRecord]
      get_engine_health()     → dict[str, EngineHealthRecord]
      force_cycle()           → 手动触发新管道周期
      set_risk_gate()         → 开启/关闭风险门控
      broadcast_regime()      → 广播 Regime 状态至所有模块
      get_summary()           → dict
    """

    engine_name = APP_NAME

    def __init__(self, main_engine: MainEngine, event_engine: EventEngine) -> None:
        super().__init__(main_engine, event_engine, APP_NAME)
        self._status:      BusStatus       = BusStatus.IDLE
        self._started_at:  datetime | None = None
        self._log_records: list[str]       = []

        # ── sub-engines ───────────────────────────────────────────────
        self._router  = ChannelRouter(event_engine, log_fn=self._log)
        self._pipeline= PipelineEngine(
            on_stage_complete = self._on_stage_complete,
            on_cycle_complete = self._on_cycle_complete,
            log_fn            = self._log,
        )
        self._health  = HealthMonitor(
            on_status_change = self._on_health_change,
            log_fn           = self._log,
        )

        # ── state ─────────────────────────────────────────────────────
        self._total_messages:  int  = 0
        self._forwarded_count: int  = 0
        self._error_count:     int  = 0
        self._risk_gate_open:  bool = False   # True = 阻断执行层消息
        self._channel_counts:  dict = {}

        self._log(f"[{APP_NAME}] SystemBusEngine created")

    # ── lifecycle ────────────────────────────────────────────────────
    def init(self) -> None:
        self._log(f"[{APP_NAME}] init()")
        self._status = BusStatus.IDLE

        # 注册所有通道 handler → pipeline + health
        for channel in BusChannel:
            self._router.register_channel_handler(
                channel, self._on_bus_message)

    def start(self) -> None:
        self._started_at = datetime.now()
        self._status     = BusStatus.RUNNING
        self._router.start()
        self._pipeline.start_cycle()
        self.dispatch_event(EVENT_BUS_STARTED,
                            {"status": self._status.value, "app": APP_NAME})
        self._log(f"[{APP_NAME}] start() — bus is RUNNING")

    def stop(self) -> None:
        self._router.stop()
        self._pipeline.force_close_cycle("bus stopped")
        self._status = BusStatus.STOPPED
        self.dispatch_event(EVENT_BUS_STOPPED,
                            {"status": self._status.value})
        self._log(f"[{APP_NAME}] stop()")

    def close(self) -> None:
        self.stop()

    # ── core message handler ─────────────────────────────────────────
    def _on_bus_message(self, msg: BusMessage) -> None:
        """所有通道消息的统一入口。"""
        self._total_messages += 1
        ch = msg.channel.value
        self._channel_counts[ch] = self._channel_counts.get(ch, 0) + 1

        # 健康脉冲
        self._health.pulse_channel(msg.channel)

        # 风险门控：CRITICAL 风险事件时暂停 EXECUTE 阶段转发
        if msg.channel == BusChannel.RISK and msg.priority == MessagePriority.CRITICAL:
            self._risk_gate_open = True
            self.dispatch_event(EVENT_RISK_GATE, msg.to_dict())
            self._log(f"[{APP_NAME}] RISK GATE OPENED: {msg.event_type}")

        # 跨模块转发：Regime 变化广播至所有模块
        if msg.channel == BusChannel.REGIME and msg.event_type in (
                "eMarketRegimeChanged", "eMarketRegimeDetected"):
            self._broadcast_regime(msg)

        # 跨模块转发：DIL FusedState → AlphaFactory 补充数据
        if (msg.channel == BusChannel.DATA_INTELLIGENCE
                and msg.event_type == "eDI_DataFused"):
            self._forward(msg, "alpha_factory_2", EVENT_SIGNAL_FORWARDED)

        # 跨模块转发：执行反馈 → AdaptiveLearning
        if msg.channel in (BusChannel.EXECUTION, BusChannel.EXECUTION_INTEL):
            if msg.event_type in ("eFillUpdate", "eExecutionCompleted"):
                self._forward(msg, "adaptive_learning_ai", EVENT_SIGNAL_FORWARDED)

        # 跨模块转发：Learning 输出 → AlphaFactory（模型更新）
        if (msg.channel == BusChannel.LEARNING
                and msg.event_type in ("eAL_ModelUpdated", "eAL_SystemAdapted")):
            self._forward(msg, "alpha_factory_2", EVENT_SIGNAL_FORWARDED)

        # 推入管道
        self._pipeline.on_message(msg)

        # 广播 BusMessage 事件（供 UI 监听）
        self.dispatch_event(EVENT_BUS_MESSAGE, msg.to_dict())

    def _forward(self, msg: BusMessage, target: str,
                  event_type: str) -> None:
        """将消息转发给目标模块，并广播 SIGNAL_FORWARDED 事件。"""
        fwd = BusMessage(
            msg_id     = f"FWD_{uuid.uuid4().hex[:8].upper()}",
            channel    = msg.channel,
            stage      = msg.stage,
            priority   = msg.priority,
            source     = msg.source,
            target     = target,
            event_type = msg.event_type,
            payload    = msg.payload,
            forwarded  = True,
        )
        self._forwarded_count += 1
        self.dispatch_event(event_type, fwd.to_dict())

    def _broadcast_regime(self, msg: BusMessage) -> None:
        """广播 Regime 状态变化至所有已注册模块。"""
        self.dispatch_event(EVENT_REGIME_BROADCAST, {
            "source":     msg.source,
            "event_type": msg.event_type,
            "payload":    msg.payload,
        })
        self._log(f"[{APP_NAME}] REGIME BROADCAST: {msg.event_type}")

    # ── stage / cycle callbacks ───────────────────────────────────────
    def _on_stage_complete(self, stage: PipelineStage,
                            record: PipelineRecord | None) -> None:
        ev = _STAGE_EVENTS.get(stage, EVENT_BUS_MESSAGE)
        self.dispatch_event(ev, {
            "stage":    stage.value,
            "cycle_id": record.cycle_id if record else "",
        })
        self._log(f"[{APP_NAME}] stage {stage.value} complete")

    def _on_cycle_complete(self, record: PipelineRecord) -> None:
        self.dispatch_event(EVENT_PIPELINE_CYCLE, record.to_dict())
        self._log(
            f"[{APP_NAME}] pipeline cycle {record.cycle_num} complete "
            f"({record.duration_ms:.1f}ms) "
            f"stages={record.stages_done}")
        # 自动开始下一周期
        if self._status == BusStatus.RUNNING:
            self._pipeline.start_cycle()

    # ── health callbacks ──────────────────────────────────────────────
    def _on_health_change(self, record: EngineHealthRecord) -> None:
        if record.status == HealthStatus.OFFLINE:
            self.dispatch_event(EVENT_ENGINE_OFFLINE, record.to_dict())
            self._pipeline.mark_channel_offline(
                self._module_to_channel(record.module))
            # 若多个核心引擎下线，切换至 DEGRADED
            offline = self._health.get_offline()
            if len(offline) >= 2:
                self._status = BusStatus.DEGRADED
                self.dispatch_event(EVENT_BUS_DEGRADED,
                                    {"offline": [r.module for r in offline]})
        elif record.status == HealthStatus.HEALTHY:
            self.dispatch_event(EVENT_ENGINE_RECOVERED, record.to_dict())
            self._pipeline.mark_channel_online(
                self._module_to_channel(record.module))
            if self._status == BusStatus.DEGRADED:
                if not self._health.get_offline():
                    self._status = BusStatus.RUNNING

    def _module_to_channel(self, module: str) -> BusChannel:
        from .health_monitor import _CHANNEL_MODULE
        for ch, mod in _CHANNEL_MODULE.items():
            if mod == module:
                return ch
        return BusChannel.SYSTEM

    # ── public control ────────────────────────────────────────────────
    def force_cycle(self) -> None:
        """手动关闭当前周期并开始新周期。"""
        self._pipeline.force_close_cycle("manual force")
        self._pipeline.start_cycle()

    def set_risk_gate(self, open_gate: bool) -> None:
        self._risk_gate_open = open_gate
        self._log(f"[{APP_NAME}] risk gate = {open_gate}")

    def broadcast_regime(self, payload: dict) -> None:
        """外部主动广播 Regime 状态。"""
        self.dispatch_event(EVENT_REGIME_BROADCAST, payload)

    def check_health(self) -> list[EngineHealthRecord]:
        """手动触发一次健康检查（通常由定时器调用）。"""
        return self._health.check_all()

    # ── query ─────────────────────────────────────────────────────────
    def get_bus_state(self) -> BusState:
        health_summ = self._health.summary()
        return BusState(
            status          = self._status,
            cycle_count     = self._pipeline._cycle_num,
            total_messages  = self._total_messages,
            forwarded_count = self._forwarded_count,
            error_count     = self._error_count,
            dropped_count   = self._router.drop_count,
            channel_counts  = dict(self._channel_counts),
            engine_health   = health_summ["details"],
            active_channels = [c.value for c in
                               self._health.get_online_channels()],
            offline_engines = [r.module for r in self._health.get_offline()],
            avg_cycle_ms    = self._pipeline.summary()["avg_cycle_ms"],
            throughput_mpm  = self._throughput(),
            updated_at      = datetime.now(),
        )

    def get_pipeline_history(self, n: int = 20) -> list[PipelineRecord]:
        return self._pipeline.get_history(n)

    def get_engine_health(self) -> dict[str, EngineHealthRecord]:
        return self._health.get_all()

    def get_logs(self, limit: int = 200) -> list[str]:
        return self._log_records[-limit:]

    def get_summary(self) -> dict:
        hs = self._health.summary()
        ps = self._pipeline.summary()
        return {
            "app":           APP_NAME,
            "status":        self._status.value,
            "uptime":        self._uptime(),
            "total_messages":self._total_messages,
            "forwarded":     self._forwarded_count,
            "dropped":       self._router.drop_count,
            "risk_gate_open":self._risk_gate_open,
            "health":        hs,
            "pipeline":      ps,
        }

    # ── events ───────────────────────────────────────────────────────
    def dispatch_event(self, event_type: str, data: dict | None = None) -> None:
        self.event_engine.put(Event(event_type, data or {}))

    # ── internal ─────────────────────────────────────────────────────
    def _uptime(self) -> float:
        if self._started_at is None:
            return 0.0
        return round((datetime.now() - self._started_at).total_seconds(), 1)

    def _throughput(self) -> float:
        if self._started_at is None or self._total_messages == 0:
            return 0.0
        elapsed = (datetime.now() - self._started_at).total_seconds() / 60.0
        return round(self._total_messages / max(elapsed, 1/60), 2)

    def _log(self, msg: str) -> None:
        ts = str(datetime.now())[:19]
        self._log_records.append(f"{ts}  {msg}")
        try:    self.write_log(msg)
        except: pass


__all__ = ["SystemBusEngine", "ChannelRouter",
           "PipelineEngine", "HealthMonitor"]
