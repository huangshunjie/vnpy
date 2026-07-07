"""
temporal_intelligence_ai/engine/validation_engine.py

Temporal Forecast Validation Engine — 时间验证引擎（Phase 6）。

职责：
  - 记录预测值（来自 CycleEngine / DecayEngine / DependencyEngine）
  - 当实际值到期时更新记录并执行验证计算
  - 输出 ValidationState，由主引擎派发 EVENT_VALIDATION_UPDATED

核心理念：
  不是预测未来，而是验证"当前时间结构分析是否正在准确描述已发生的衰减"。

严格禁止：生成交易信号、任何前瞻偏差
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from ..model.validation_model import (
    ValidationHistory,
    ValidationRecord,
    ValidationState,
)
from ..utils.temporal_utils import build_validation_metrics


class ValidationEngine:
    """
    Temporal Forecast Validation Engine.

    调用流程：
      1. submit_prediction()   — 提交一条预测记录
      2. realize()             — 当实际值到期时更新记录
      3. validate()            — 触发完整验证计算，返回 ValidationState
      4. get_state()           — 获取最新 ValidationState
      5. get_history()         — 获取历史序列
    """

    def __init__(self) -> None:
        self._records:  Dict[str, ValidationRecord] = {}
        self._current:  Optional[ValidationState]   = None
        self._history:  ValidationHistory           = ValidationHistory()

        # 外部注入的序列（供衰减对齐和 ACF 验证使用）
        self._decay_predicted:       List[float] = []
        self._decay_realized:        List[float] = []
        self._acf_predicted:         List[float] = []
        self._acf_realized:          List[float] = []
        self._significant_acf_lags:  List[int]   = []

        self._auto_bar: int = 0   # 内部 bar 计数（用于 horizon 到期判断）

    # ── prediction submission ────────────────────────────────────────

    def submit_prediction(self, record: ValidationRecord) -> None:
        """
        提交一条预测记录（不含实际值）。

        同一 record_id 重复提交时覆盖。
        """
        self._records[record.record_id] = record

    def submit_many(self, records: List[ValidationRecord]) -> None:
        for r in records:
            self.submit_prediction(r)

    # ── realization ──────────────────────────────────────────────────

    def realize(self, record_id: str, realized_value: float) -> None:
        """
        更新某条记录的实际值，标记为已实现。

        Args:
            record_id:      预测记录 ID
            realized_value: 实际观测值
        """
        rec = self._records.get(record_id)
        if rec is None:
            return
        rec.realized    = realized_value
        rec.realized_at = datetime.now()
        rec.is_realized = True

    def auto_realize_by_bar(self, current_bar: int) -> int:
        """
        自动将已超过 horizon_bars 的记录标记为到期（使用 predicted 作为占位实现值）。

        用于演示和压测，实际使用时应通过 realize() 传入真实值。

        Returns:
            本次自动到期的记录数
        """
        self._auto_bar = current_bar
        count = 0
        for rec in self._records.values():
            if rec.is_realized:
                continue
            created_bar = getattr(rec, "_created_bar", 0)
            if current_bar - created_bar >= rec.horizon_bars:
                # 用预测值的带噪声版本模拟实际值（仅用于演示）
                import random
                noise = random.gauss(0, abs(rec.predicted) * 0.15 + 0.01)
                rec.realized    = rec.predicted + noise
                rec.realized_at = datetime.now()
                rec.is_realized = True
                count += 1
        return count

    # ── context injection ────────────────────────────────────────────

    def set_decay_series(
        self,
        predicted: List[float],
        realized:  List[float],
    ) -> None:
        """注入衰减强度序列（由 DecayEngine 输出注入）。"""
        self._decay_predicted = list(predicted)
        self._decay_realized  = list(realized)

    def set_acf_series(
        self,
        predicted:        List[float],
        realized:         List[float],
        significant_lags: List[int],
    ) -> None:
        """注入 ACF 序列（由 DependencyEngine 输出注入）。"""
        self._acf_predicted        = list(predicted)
        self._acf_realized         = list(realized)
        self._significant_acf_lags = list(significant_lags)

    # ── core validation ──────────────────────────────────────────────

    def validate(self) -> ValidationState:
        """
        触发完整时间验证计算。

        Returns:
            ValidationState
        """
        all_records = list(self._records.values())
        metrics = build_validation_metrics(
            records              = all_records,
            decay_predicted      = self._decay_predicted or None,
            decay_realized       = self._decay_realized  or None,
            acf_predicted        = self._acf_predicted   or None,
            acf_realized         = self._acf_realized    or None,
            significant_acf_lags = self._significant_acf_lags or None,
        )

        from ..utils.temporal_utils import compute_errors
        realized_records = [r for r in all_records if r.is_realized]
        results = compute_errors(realized_records)

        state = ValidationState(
            timestamp = datetime.now(),
            metrics   = metrics,
            results   = results,
        )

        self._current = state
        self._history.append_snapshot(state)
        return state

    # ── accessors ────────────────────────────────────────────────────

    def get_state(self) -> Optional[ValidationState]:
        return self._current

    def get_history(self) -> ValidationHistory:
        return self._history

    def get_all_records(self) -> List[ValidationRecord]:
        return list(self._records.values())

    def get_realized_records(self) -> List[ValidationRecord]:
        return [r for r in self._records.values() if r.is_realized]

    def clear_records(self) -> None:
        self._records.clear()

    def get_summary(self) -> dict:
        if self._current is None:
            return {
                "n_records":      0,
                "n_realized":     0,
                "temporal_health": 0.0,
                "direction_acc":  0.0,
                "mae":            0.0,
            }
        m = self._current.metrics
        return {
            "n_records":      m.n_records,
            "n_realized":     m.n_realized,
            "temporal_health": m.temporal_health,
            "direction_acc":  m.direction_acc,
            "mae":            m.mae,
        }
