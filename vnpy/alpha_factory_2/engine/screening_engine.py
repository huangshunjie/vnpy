"""
alpha_factory_2/engine/screening_engine.py  (Phase 4)

ScreeningEngine — Alpha 筛选与自动淘汰引擎。

筛选规则（可动态调整）：
  IC_THRESHOLD        ic >= threshold（默认 0.02）
  STABILITY_THRESHOLD stability(IR) >= threshold（默认 0.0）
  DECAY_THRESHOLD     decay(半衰期) >= threshold（默认 2.0 日）
  SCORE_THRESHOLD     total_score >= threshold（默认 0.20）
  TURNOVER_THRESHOLD  turnover <= threshold（默认 0.95）

自动淘汰机制：
  长期低分（连续 N 次评分低于 retire_score）→ REJECTED
  IC 持续为负（连续 N 次 IC < retire_ic）→ REJECTED

❌ 不执行任何交易逻辑
❌ 不修改 Portfolio / Execution / Risk
✔  仅读取 AlphaScore，广播 EVENT_ALPHA_SCREENED / EVENT_ALPHA_REJECTED
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from ..constant import AlphaStatus, ScreeningRule
from ..model.alpha_model import AlphaSignal
from ..model.score_model import AlphaScore


# ─────────────────────────────────────────────────────────────────────────────
#  筛选规则配置
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScreeningThresholds:
    """所有筛选阈值（可运行时修改）。"""
    ic_min:            float = 0.02     # IC >= ic_min
    stability_min:     float = 0.0      # IR >= stability_min
    decay_min:         float = 2.0      # 半衰期 >= decay_min（交易日）
    score_min:         float = 0.20     # total_score >= score_min
    turnover_max:      float = 0.95     # turnover <= turnover_max

    # 自动退役条件
    retire_score:      float = 0.15     # 连续低分退役阈值
    retire_ic:         float = -0.05    # 连续低 IC 退役阈值
    retire_streak:     int   = 3        # 连续 N 次触发才退役


# ─────────────────────────────────────────────────────────────────────────────
#  筛选记录
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScreeningRecord:
    """单次筛选决策记录。"""
    record_id:   str
    alpha_id:    str
    passed:      bool
    rules_failed: list[str]          = field(default_factory=list)
    score:       float               = 0.0
    ts:          datetime            = field(default_factory=datetime.now)
    detail:      str                 = ""

    def to_dict(self) -> dict:
        return {
            "record_id":    self.record_id,
            "alpha_id":     self.alpha_id,
            "passed":       self.passed,
            "rules_failed": self.rules_failed,
            "score":        round(self.score, 4),
            "ts":           str(self.ts)[:19],
            "detail":       self.detail,
        }


@dataclass
class RetireRecord:
    """Alpha 退役记录。"""
    alpha_id:  str
    reason:    str
    score:     float    = 0.0
    ic:        float    = 0.0
    streak:    int      = 0
    retired_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "alpha_id":   self.alpha_id,
            "reason":     self.reason,
            "score":      round(self.score, 4),
            "ic":         round(self.ic, 4),
            "streak":     self.streak,
            "retired_at": str(self.retired_at)[:19],
        }


# ─────────────────────────────────────────────────────────────────────────────
#  ScreeningEngine
# ─────────────────────────────────────────────────────────────────────────────

class ScreeningEngine:
    """
    Alpha 筛选引擎（Phase 4）。

    使用方式：
        se = ScreeningEngine()
        passed, rejected = se.batch_screen(alphas, scores)
        # 自动退役检查
        retired = se.check_retirement(alpha_id, score)
    """

    def __init__(
        self,
        thresholds: ScreeningThresholds | None = None,
        log_fn:     Callable | None            = None,
    ) -> None:
        self._t       = thresholds or ScreeningThresholds()
        self._log     = log_fn or (lambda msg: None)
        self._counter = 0

        # 历史记录
        self._screening_records: list[ScreeningRecord] = []
        self._retire_records:    list[RetireRecord]    = []

        # 连续低分追踪 {alpha_id: (streak_count, last_score, last_ic)}
        self._streak: dict[str, dict] = {}

    # ------------------------------------------------------------------ #
    #  单个筛选
    # ------------------------------------------------------------------ #

    def screen(
        self,
        alpha: AlphaSignal,
        score: AlphaScore,
    ) -> bool:
        """
        筛选单个 Alpha。

        Returns
        -------
        bool  True = 通过筛选
        """
        failed: list[str] = []

        if score.ic < self._t.ic_min:
            failed.append(
                f"{ScreeningRule.IC_THRESHOLD.value}: "
                f"IC={score.ic:.4f} < {self._t.ic_min}"
            )
        if score.stability < self._t.stability_min:
            failed.append(
                f"{ScreeningRule.STABILITY_THRESHOLD.value}: "
                f"IR={score.stability:.3f} < {self._t.stability_min}"
            )
        if score.decay < self._t.decay_min:
            failed.append(
                f"{ScreeningRule.DECAY_THRESHOLD.value}: "
                f"HL={score.decay:.1f} < {self._t.decay_min}"
            )
        if score.total_score < self._t.score_min:
            failed.append(
                f"{ScreeningRule.LOW_SCORE_RETIRE.value}: "
                f"score={score.total_score:.4f} < {self._t.score_min}"
            )
        if score.turnover > self._t.turnover_max:
            failed.append(
                f"turnover_threshold: "
                f"TO={score.turnover:.3f} > {self._t.turnover_max}"
            )

        passed = len(failed) == 0
        self._counter += 1
        rec = ScreeningRecord(
            record_id    = f"SCR_{self._counter:06d}",
            alpha_id     = alpha.alpha_id,
            passed       = passed,
            rules_failed = failed,
            score        = score.total_score,
            detail       = "; ".join(failed) if failed else "all rules passed",
        )
        self._screening_records.append(rec)

        self._log(
            f"[ScreeningEngine] {alpha.alpha_id}  "
            f"{'PASS' if passed else 'FAIL'}  "
            f"score={score.total_score:.4f}  "
            f"failed={len(failed)}"
        )
        return passed

    # ------------------------------------------------------------------ #
    #  批量筛选
    # ------------------------------------------------------------------ #

    def batch_screen(
        self,
        alphas: list[AlphaSignal],
        scores: list[AlphaScore],
    ) -> tuple[list[AlphaSignal], list[AlphaSignal]]:
        """
        批量筛选。

        Parameters
        ----------
        alphas : Alpha 列表
        scores : 与 alphas 等长的评分列表

        Returns
        -------
        (passed_list, rejected_list)
        """
        passed:   list[AlphaSignal] = []
        rejected: list[AlphaSignal] = []

        score_map = {s.alpha_id: s for s in scores}

        for alpha in alphas:
            sc = score_map.get(alpha.alpha_id)
            if sc is None:
                rejected.append(alpha)
                continue
            if self.screen(alpha, sc):
                passed.append(alpha)
            else:
                rejected.append(alpha)

        self._log(
            f"[ScreeningEngine] batch_screen: "
            f"passed={len(passed)}  rejected={len(rejected)}"
        )
        return passed, rejected

    # ------------------------------------------------------------------ #
    #  自动退役检查
    # ------------------------------------------------------------------ #

    def check_retirement(
        self,
        alpha_id: str,
        score:    AlphaScore,
    ) -> bool:
        """
        检查 Alpha 是否应退役。

        条件（满足任一即退役）：
          连续 retire_streak 次 total_score < retire_score
          连续 retire_streak 次 ic < retire_ic

        Returns
        -------
        bool  True = 应退役
        """
        t = self._t
        if alpha_id not in self._streak:
            self._streak[alpha_id] = {
                "low_score_streak": 0,
                "low_ic_streak":    0,
            }

        st = self._streak[alpha_id]

        # 低分连续计数
        if score.total_score < t.retire_score:
            st["low_score_streak"] += 1
        else:
            st["low_score_streak"] = 0

        # 低 IC 连续计数
        if score.ic < t.retire_ic:
            st["low_ic_streak"] += 1
        else:
            st["low_ic_streak"] = 0

        # 判断是否触发退役
        if st["low_score_streak"] >= t.retire_streak:
            reason = (
                f"连续 {st['low_score_streak']} 次评分低于 {t.retire_score}"
            )
            self._record_retire(
                alpha_id, reason, score,
                streak=st["low_score_streak"]
            )
            return True

        if st["low_ic_streak"] >= t.retire_streak:
            reason = (
                f"连续 {st['low_ic_streak']} 次 IC 低于 {t.retire_ic}"
            )
            self._record_retire(
                alpha_id, reason, score,
                streak=st["low_ic_streak"]
            )
            return True

        return False

    def _record_retire(
        self, alpha_id: str, reason: str,
        score: AlphaScore, streak: int,
    ) -> None:
        rec = RetireRecord(
            alpha_id = alpha_id,
            reason   = reason,
            score    = score.total_score,
            ic       = score.ic,
            streak   = streak,
        )
        self._retire_records.append(rec)
        self._log(f"[ScreeningEngine] RETIRE {alpha_id}  {reason}")

    # ------------------------------------------------------------------ #
    #  阈值动态更新
    # ------------------------------------------------------------------ #

    def update_thresholds(self, **kwargs) -> None:
        """动态更新筛选阈值，如 update_thresholds(ic_min=0.03)。"""
        for k, v in kwargs.items():
            if hasattr(self._t, k):
                setattr(self._t, k, v)
                self._log(f"[ScreeningEngine] threshold updated: {k}={v}")

    # ------------------------------------------------------------------ #
    #  查询接口
    # ------------------------------------------------------------------ #

    def get_screening_records(
        self,
        limit:       int  = 200,
        passed_only: bool = False,
        failed_only: bool = False,
    ) -> list[ScreeningRecord]:
        recs = self._screening_records[-limit:]
        if passed_only:
            return [r for r in recs if r.passed]
        if failed_only:
            return [r for r in recs if not r.passed]
        return recs

    def get_retire_records(self, limit: int = 100) -> list[RetireRecord]:
        return self._retire_records[-limit:]

    def get_thresholds(self) -> dict:
        t = self._t
        return {
            "ic_min":        t.ic_min,
            "stability_min": t.stability_min,
            "decay_min":     t.decay_min,
            "score_min":     t.score_min,
            "turnover_max":  t.turnover_max,
            "retire_score":  t.retire_score,
            "retire_ic":     t.retire_ic,
            "retire_streak": t.retire_streak,
        }

    def summary(self) -> dict:
        total   = len(self._screening_records)
        passed  = sum(1 for r in self._screening_records if r.passed)
        retired = len(self._retire_records)
        return {
            "total_screened": total,
            "passed":         passed,
            "rejected":       total - passed,
            "pass_rate":      round(passed / total, 4) if total else 0.0,
            "retired":        retired,
        }
