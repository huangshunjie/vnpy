"""
adaptive_learning_ai/engine/feedback_engine.py  (Phase 2)

FeedbackEngine — 反馈采集引擎。

职责：
  - 接收来自 Execution / Portfolio / Risk / Strategy / Alpha 的反馈
  - 构建 FeedbackRecord，计算严重程度与信号强度
  - 维护 FeedbackBatch（当前周期）
  - 提供聚合统计与历史查询
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable
import uuid

from ..constant import FeedbackType, SystemStatus
from ..model.feedback_model import FeedbackRecord, FeedbackBatch, FeedbackState
from ..utils.feedback_utils import (
    compute_deviation, compute_severity, compute_signal_strength,
    aggregate_feedback,
)


class FeedbackEngine:
    """反馈采集引擎（Phase 2 完整实现）。"""

    def __init__(self, log_fn: Callable | None = None) -> None:
        self._log          = log_fn or (lambda m: None)
        self._state        = FeedbackState()
        self._current_batch: FeedbackBatch | None = None
        self._all_batches:   list[FeedbackBatch]  = []
        self._all_records:   list[FeedbackRecord] = []
        self._cycle        = 0

    def init(self)  -> None: self._log("[FeedbackEngine] init()")
    def start(self) -> None:
        self._log("[FeedbackEngine] start()")
        self._open_batch()

    def stop(self) -> None:
        self._close_batch()
        self._log("[FeedbackEngine] stop()")

    # ── batch lifecycle ───────────────────────────────────────────────
    def _open_batch(self) -> None:
        self._cycle += 1
        self._current_batch = FeedbackBatch(
            batch_id   = f"BATCH_{uuid.uuid4().hex[:6].upper()}",
            cycle      = self._cycle,
            created_at = datetime.now(),
        )

    def _close_batch(self) -> FeedbackBatch | None:
        if self._current_batch is None:
            return None
        self._current_batch.compute_stats()
        self._all_batches.append(self._current_batch)
        closed = self._current_batch
        self._current_batch = None
        return closed

    def next_cycle(self) -> FeedbackBatch | None:
        """关闭当前批次，开启下一个周期。返回已关闭的批次。"""
        closed = self._close_batch()
        self._open_batch()
        self._update_state()
        self._log(f"[FeedbackEngine] next_cycle: cycle={self._cycle}")
        return closed

    # ── record ingestion ──────────────────────────────────────────────
    def ingest(self, raw: dict) -> FeedbackRecord:
        """
        接收原始反馈字典，构建 FeedbackRecord 并加入当前批次。

        raw 字典必需字段：
          feedback_type : FeedbackType  或  str
          decision_value: float
          actual_value  : float

        可选字段：
          source_module, reason, symbol, strategy_id, metadata
        """
        if self._current_batch is None:
            self._open_batch()

        # 解析 feedback_type
        ft_raw = raw.get("feedback_type", FeedbackType.EXECUTION_SLIPPAGE)
        if isinstance(ft_raw, str):
            ft = FeedbackType(ft_raw)
        else:
            ft = ft_raw

        decision = float(raw.get("decision_value", 0.0))
        actual   = float(raw.get("actual_value",   0.0))
        dev, dev_pct = compute_deviation(decision, actual)

        # 优先使用外部提供的 severity/signal，否则自动计算
        severity = float(raw.get("severity",
                                  compute_severity(dev_pct, ft)))
        n_recent = len(self._all_records) + 1
        signal   = float(raw.get("signal_strength",
                                  compute_signal_strength(severity, n_recent)))

        record = FeedbackRecord(
            record_id       = raw.get("record_id",
                                       f"FB_{uuid.uuid4().hex[:8].upper()}"),
            feedback_type   = ft,
            source_module   = raw.get("source_module",   ""),
            decision_value  = decision,
            actual_value    = actual,
            deviation       = dev,
            deviation_pct   = dev_pct,
            reason          = raw.get("reason",          ""),
            severity        = severity,
            signal_strength = signal,
            symbol          = raw.get("symbol",          ""),
            strategy_id     = raw.get("strategy_id",     ""),
            metadata        = raw.get("metadata",        {}),
        )

        self._current_batch.add(record)
        self._all_records.append(record)
        self._update_state()
        return record

    def ingest_many(self, raws: list[dict]) -> list[FeedbackRecord]:
        """批量接收反馈。"""
        return [self.ingest(r) for r in raws]

    # ── convenience ingest helpers ────────────────────────────────────
    def ingest_execution(self, decision_price: float, actual_price: float,
                          symbol: str = "", strategy_id: str = "") -> FeedbackRecord:
        from ..utils.feedback_utils import make_execution_feedback
        return self.ingest(make_execution_feedback(
            decision_price, actual_price, symbol, strategy_id,
            n_recent=len(self._all_records) + 1))

    def ingest_strategy(self, expected_return: float, actual_return: float,
                         strategy_id: str = "") -> FeedbackRecord:
        from ..utils.feedback_utils import make_strategy_feedback
        return self.ingest(make_strategy_feedback(
            expected_return, actual_return, strategy_id,
            n_recent=len(self._all_records) + 1))

    def ingest_portfolio(self, target_weight: float, actual_weight: float,
                          symbol: str = "") -> FeedbackRecord:
        from ..utils.feedback_utils import make_portfolio_feedback
        return self.ingest(make_portfolio_feedback(
            target_weight, actual_weight, symbol,
            n_recent=len(self._all_records) + 1))

    def ingest_risk(self, risk_limit: float, actual_risk: float,
                    strategy_id: str = "") -> FeedbackRecord:
        from ..utils.feedback_utils import make_risk_feedback
        return self.ingest(make_risk_feedback(risk_limit, actual_risk, strategy_id))

    def ingest_alpha(self, expected_ic: float, actual_ic: float,
                     alpha_id: str = "") -> FeedbackRecord:
        from ..utils.feedback_utils import make_alpha_feedback
        return self.ingest(make_alpha_feedback(
            expected_ic, actual_ic, alpha_id,
            n_recent=len(self._all_records) + 1))

    # ── state update ─────────────────────────────────────────────────
    def _update_state(self) -> None:
        records_dicts = [r.to_dict() for r in self._all_records[-200:]]
        agg           = aggregate_feedback(records_dicts)

        type_counts: dict[str, int] = {}
        for r in self._all_records:
            k = r.feedback_type.value
            type_counts[k] = type_counts.get(k, 0) + 1

        latest = {}
        if self._all_batches:
            latest = self._all_batches[-1].to_dict()
        elif self._current_batch and self._current_batch.n_records > 0:
            self._current_batch.compute_stats()
            latest = self._current_batch.to_dict()

        self._state = FeedbackState(
            total_records     = len(self._all_records),
            total_batches     = len(self._all_batches),
            current_cycle     = self._cycle,
            type_counts       = type_counts,
            avg_severity      = agg["avg_severity"],
            avg_signal        = agg["avg_signal"],
            high_severity_pct = agg["high_severity_pct"],
            latest_batch      = latest,
            updated_at        = datetime.now(),
        )

    # ── query ─────────────────────────────────────────────────────────
    def get_state(self) -> FeedbackState:
        return self._state

    def get_records(self, n: int = 50,
                    fb_type: FeedbackType | None = None) -> list[FeedbackRecord]:
        records = self._all_records
        if fb_type is not None:
            records = [r for r in records if r.feedback_type == fb_type]
        return records[-n:]

    def get_batch(self, cycle: int) -> FeedbackBatch | None:
        for b in self._all_batches:
            if b.cycle == cycle:
                return b
        return None

    def get_current_batch(self) -> FeedbackBatch | None:
        return self._current_batch

    def get_high_severity_records(self, threshold: float = 0.7) -> list[FeedbackRecord]:
        return [r for r in self._all_records if r.severity >= threshold]

    def summary(self) -> dict:
        return {
            "phase":              2,
            "status":             "active",
            "total_records":      self._state.total_records,
            "total_batches":      self._state.total_batches,
            "current_cycle":      self._state.current_cycle,
            "avg_severity":       self._state.avg_severity,
            "avg_signal":         self._state.avg_signal,
            "high_severity_pct":  self._state.high_severity_pct,
            "type_counts":        self._state.type_counts,
        }
