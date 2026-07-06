"""
system_integration_bus/engine/pipeline_engine.py

PipelineEngine — 五阶段数据管道引擎。

闭环：
  Stage 1  INGEST    DIL 数据就绪 → 推送至 Signal 层
  Stage 2  SIGNAL    Alpha/Regime 信号就绪 → 推送至 Allocate 层
  Stage 3  ALLOCATE  Portfolio/Capital/Risk 决策就绪 → 推送至 Execute 层
  Stage 4  EXECUTE   执行完成 → 推送至 Learn 层
  Stage 5  LEARN     学习反馈完成 → 关闭本轮周期

每个阶段通过 BusMessage 触发；PipelineEngine 维护每轮周期的完整记录。
"""
from __future__ import annotations
from collections import defaultdict, deque
from datetime import datetime
from typing import Callable
import uuid

from ..constant import BusChannel, PipelineStage, MessagePriority, BusStatus
from ..model.bus_model import BusMessage, PipelineRecord


# ── 阶段前驱映射（哪些 Channel 的消息触发下一阶段） ──────────────────
_STAGE_TRIGGERS: dict[PipelineStage, set[BusChannel]] = {
    PipelineStage.INGEST:   {BusChannel.DATA_INTELLIGENCE},
    PipelineStage.SIGNAL:   {BusChannel.ALPHA, BusChannel.REGIME,
                              BusChannel.STRATEGY_LIFECYCLE},
    PipelineStage.ALLOCATE: {BusChannel.PORTFOLIO, BusChannel.CAPITAL,
                              BusChannel.RISK},
    PipelineStage.EXECUTE:  {BusChannel.EXECUTION, BusChannel.EXECUTION_INTEL},
    PipelineStage.LEARN:    {BusChannel.LEARNING},
}

_STAGE_ORDER = [
    PipelineStage.INGEST,
    PipelineStage.SIGNAL,
    PipelineStage.ALLOCATE,
    PipelineStage.EXECUTE,
    PipelineStage.LEARN,
]


class PipelineEngine:
    """五阶段管道引擎。"""

    def __init__(
        self,
        on_stage_complete: Callable | None = None,   # (stage, record) → None
        on_cycle_complete: Callable | None = None,   # (record,) → None
        log_fn:            Callable | None = None,
    ) -> None:
        self._on_stage = on_stage_complete or (lambda s, r: None)
        self._on_cycle = on_cycle_complete or (lambda r: None)
        self._log      = log_fn or (lambda m: None)

        self._cycle_num:   int = 0
        self._current:     PipelineRecord | None = None
        self._history:     deque[PipelineRecord] = deque(maxlen=200)

        # 每阶段收到的 BusMessage 缓冲（当前周期）
        self._stage_buf:   dict[PipelineStage, list[BusMessage]] = defaultdict(list)
        self._stage_times: dict[PipelineStage, datetime]         = {}

        # 当前已完成的阶段集合
        self._done_stages: set[PipelineStage] = set()

        # 可选：哪些 Channel 当前可用（空 = 全部可用）
        self._online_channels: set[BusChannel] = set(BusChannel)

    # ── public API ────────────────────────────────────────────────────
    def start_cycle(self) -> PipelineRecord:
        """开始新的管道周期。"""
        self._cycle_num += 1
        self._current = PipelineRecord(
            cycle_id   = f"CYC_{uuid.uuid4().hex[:8].upper()}",
            cycle_num  = self._cycle_num,
            started_at = datetime.now(),
        )
        self._stage_buf   = defaultdict(list)
        self._stage_times = {}
        self._done_stages = set()
        self._log(f"[Pipeline] cycle {self._cycle_num} started")
        return self._current

    def on_message(self, msg: BusMessage) -> None:
        """
        接收来自 ChannelRouter 的 BusMessage。
        判断该消息属于哪个阶段，更新管道状态。
        """
        if self._current is None:
            self.start_cycle()

        stage = msg.stage
        self._stage_buf[stage].append(msg)

        if self._current:
            self._current.total_messages += 1
            counts = self._current.stage_counts
            counts[stage.value] = counts.get(stage.value, 0) + 1

        # 记录该阶段第一次收到消息的时间
        if stage not in self._stage_times:
            self._stage_times[stage] = datetime.now()

        # 检查是否可以标记该阶段完成
        self._try_complete_stage(stage)

    def _try_complete_stage(self, stage: PipelineStage) -> None:
        """
        判断一个阶段是否完成。
        条件：该阶段至少收到 1 条消息，且尚未标记完成。
        """
        if stage in self._done_stages:
            return
        if not self._stage_buf.get(stage):
            return

        self._done_stages.add(stage)
        now = datetime.now()

        if self._current:
            if stage.value not in self._current.stages_done:
                self._current.stages_done.append(stage.value)

            # 计算延迟
            t0 = self._stage_times.get(stage, now)
            latency = round((now - t0).total_seconds() * 1000, 2)
            self._current.stage_latency[stage.value] = latency

        self._log(f"[Pipeline] stage {stage.value} complete")
        self._on_stage(stage, self._current)

        # 检查全部 5 个阶段是否均完成
        self._check_cycle_complete()

    def _check_cycle_complete(self) -> None:
        """若所有有效阶段均完成，关闭本周期。"""
        # 计算当前在线的阶段（对应通道至少一个在线）
        available_stages = set()
        for stage, channels in _STAGE_TRIGGERS.items():
            if channels & self._online_channels:
                available_stages.add(stage)

        if available_stages and available_stages.issubset(self._done_stages):
            self._close_cycle()

    def force_close_cycle(self, reason: str = "forced") -> PipelineRecord | None:
        """强制关闭当前周期（超时或外部触发）。"""
        if self._current is None:
            return None
        if self._current:
            # 标记未完成的阶段为 skipped
            for stage in _STAGE_ORDER:
                if stage not in self._done_stages:
                    self._current.stages_skipped.append(stage.value)
            self._current.success   = len(self._current.stages_skipped) == 0
            self._current.error_msg = reason
        return self._close_cycle()

    def _close_cycle(self) -> PipelineRecord | None:
        if self._current is None:
            return None
        rec = self._current
        rec.completed_at = datetime.now()
        if not rec.error_msg:
            rec.success = True
        self._history.append(rec)
        self._log(
            f"[Pipeline] cycle {rec.cycle_num} closed: "
            f"duration={rec.duration_ms:.1f}ms "
            f"stages={rec.stages_done} "
            f"skipped={rec.stages_skipped}")
        self._on_cycle(rec)
        self._current = None
        return rec

    def set_online_channels(self, channels: set[BusChannel]) -> None:
        self._online_channels = channels

    def mark_channel_offline(self, channel: BusChannel) -> None:
        self._online_channels.discard(channel)

    def mark_channel_online(self, channel: BusChannel) -> None:
        self._online_channels.add(channel)

    # ── query ─────────────────────────────────────────────────────────
    def get_current(self) -> PipelineRecord | None:
        return self._current

    def get_history(self, n: int = 20) -> list[PipelineRecord]:
        hist = list(self._history)
        return hist[-n:]

    def get_stage_messages(self, stage: PipelineStage,
                            n: int = 20) -> list[BusMessage]:
        return self._stage_buf.get(stage, [])[-n:]

    def summary(self) -> dict:
        hist = list(self._history)
        avg_ms = (sum(r.duration_ms for r in hist) / len(hist)) if hist else 0.0
        return {
            "cycle_count":     self._cycle_num,
            "avg_cycle_ms":    round(avg_ms, 2),
            "online_channels": [c.value for c in self._online_channels],
            "current_cycle":   self._current.cycle_num if self._current else None,
            "done_stages":     [s.value for s in self._done_stages],
        }
