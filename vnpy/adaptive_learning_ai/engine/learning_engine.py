"""
adaptive_learning_ai/engine/learning_engine.py  (Phase 3)

LearningEngine — 学习引擎完整实现。

流程：Feedback → Pattern Extraction → Adjustment Signal

职责：
  - 从 FeedbackEngine 拉取反馈批次
  - 调用 learning_utils 提取信号、聚合模式
  - 维护信号历史与学习状态
  - 输出 LearningPattern 列表供 AdaptationEngine 消费
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable
import uuid

from ..constant import APP_NAME, SystemStatus, FeedbackType, AdaptationTarget
from ..model.feedback_model import FeedbackRecord, FeedbackBatch
from ..model.learning_model  import LearningSignal, LearningPattern, LearningState
from ..utils.learning_utils  import (
    extract_signal, extract_signals,
    aggregate_signals,
    compute_learning_velocity,
    filter_high_confidence,
    top_urgent_signals,
)


class LearningEngine:
    """学习引擎（Phase 3 完整实现）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log             = log_fn or (lambda m: None)
        self._status          = SystemStatus.IDLE
        self._started_at: datetime | None = None
        self._cycle           = 0
        self._cycle_signal_counts: list[int] = []

        self._all_signals:   list[LearningSignal]  = []
        self._all_patterns:  list[LearningPattern] = []
        self._state          = LearningState()

    def init(self) -> None:
        self._log(f"[LearningEngine] init()")
        self._status = SystemStatus.IDLE

    def start(self) -> None:
        self._started_at = datetime.now()
        self._status     = SystemStatus.COLLECTING
        self._log(f"[LearningEngine] start()")

    def stop(self) -> None:
        self._status = SystemStatus.STOPPED
        self._log(f"[LearningEngine] stop()")

    # ── core pipeline ─────────────────────────────────────────────────
    def learn_from_records(
        self,
        records: list[FeedbackRecord],
    ) -> tuple[list[LearningSignal], list[LearningPattern]]:
        """
        从反馈记录列表执行一次学习迭代。

        Returns (new_signals, new_patterns)
        """
        if not records:
            return [], []

        self._status = SystemStatus.LEARNING
        self._cycle += 1

        # Step 1: 提取信号
        new_signals = extract_signals(records)
        self._all_signals.extend(new_signals)

        # Step 2: 聚合模式（使用全量信号的最近 window）
        window_signals = self._all_signals[-100:]
        new_patterns   = aggregate_signals(
            window_signals, min_count=2, min_consistency=0.55)
        self._all_patterns = new_patterns   # 替换（模式是动态的）

        # Step 3: 更新学习速度
        self._cycle_signal_counts.append(len(new_signals))

        self._update_state()
        self._status = SystemStatus.COLLECTING

        self._log(
            f"[LearningEngine] cycle={self._cycle} "
            f"signals={len(new_signals)} patterns={len(new_patterns)}"
        )
        return new_signals, new_patterns

    def learn_from_batch(
        self,
        batch: FeedbackBatch,
    ) -> tuple[list[LearningSignal], list[LearningPattern]]:
        """从 FeedbackBatch 执行一次学习迭代。"""
        return self.learn_from_records(batch.records)

    def learn_from_single(
        self,
        record: FeedbackRecord,
    ) -> LearningSignal:
        """从单条反馈记录提取信号（不触发模式聚合，适合实时流）。"""
        signal = extract_signal(record)
        self._all_signals.append(signal)
        self._update_state()
        return signal

    # ── query ─────────────────────────────────────────────────────────
    def get_signals(
        self,
        n: int = 50,
        target: AdaptationTarget | None = None,
        fb_type: FeedbackType | None = None,
    ) -> list[LearningSignal]:
        signals = self._all_signals
        if target  is not None:
            signals = [s for s in signals if s.target       == target]
        if fb_type is not None:
            signals = [s for s in signals if s.feedback_type == fb_type]
        return signals[-n:]

    def get_patterns(
        self,
        target: AdaptationTarget | None = None,
    ) -> list[LearningPattern]:
        if target is None:
            return list(self._all_patterns)
        return [p for p in self._all_patterns if p.target == target]

    def get_high_confidence_signals(
        self, threshold: float = 0.7
    ) -> list[LearningSignal]:
        return filter_high_confidence(self._all_signals, threshold)

    def get_urgent_signals(self, n: int = 5) -> list[LearningSignal]:
        return top_urgent_signals(self._all_signals, n)

    def get_state(self) -> LearningState:
        return self._state

    # ── state update ──────────────────────────────────────────────────
    def _update_state(self) -> None:
        signals = self._all_signals
        n       = len(signals)

        avg_conf = (sum(s.confidence for s in signals) / n) if n else 0.0
        avg_urg  = (sum(s.urgency    for s in signals) / n) if n else 0.0
        hi_conf  = sum(1 for s in signals if s.confidence >= 0.7)

        target_counts: dict[str, int] = {}
        for s in signals:
            k = s.target.value
            target_counts[k] = target_counts.get(k, 0) + 1

        velocity = compute_learning_velocity(self._cycle_signal_counts)

        self._state = LearningState(
            cycle             = self._cycle,
            phase             = 3,
            total_signals     = n,
            active_patterns   = len(self._all_patterns),
            high_conf_signals = hi_conf,
            avg_confidence    = round(avg_conf, 4),
            avg_urgency       = round(avg_urg,  4),
            learning_velocity = velocity,
            target_counts     = target_counts,
            recent_patterns   = [p.to_dict() for p in self._all_patterns[:5]],
            updated_at        = datetime.now(),
        )

    def summary(self) -> dict:
        return {
            "phase":             3,
            "status":            self._status.value,
            "cycle":             self._cycle,
            "total_signals":     self._state.total_signals,
            "active_patterns":   self._state.active_patterns,
            "high_conf_signals": self._state.high_conf_signals,
            "avg_confidence":    self._state.avg_confidence,
            "learning_velocity": self._state.learning_velocity,
        }
