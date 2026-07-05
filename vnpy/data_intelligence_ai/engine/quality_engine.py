"""
data_intelligence_ai/engine/quality_engine.py  (Phase 3)

QualityEngine — 数据质量引擎。

职责：
  - 对 Feature Store 中的特征执行质量检查
  - 维护特征历史窗口（用于异常值检测）
  - 执行数据漂移检测
  - 维护质量报告历史与状态快照
"""
from __future__ import annotations
from datetime import datetime
from typing import Callable
import uuid

from ..constant import QualityStatus, SystemStatus
from ..model.quality_model import (
    QualityReport, DriftReport, QualityState, QualityIssue)
from ..model.feature_model import FeatureRecord
from ..utils.quality_utils import run_quality_check, detect_drift


class QualityEngine:
    """数据质量引擎（Phase 3 完整实现）。"""

    def __init__(
        self,
        history_window: int   = 50,
        z_threshold:    float = 3.5,
        max_delay_secs: float = 300.0,
        drift_threshold:float = 0.3,
        log_fn: Callable | None = None,
    ) -> None:
        self._log            = log_fn or (lambda m: None)
        self._status         = SystemStatus.IDLE
        self._history_window = history_window
        self._z_threshold    = z_threshold
        self._max_delay_secs = max_delay_secs
        self._drift_threshold= drift_threshold

        # 历史窗口：{feature_name: {symbol: [float, ...]}}
        self._history: dict[str, dict[str, list[float]]] = {}
        # 质量报告历史
        self._reports:  list[QualityReport] = []
        # 漂移报告历史
        self._drift_reports: list[DriftReport] = []

    def init(self)  -> None: self._log("[QualityEngine] init()")
    def start(self) -> None:
        self._status = SystemStatus.COMPUTING
        self._log("[QualityEngine] start()")

    def stop(self)  -> None:
        self._status = SystemStatus.STOPPED
        self._log("[QualityEngine] stop()")

    # ── history management ────────────────────────────────────────────
    def _push_history(self, feature_name: str,
                       symbol: str, value: float) -> list[float]:
        """将新值推入历史窗口，返回当前窗口。"""
        bucket = self._history.setdefault(feature_name, {})
        window = bucket.setdefault(symbol, [])
        window.append(value)
        if len(window) > self._history_window:
            window.pop(0)
        return window

    def _get_history(self, feature_name: str,
                      symbol: str) -> list[float]:
        return self._history.get(feature_name, {}).get(symbol, [])

    # ── core check ────────────────────────────────────────────────────
    def check_feature(
        self,
        record:         FeatureRecord,
        related:        dict[str, float] | None = None,
        rules:          list[tuple[str, str, float]] | None = None,
    ) -> QualityReport:
        """
        对单条 FeatureRecord 执行完整质量检查。
        结果追加到报告历史。
        """
        history = self._get_history(record.feature_name, record.symbol)

        report = run_quality_check(
            value          = record.value,
            timestamp      = record.timestamp,
            feature_name   = record.feature_name,
            symbol         = record.symbol,
            history        = history,
            related        = related,
            rules          = rules,
            z_threshold    = self._z_threshold,
            max_delay_secs = self._max_delay_secs,
        )

        # 更新历史窗口（仅 CLEAN / OUTLIER 时更新，MISSING/DELAYED 不推入）
        if record.value is not None and report.status not in (
                QualityStatus.MISSING,):
            self._push_history(record.feature_name, record.symbol, record.value)

        self._reports.append(report)
        self._log(
            f"[QualityEngine] check {record.feature_name}/{record.symbol}: "
            f"status={report.status.value} score={report.score:.1f} "
            f"issues={report.n_issues}")
        return report

    def check_many(
        self,
        records: list[FeatureRecord],
    ) -> list[QualityReport]:
        """批量质量检查。"""
        return [self.check_feature(r) for r in records]

    # ── drift detection ───────────────────────────────────────────────
    def check_drift(
        self,
        feature_name:    str,
        symbol:          str,
        curr_values:     list[float],
        hist_values:     list[float] | None = None,
    ) -> DriftReport:
        """
        检测特征分布漂移。
        hist_values 未提供时使用内部历史窗口的前半段。
        """
        if hist_values is None:
            window = self._get_history(feature_name, symbol)
            mid    = max(len(window) // 2, 1)
            hist_values = window[:mid]

        report = detect_drift(
            feature_name    = feature_name,
            symbol          = symbol,
            hist_values     = hist_values,
            curr_values     = curr_values,
            drift_threshold = self._drift_threshold,
        )
        self._drift_reports.append(report)
        if report.is_drifted:
            self._log(
                f"[QualityEngine] DRIFT detected {feature_name}/{symbol}: "
                f"score={report.drift_score:.3f} > {self._drift_threshold}")
        return report

    def check_drift_from_feature(
        self,
        record: FeatureRecord,
    ) -> DriftReport | None:
        """
        用最新的特征值与历史窗口的前半段比较，检测漂移。
        历史样本不足时返回 None。
        """
        window = self._get_history(record.feature_name, record.symbol)
        if len(window) < 10:
            return None
        mid        = len(window) // 2
        hist_half  = window[:mid]
        curr_half  = window[mid:] + [record.value]
        return self.check_drift(
            record.feature_name, record.symbol, curr_half, hist_half)

    # ── query ─────────────────────────────────────────────────────────
    def get_reports(self, n: int = 50,
                     status: QualityStatus | None = None) -> list[QualityReport]:
        reps = self._reports
        if status is not None:
            reps = [r for r in reps if r.status == status]
        return reps[-n:]

    def get_drift_reports(self, n: int = 20,
                           drifted_only: bool = False) -> list[DriftReport]:
        reps = self._drift_reports
        if drifted_only:
            reps = [r for r in reps if r.is_drifted]
        return reps[-n:]

    def get_feature_quality(self, feature_name: str,
                             symbol: str) -> QualityReport | None:
        """返回指定特征的最新质量报告。"""
        for r in reversed(self._reports):
            if r.feature_name == feature_name and r.symbol == symbol:
                return r
        return None

    def get_blockers(self) -> list[QualityReport]:
        """返回所有含阻断性问题的报告。"""
        return [r for r in self._reports if r.has_blocker]

    # ── state ─────────────────────────────────────────────────────────
    def get_state(self) -> QualityState:
        reps   = self._reports
        n      = len(reps)
        clean  = sum(1 for r in reps if r.status == QualityStatus.CLEAN)
        issues = sum(r.n_issues for r in reps)
        blkr   = sum(1 for r in reps if r.has_blocker)

        status_counts: dict[str, int] = {}
        for r in reps:
            k = r.status.value
            status_counts[k] = status_counts.get(k, 0) + 1

        avg_score = (sum(r.score for r in reps) / n) if n else 100.0
        drifted   = [dr for dr in self._drift_reports if dr.is_drifted]
        drift_feats = list({f"{d.feature_name}/{d.symbol}" for d in drifted})

        return QualityState(
            total_checked  = n,
            total_issues   = issues,
            total_drifted  = len(drifted),
            clean_count    = clean,
            clean_pct      = round(clean / n * 100, 2) if n else 100.0,
            avg_score      = round(avg_score, 2),
            blocker_count  = blkr,
            status_counts  = status_counts,
            drift_features = drift_feats,
            updated_at     = datetime.now(),
        )

    def summary(self) -> dict:
        s = self.get_state()
        return {
            "phase":         3,
            "status":        self._status.value,
            "total_checked": s.total_checked,
            "clean_pct":     s.clean_pct,
            "avg_score":     s.avg_score,
            "blocker_count": s.blocker_count,
            "total_drifted": s.total_drifted,
        }
